# Telegram Bot Service

Centralized Telegram bot for homelab platform messaging, notifications, and commands.

**Status:** ✅ Implemented — /help, /resume  
**Planned:** /deploy, /backup, /expenses, /notion, /github, /health, /status

## Overview

The Telegram bot runs as a Kubernetes Deployment and provides:

1. **Command Interface** — /help, /resume, etc.
2. **Notification API** — Other services POST notifications via HTTP
3. **Message Routing** — Centralized message handling and persistence

## Architecture

```
┌─────────────────────────────────────────┐
│ Services                                │
│ (hello-world, backup-job, etc)          │
└────────────┬────────────────────────────┘
             │
             │ HTTP POST /api/notify
             │
┌────────────▼────────────────────────────┐
│ Telegram Bot (Kubernetes Deployment)    │
│                                         │
│ ├── FastAPI: /api/notify                │
│ ├── Telegram Bot Handler                │
│ │   ├── /help                           │
│ │   ├── /resume                         │
│ │   ├── /deploy (future)                │
│ │   └── ...                             │
│ └── Service (ClusterIP:9999)            │
└────────────┬────────────────────────────┘
             │
             │ Telegram API
             │
             ▼
     Telegram Servers
```

## Setup

### 1. Create Telegram Bot

```bash
# Message @BotFather on Telegram
/start
/newbot
# Follow prompts, get your token

# Your token will look like:
# 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

### 2. Get Chat ID

```bash
# Message your bot, then visit:
https://api.telegram.org/bot{YOUR_TOKEN}/getUpdates

# Find your user ID in the response
```

### 3. Create Kubernetes Secret

```bash
kubectl create secret generic telegram-bot-secrets \
  --from-literal=TELEGRAM_BOT_TOKEN='123456:ABC-DEF1234...' \
  --from-literal=TELEGRAM_CHAT_ID='YOUR_USER_ID' \
  -n home
```

### 4. Deploy

```bash
# ArgoCD will auto-deploy when you commit:
git add services/messaging/telegram-bot/
git commit -m "feat: deploy telegram-bot service"
git push origin main

# Or manually:
kubectl apply -f services/messaging/telegram-bot/
```

### 5. Verify

```bash
# Check pod is running
kubectl get pods -n home -l app.kubernetes.io/name=telegram-bot

# Check logs
kubectl logs -n home -l app.kubernetes.io/name=telegram-bot -f

# Check service
kubectl get svc -n home -l app.kubernetes.io/name=telegram-bot
```

## Commands

### /help
Shows all available commands and how to use the bot.

```
/help
```

Response:
```
🤖 Homelab Control Bot - Available Commands

Implemented:
• /help - Show this help message
• /resume - Get your resume/CV

Coming Soon:
• /deploy - Deploy a service
• /backup - Trigger system backup
...
```

### /resume
Retrieve your latest resume/CV from storage.

```
/resume
```

**Development:** Currently returns a template. Will integrate with storage to fetch actual resume.

## Notification API

Any service can send notifications via HTTP POST:

### Endpoint
```
POST http://telegram-bot.home.svc.cluster.local:9999/api/notify
```

### Request Body
```json
{
  "title": "Backup Complete",
  "message": "Daily backup finished at 2024-06-13T10:30:00Z",
  "service": "backup-job",
  "chat_id": "optional_override_chat_id"
}
```

### Example: From hello-world
```python
import requests

def send_heartbeat():
    notification = {
        "title": "Hello World Heartbeat",
        "message": f"Daily heartbeat at {datetime.now().isoformat()}",
        "service": "hello-world"
    }
    
    response = requests.post(
        "http://telegram-bot.home.svc.cluster.local:9999/api/notify",
        json=notification,
        timeout=5
    )
    
    if response.status_code == 200:
        print("Notification sent successfully")
```

### Example: From Kubernetes Event
```bash
# CronJob can send notification:
command:
  - /bin/bash
args:
  - -c
  - |
    # Do work...
    
    # Send notification
    curl -X POST http://telegram-bot:9999/api/notify \
      -H "Content-Type: application/json" \
      -d '{
        "title": "Backup Complete",
        "message": "Daily backup finished successfully",
        "service": "backup-job"
      }'
