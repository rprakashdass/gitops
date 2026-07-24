#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timezone

print("Script is executing!..", flush=True)

try:
    import requests
    from kubernetes import client, config
    from kubernetes.stream import stream
except ImportError as e:
    print(f"ERROR: missing package — {e}", flush=True)
    sys.exit(1)


SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
SCALE_STEP_GI = 10
MAX_SIZE_GI   = 250
THRESHOLD_PCT = 80


def parse_storage_bytes(size_str):
    for unit, mult in [("Ti", 1024**4), ("Gi", 1024**3), ("Mi", 1024**2), ("Ki", 1024),
                       ("T", 1000**4), ("G", 1000**3), ("M", 1000**2), ("K", 1000)]:
        if size_str.endswith(unit):
            return int(size_str[:-len(unit)]) * mult
    return int(size_str)


def parse_cpu_millicores(cpu_str):
    if cpu_str.endswith("n"):
        return int(cpu_str[:-1]) / 1_000_000
    if cpu_str.endswith("m"):
        return int(cpu_str[:-1])
    return int(cpu_str) * 1000


def parse_memory_mib(mem_str):
    if mem_str.endswith("Ki"):
        return int(mem_str[:-2]) / 1024
    if mem_str.endswith("Mi"):
        return int(mem_str[:-2])
    if mem_str.endswith("Gi"):
        return int(mem_str[:-2]) * 1024
    return int(mem_str) / (1024 * 1024)


def send_slack(text):
    if not SLACK_WEBHOOK:
        print("SLACK_WEBHOOK_URL not set — skipping Slack alert", flush=True)
        return
    try:
        resp = requests.post(SLACK_WEBHOOK, json={"text": text}, timeout=10)
        resp.raise_for_status()
        print("Slack alert sent.", flush=True)
    except Exception as e:
        print(f"Slack send failed: {e}", flush=True)


def get_pvc_disk_usage(v1, namespace, pvc_name):
    """Exec df into the pod mounting the PVC, returns (usage_pct, pod_name)."""
    pods = v1.list_namespaced_pod(namespace=namespace)
    for pod in pods.items:
        if pod.status.phase != "Running":
            continue
        for volume in (pod.spec.volumes or []):
            pvc_ref = volume.persistent_volume_claim
            if not pvc_ref or pvc_ref.claim_name != pvc_name:
                continue
            for container in pod.spec.containers:
                for vm in (container.volume_mounts or []):
                    if vm.name != volume.name:
                        continue
                    try:
                        ws = stream(
                            v1.connect_get_namespaced_pod_exec,
                            pod.metadata.name, namespace,
                            command=["df", "-k", vm.mount_path],
                            container=container.name,
                            stderr=True, stdin=False, stdout=True, tty=False,
                            _preload_content=False
                        )
                        ws.run_forever(timeout=10)
                        output = ws.read_all()
                        for line in output.splitlines():
                            parts = line.split()
                            if len(parts) >= 5 and parts[4].endswith("%"):
                                return int(parts[4].rstrip("%")), pod.metadata.name
                    except Exception as e:
                        print(f"  df exec failed on {pod.metadata.name}/{container.name}: {e}", flush=True)
    return None, None


def scale_pvc(v1, namespace, pvc, usage_pct, lines):
    capacity_str  = pvc.spec.resources.requests.get("storage", "0")
    current_bytes = parse_storage_bytes(capacity_str)
    max_bytes     = MAX_SIZE_GI * (1024 ** 3)

    if current_bytes >= max_bytes:
        lines.append(f"  ⚠️ `{pvc.metadata.name}` at {usage_pct}% — already at max ({MAX_SIZE_GI}Gi), skipping")
        return

    new_bytes = min(current_bytes + SCALE_STEP_GI * (1024 ** 3), max_bytes)
    new_size  = f"{new_bytes // (1024 ** 3)}Gi"

    try:
        v1.patch_namespaced_persistent_volume_claim(
            name=pvc.metadata.name,
            namespace=namespace,
            body={"spec": {"resources": {"requests": {"storage": new_size}}}}
        )
        lines.append(f"  ✅ Scaled `{pvc.metadata.name}`: {capacity_str} → {new_size} (usage: {usage_pct}%)")
        print(f"Scaled {pvc.metadata.name}: {capacity_str} → {new_size}", flush=True)
    except Exception as e:
        lines.append(f"  ❌ Scale failed for `{pvc.metadata.name}`: {e}")
        print(f"Scale failed: {e}", flush=True)


def main():
    config.load_incluster_config()
    v1     = client.CoreV1Api()
    custom = client.CustomObjectsApi()

    namespace = os.getenv("NAMESPACE", "pos-dev")
    now       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        f"*Resource Report (df) — {now}*",
        f"Namespace: `{namespace}`",
        "",
    ]

    # ── PVC storage & autoscale ───────────────────────────────────────────────
    lines.append(f"*PVC Storage (threshold: {THRESHOLD_PCT}%, step: +{SCALE_STEP_GI}Gi, max: {MAX_SIZE_GI}Gi):*")

    pvcs = v1.list_namespaced_persistent_volume_claim(namespace=namespace)
    if not pvcs.items:
        lines.append("  No PVCs found.")
    else:
        for pvc in sorted(pvcs.items, key=lambda p: p.metadata.name):
            capacity  = pvc.status.capacity.get("storage", "N/A") if pvc.status.capacity else "N/A"
            usage_pct, pod_name = get_pvc_disk_usage(v1, namespace, pvc.metadata.name)

            if usage_pct is not None:
                icon = "🔴" if usage_pct >= THRESHOLD_PCT else "🟢"
                lines.append(f"  {icon} `{pvc.metadata.name}` — {pvc.status.phase} / {capacity} / {usage_pct}% used (pod: `{pod_name}`)")
                if usage_pct >= THRESHOLD_PCT:
                    scale_pvc(v1, namespace, pvc, usage_pct, lines)
            else:
                lines.append(f"  ⚪ `{pvc.metadata.name}` — {pvc.status.phase} / {capacity} (no running pod found)")

    lines.append("")

    # ── Pod CPU & memory ──────────────────────────────────────────────────────
    lines.append("*Pod CPU & Memory Usage:*")
    try:
        pod_metrics = custom.list_namespaced_custom_object("metrics.k8s.io", "v1beta1", namespace, "pods")
        if not pod_metrics["items"]:
            lines.append("  No pod metrics available.")
        for pm in sorted(pod_metrics["items"], key=lambda p: p["metadata"]["name"]):
            for c in pm["containers"]:
                cpu_m  = parse_cpu_millicores(c["usage"]["cpu"])
                mem_mi = parse_memory_mib(c["usage"]["memory"])
                lines.append(f"  • `{pm['metadata']['name']}` [{c['name']}] — CPU: {cpu_m:.0f}m | Mem: {mem_mi:.1f}Mi")
    except Exception as e:
        lines.append(f"  Could not fetch pod metrics: {e}")

    report = "\n".join(lines)
    print(report, flush=True)
    send_slack(report)


print("Execution completed!..", flush=True)

if __name__ == "__main__":
    main()
