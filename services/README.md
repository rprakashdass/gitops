# Messaging Services

Centralized messaging and notification services for the homelab platform.

## Services

### [telegram-bot/](./telegram-bot/)

**Status:** ✅ Running | **Version:** 1.0.0

Centralized Telegram bot for commands, notifications, and integrations.

**Commands:**
- ✅ `/help` — Show available commands
- ✅ `/resume` — Get your resume/CV
- 🔄 `/deploy` — Deploy a service (future)
- 🔄 `/backup` — Trigger backup (future)
- 🔄 `/expenses` — View expenses (future)
- 🔄 `/notion` — Notion integration (future)
- 🔄 `/github` — GitHub integration (future)
- 🔄 `/health` — Cluster health (future)
- 🔄 `/status` — System status (future)

**API:**
```bash
# Send notification from any service
curl -X POST http://telegram-bot:9999/api/notify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Backup Complete",
    "message": "Daily backup finished successfully",
    "service": "backup-job"
  }'
```

**Setup:**
1. Create bot with @BotFather on Telegram
2. Get your chat ID
3. Create secret: `kubectl create secret generic telegram-bot-secrets --from-literal=TELEGRAM_BOT_TOKEN=... --from-literal=TELEGRAM_CHAT_ID=...`
4. Deploy via ArgoCD

See [telegram-bot/README.md](./telegram-bot/README.md) for detailed setup.

---

## Using Messaging in Your Services

### Option 1: Send Notification via HTTP

From any service/pod in the cluster:

```python
import requests

def notify_user(title: str, message: str, service: str):
    """Send notification via Telegram bot"""
    try:
        response = requests.post(
            "http://telegram-bot:9999/api/notify",
            json={
                "title": title,
                "message": message,
                "service": service
            },
            timeout=5
        )
        if response.status_code == 200:
            print("Notification sent")
        else:
            print(f"Failed: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

# Usage
notify_user(
    title="Backup Complete",
    message="Daily backup finished at 10:30 UTC",
    service="backup-job"
)
```

### Option 2: From Bash/Shell

```bash
#!/bin/bash

curl -X POST http://telegram-bot:9999/api/notify \
  -H "Content-Type: application/json" \
  -d "$(cat <<EOF
{
  "title": "Daily Report",
  "message": "Report generated: $(date)",
  "service": "report-generator"
}
EOF
)"
```

### Option 3: From Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup-job
  namespace: home
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: backup-service:latest
            command:
            - /bin/sh
            - -c
            - |
              # Do backup work...
              
              # Send notification
              curl -X POST http://telegram-bot:9999/api/notify \
                -H "Content-Type: application/json" \
                -d '{
                  "title": "Backup Complete",
                  "message": "Daily backup finished successfully",
                  "service": "backup-job"
                }'
          restartPolicy: OnFailure
```

## Architecture

```
┌─────────────────────────────────────────┐
│ Services                                │
│ • hello-world                           │
│ • backup-job                            │
│ • report-generator                      │
│ • etc.                                  │
└─────────────┬───────────────────────────┘
              │
              │ POST /api/notify
              │ (JSON with title, message, service)
              │
┌─────────────▼───────────────────────────┐
│ Telegram Bot Deployment                 │
│                                         │
│ ├── FastAPI Server (port 9999)          │
│ │   ├── /health (health check)          │
│ │   ├── /api/notify (receive messages)  │
│ │   ├── /api/commands (list commands)   │
│ │   └── /api/... (future endpoints)     │
│ │                                       │
│ ├── Telegram Bot Handler                │
│ │   ├── /help                           │
│ │   ├── /resume                         │
│ │   ├── /deploy (future)                │
│ │   └── ...                             │
│ │                                       │
│ └── Service (ClusterIP:9999)            │
└─────────────┬───────────────────────────┘
              │
              │ Telegram Bot API
              │
              ▼
       Telegram Servers
       └─ Your Telegram Account
```

## Environment Variables

All messaging services use these environment variables:

### Telegram Bot

| Variable | Required | Example |
|----------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Yes | `123456:ABC-DEF1234...` |
| `TELEGRAM_CHAT_ID` | Yes | `987654321` |
| `API_PORT` | No | `9999` (default) |
| `LOG_LEVEL` | No | `INFO` (default) |

Store in Kubernetes Secret:
```bash
kubectl create secret generic telegram-bot-secrets \
  --from-literal=TELEGRAM_BOT_TOKEN='...' \
  --from-literal=TELEGRAM_CHAT_ID='...' \
  -n home
```

## Future Services

### email/ (planned)
Email notifications for services.

### slack/ (planned)
Slack integration for notifications.

### webhooks/ (planned)
Generic webhook routing for notifications.

### router/ (planned)
Intelligent message routing based on priority, service, type.

## Monitoring

### Check Bot Status

```bash
# Pod status
kubectl get pods -n home -l app.kubernetes.io/name=telegram-bot

# Logs
kubectl logs -n home -l app.kubernetes.io/name=telegram-bot -f

# Service
kubectl get svc -n home -l app.kubernetes.io/name=telegram-bot

# Resource usage
kubectl top pods -n home -l app.kubernetes.io/name=telegram-bot
```

### Health Check

```bash
# From within cluster
kubectl exec -it <pod-name> -n home -- curl http://localhost:9999/health

# From outside (port-forward)
kubectl port-forward -n home svc/telegram-bot 9999:9999
curl http://localhost:9999/health
```

## Troubleshooting

### Bot not working

1. Check environment variables are set correctly
2. Verify Telegram token is valid
3. Message the bot first (activate chat)
4. Check logs: `kubectl logs -n home -l app.kubernetes.io/name=telegram-bot`

### Notifications not sending

1. Verify bot can reach Telegram API
2. Check service can reach telegram-bot service
3. Verify notification format is correct
4. Check service has proper network policy access

### Performance issues

- Monitor CPU/memory: `kubectl top pods -n home`
- Increase resource limits in values.yaml
- Consider adding message queue (Redis) for high volume

## Related

- [telegram-bot/README.md](./telegram-bot/) — Telegram bot setup and usage
- [../../docs/SELF_DISCOVERING_CICD.md](../../docs/SELF_DISCOVERING_CICD.md) — CI/CD platform
- [../../platform/base-chart/](../../platform/base-chart/) — Kubernetes templates

---

**Messaging Services** — Keep your homelab connected 🚀📢