```

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | (required) | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | (required) | Default chat to send messages to |
| `API_PORT` | 9999 | HTTP API port |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Kubernetes Secret

```bash
kubectl create secret generic telegram-bot-secrets \
  --from-literal=TELEGRAM_BOT_TOKEN='your-token' \
  --from-literal=TELEGRAM_CHAT_ID='your-chat-id' \
  -n home

# Edit existing
kubectl edit secret telegram-bot-secrets -n home
```

## Adding Commands

To add a new command (e.g., /deploy):

### 1. Add Handler in src/main.py

```python
async def deploy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /deploy command"""
    await update.message.reply_text(
        "🚀 Deployment Options:\n\n"
        "1. Deploy service\n"
        "2. Deploy all\n"
        "\nReply with: deploy SERVICE_NAME"
    )
    # Store state in context for follow-up

# Register handler
application.add_handler(CommandHandler("deploy", deploy_command))
```

### 2. Handle Follow-up Messages

```python
# For conversation-like flow, use ConversationHandler
from telegram.ext import ConversationHandler

def handle_deploy_response(update, context):
    service = update.message.text.split()[-1]
    # Deploy logic here
```

### 3. Test Locally

```bash
# Set environment
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"
export API_PORT=9999

# Run
python src/main.py
```

## API Endpoints

### GET /health
Health check endpoint for Kubernetes probes.

```bash
curl http://localhost:9999/health
# Response: {"status": "ok", "service": "telegram-bot"}
```

### POST /api/notify
Send notification from service.

```bash
curl -X POST http://localhost:9999/api/notify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test",
    "message": "This is a test notification",
    "service": "test-service"
  }'
```

### GET /api/commands
List all available commands.

```bash
curl http://localhost:9999/api/commands
```

## Troubleshooting

### Bot not receiving messages

```bash
# Check bot token
curl https://api.telegram.org/bot{TOKEN}/getMe

# Check for updates (messages)
curl https://api.telegram.org/bot{TOKEN}/getUpdates
```

### Service can't reach bot

```bash
# From another pod in cluster:
kubectl run -it --rm curl-test --image=curlimages/curl -- sh

# Inside pod:
curl http://telegram-bot:9999/health
curl http://telegram-bot.home.svc.cluster.local:9999/health
```

### Bot not starting

```bash
# Check logs
kubectl logs -n home -l app.kubernetes.io/name=telegram-bot

# Check events
kubectl describe pod -n home -l app.kubernetes.io/name=telegram-bot

# Verify secret
kubectl get secret telegram-bot-secrets -n home -o jsonpath='{.data.TELEGRAM_BOT_TOKEN}' | base64 -d
```

### Memory/CPU issues

```bash
# Increase limits in values.yaml
resources:
  limits:
    cpu: 1000m        # Increase from 500m
    memory: 512Mi     # Increase from 256Mi
```

## Future Enhancements

- [ ] Database storage for notifications history
- [ ] Message persistence and querying
- [ ] Scheduled messages
- [ ] /deploy command integration
- [ ] /backup command integration
- [ ] /health cluster status
- [ ] /status system metrics
- [ ] /expenses tracking
- [ ] /github notifications
- [ ] /notion integration
- [ ] Rich message formatting with buttons
- [ ] Conversation flows for multi-step commands
- [ ] Rate limiting and spam protection
- [ ] User permissions and roles
- [ ] Message editing and deletion

## Development

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"

# Run
python src/main.py
```

### Docker Build

```bash
docker build -t telegram-bot:test .
docker run -e TELEGRAM_BOT_TOKEN=... -e TELEGRAM_CHAT_ID=... -p 9999:9999 telegram-bot:test
```

### Helm Testing

```bash
# Lint
helm lint .

# Render
helm template test . -f values.yaml

# Dry-run
helm install test . --dry-run
```

## Related Services

- [services/messaging/](../) — Messaging capabilities
- [docs/SELF_DISCOVERING_CICD.md](../../docs/SELF_DISCOVERING_CICD.md) — CI/CD platform
- [platform/base-chart/](../../platform/base-chart/) — Universal Helm chart

---

**Telegram Bot Service** — Centralized messaging for the homelab platform 🤖
