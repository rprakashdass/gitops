# platform/

Shared, cluster-wide infrastructure — deployed by the app-of-apps in
[`../argocd/applications`](../argocd/applications). These are the capabilities
every workload relies on; they are not application workloads themselves.

| Directory / file | Purpose |
|------------------|---------|
| `observability/` | Grafana stack: Alloy, Loki, Mimir, Tempo, Grafana, MinIO, alerting |
| `alerting/` | Alert rules + Alertmanager config (`global/`, `production/`) |
| `ingress.yaml` | Platform ingress routing |
| `vault/` | HashiCorp Vault — `values.yaml` (main) + `transit/` (auto-unseal) |
| `external-secrets/` | External Secrets Operator values + `stores/` (SecretStore + ExternalSecrets) |

See [../docs/secrets.md](../docs/secrets.md) for the Vault + ESO bootstrap and
[../docs/repos.md](../docs/repos.md) for how this control plane relates to
`homelab-gitops`.
