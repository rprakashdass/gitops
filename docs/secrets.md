# Secrets — Vault + External Secrets Operator

Secrets live in **Vault**; the **External Secrets Operator (ESO)** syncs the
keys you declare into native Kubernetes Secrets. Nothing secret is committed to
git — only `ExternalSecret` *references*.

```
 Transit Vault ──(transit key)──▶ Main Vault (KV secret/) ◀──(K8s auth)── ESO
 (Shamir seal,                    (auto-unsealed)                          │
  manual unseal on                                                         ▼
  cold boot only)                                       ExternalSecret → K8s Secret
```

Why two Vaults: the main Vault auto-unseals against the transit Vault's key, so
node reboots don't leave your app secrets unreachable. The transit Vault is the
only thing you ever unseal by hand — and only on a cold boot.

## Bootstrap (walk in order; enable each app in `argocd/applications/values.yaml` as you go)

All `vault` CLI calls run inside the pod: `kubectl -n vault exec -it <pod> -- sh`,
then `export VAULT_ADDR=http://127.0.0.1:8200`.

### 1. Transit Vault
Enable `vault-transit: true`, sync, then:
```bash
kubectl -n vault exec -it vault-transit-0 -- vault operator init \
  -key-shares=1 -key-threshold=1            # SAVE the unseal key + root token
kubectl -n vault exec -it vault-transit-0 -- vault operator unseal <unseal-key>
```
Configure the transit key + a token the main Vault will use:
```bash
kubectl -n vault exec -it vault-transit-0 -- sh -c '
  export VAULT_TOKEN=<transit-root-token>
  vault secrets enable transit
  vault write -f transit/keys/autounseal
  vault policy write autounseal - <<EOF
path "transit/encrypt/autounseal" { capabilities = ["update"] }
path "transit/decrypt/autounseal" { capabilities = ["update"] }
EOF
  vault token create -policy=autounseal -period=24h -orphan
'                                            # SAVE this token
```

### 2. Give the main Vault its transit token (out-of-band, never in git)
```bash
kubectl -n vault create secret generic vault-transit-unseal \
  --from-literal=token=<transit-token-from-step-1>
```

### 3. Main Vault
Enable `vault: true`, sync. It starts sealed, reads the transit token from the
secret above, and **auto-unseals**. Initialize it (auto-unseal → recovery keys,
no manual unseal):
```bash
kubectl -n vault exec -it vault-0 -- vault operator init \
  -recovery-shares=1 -recovery-threshold=1  # SAVE recovery key + root token
```
Configure KV + Kubernetes auth + an ESO role:
```bash
kubectl -n vault exec -it vault-0 -- sh -c '
  export VAULT_TOKEN=<main-root-token>
  vault secrets enable -path=secret -version=2 kv
  vault auth enable kubernetes
  vault write auth/kubernetes/config \
    kubernetes_host=https://kubernetes.default.svc
  vault policy write external-secrets - <<EOF
path "secret/data/*" { capabilities = ["read"] }
EOF
  vault write auth/kubernetes/role/external-secrets \
    bound_service_account_names=external-secrets \
    bound_service_account_namespaces=external-secrets \
    policies=external-secrets ttl=1h
'
```

### 4. Seed your secrets
```bash
kubectl -n vault exec -it vault-0 -- sh -c '
  export VAULT_TOKEN=<main-root-token>
  vault kv put secret/telegram \
    TELEGRAM_BOT_TOKEN=<token> TELEGRAM_CHAT_ID=<id>
'
```

### 5. External Secrets Operator + stores
Enable `external-secrets: true`, sync. Then enable
`external-secrets-stores: true`, sync. Verify:
```bash
kubectl -n home get externalsecret telegram-bot-secrets   # STATUS SecretSynced
kubectl -n home get secret telegram-bot-secrets           # created by ESO
```

## Day-2

- **Add a secret:** `vault kv put secret/<name> KEY=val`, then add an
  `ExternalSecret` under `platform/external-secrets/stores/` (or in
  homelab-gitops next to its consumer). Commit — ESO does the rest.
- **After a full cluster cold boot:** unseal *only* the transit Vault
  (`vault operator unseal`); the main Vault auto-unseals off it.
- **Save the init material** (unseal/recovery keys + root tokens) in a password
  manager. Losing the transit unseal key means re-initializing.

## Next step
Move the telegram `ExternalSecret` into `homelab-gitops` beside the bot, so the
control plane owns only the `ClusterSecretStore` (the platform binding) and each
app owns its own secret references.
