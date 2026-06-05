#!/usr/bin/env python3
import os
import sys
from datetime import datetime, timezone

try:
    import requests
    from kubernetes import client, config
except ImportError as e:
    print(f"ERROR: missing package — {e}", flush=True)
    sys.exit(1)


SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")


def fmt(val):
    return val if val else "N/A"


def parse_cpu_to_millicores(cpu_str):
    if cpu_str.endswith("n"):
        return int(cpu_str[:-1]) / 1_000_000
    if cpu_str.endswith("m"):
        return int(cpu_str[:-1])
    return int(cpu_str) * 1000


def parse_memory_to_mib(mem_str):
    if mem_str.endswith("Ki"):
        return int(mem_str[:-2]) / 1024
    if mem_str.endswith("Mi"):
        return int(mem_str[:-2])
    if mem_str.endswith("Gi"):
        return int(mem_str[:-2]) * 1024
    return int(mem_str) / (1024 * 1024)


def send_slack(text):
    if not SLACK_WEBHOOK:
        print("SLACK_WEBHOOK_URL not set — skipping alert", flush=True)
        return
    try:
        resp = requests.post(SLACK_WEBHOOK, json={"text": text}, timeout=10)
        resp.raise_for_status()
        print("Slack alert sent.", flush=True)
    except Exception as e:
        print(f"Slack send failed: {e}", flush=True)


def main():
    config.load_incluster_config()
    v1 = client.CoreV1Api()
    custom = client.CustomObjectsApi()

    namespace = os.getenv("NAMESPACE", "pos-dev")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        f"*Resource Report — {now}*",
        f"Namespace: `{namespace}`",
        "",
    ]

    # ── PVC storage ──────────────────────────────────────────────────────────
    lines.append("*PVC Storage:*")
    pvcs = v1.list_namespaced_persistent_volume_claim(namespace=namespace)
    if not pvcs.items:
        lines.append("  No PVCs found.")
    else:
        for pvc in sorted(pvcs.items, key=lambda p: p.metadata.name):
            capacity = "N/A"
            if pvc.status.capacity:
                capacity = fmt(pvc.status.capacity.get("storage"))
            elif pvc.spec.resources and pvc.spec.resources.requests:
                capacity = fmt(pvc.spec.resources.requests.get("storage"))
            lines.append(
                f"  • `{pvc.metadata.name}` — {pvc.status.phase} / {capacity}"
            )

    lines.append("")

    # ── Pod CPU & memory ─────────────────────────────────────────────────────
    lines.append("*Pod CPU & Memory Usage:*")
    try:
        pod_metrics = custom.list_namespaced_custom_object(
            "metrics.k8s.io", "v1beta1", namespace, "pods"
        )
        if not pod_metrics["items"]:
            lines.append("  No pod metrics available.")
        for pm in sorted(pod_metrics["items"], key=lambda p: p["metadata"]["name"]):
            pod_name = pm["metadata"]["name"]
            for c in pm["containers"]:
                cpu_m = parse_cpu_to_millicores(c["usage"]["cpu"])
                mem_mi = parse_memory_to_mib(c["usage"]["memory"])
                lines.append(
                    f"  • `{pod_name}` [{c['name']}] — CPU: {cpu_m:.0f}m | Mem: {mem_mi:.1f}Mi"
                )
    except Exception as e:
        lines.append(f"  Could not fetch pod metrics: {e}")

    report = "\n".join(lines)
    print(report, flush=True)
    send_slack(report)


if __name__ == "__main__":
    main()
