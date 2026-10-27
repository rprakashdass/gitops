# Edge proxy (Azure VM)

Caddy on the Azure VM (`proxy`, reached as `k3s-bastion`) terminates TLS for `*.rprakashdass.in` and forwards to Traefik on the k3s master through the reverse SSH tunnel.

```
Internet -> Cloudflare DNS (*.rprakashdass.in, DNS-only) -> Azure VM :443 (Caddy)
         -> 127.0.0.1:8080 -> autossh reverse tunnel -> k3s master :80 (Traefik)
```

## Run

```
cd ansible/edge
TOKEN=$(cb cloudfare/dns-token-tf) && [ -n "$TOKEN" ] && \
  CADDY_CF_TOKEN=$TOKEN ansible-playbook playbook.yml --diff --ask-become-pass
```

Add `--check` for a dry run. On a fresh VM the dry run fails at "Enable and start Caddy" because check mode does not install packages.

## What lives where

| Piece | Location |
|---|---|
| Hostnames and upstreams | `group_vars/edge/main.yml` (`caddy_routes`) |
| Caddyfile | `templates/Caddyfile.j2` |
| Cloudflare token (DNS-01) | `/etc/caddy/caddy.env` on the VM, mode 0600, from `CADDY_CF_TOKEN` |
| Wildcard DNS record | `terraform/envs/edge` |
| Reverse tunnel | `k3s-tunnel.service` on the k3s master (forwards 6443, 2222 and 8080) |

## Adding an app

1. Add its hostname to a route in `group_vars/edge/main.yml`.
2. Set the host on its Ingress in this repo and let ArgoCD sync.
3. Rerun the playbook.

## Tunnel

The web forward is `-R 127.0.0.1:8080:<master LAN IP>:80`. The master's IP is read when `k3s-tunnel.service` starts (`/usr/local/bin/k3s-tunnel-start.sh`), so restart the service after the IP changes. Reserve the master's IP in the router.

## Notes

- Caddy's apt unit runs `caddy run --environ`, which prints the environment (including the token) to the journal. The drop-in overrides `ExecStart` to drop it; keep it that way.
- The Azure VM has auto-shutdown enabled (02:00 IST), which takes every site down until it is started again.

## Local values (not committed)

This repo is public. Copy `group_vars/edge/local.yml.example` to `group_vars/edge/local.yml` and `terraform/envs/edge/terraform.tfvars.example` to `terraform.tfvars`, then fill them in. Both real files are gitignored.
