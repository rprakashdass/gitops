# Telegram Bot - Quick Start

Get the Telegram bot running in 5 minutes.

## Step 1: Create Telegram Bot (2 min)

1. Open Telegram
2. Find `@BotFather`
3. Send `/start` then `/newbot`
4. Follow prompts to name your bot
5. **Copy your token** (looks like: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

## Step 2: Get Your Chat ID (1 min)

1. Message your newly created bot
2. Visit: `https://api.telegram.org/bot{YOUR_TOKEN}/getUpdates`
3. Find your user ID in the `message.from.id` field
4. **Copy your chat ID** (a number like: `987654321`)

## Step 3: Create Kubernetes Secret (1 min)

```bash
kubectl create secret generic telegram-bot-secrets \
  --from-literal=TELEGRAM_BOT_TOKEN='123456:ABC-DEF1234...' \
  --from-literal=TELEGRAM_CHAT_ID='987654321' \
  -n home
```

Verify:
```bash
kubectl get secret telegram-bot-secrets -n home
```

## Step 4: Deploy (1 min)

```bash
git add services/messaging/telegram-bot/
git commit -m "feat: deploy telegram-bot"
git push origin main
```

ArgoCD will auto-deploy within minutes.

## Step 5: Verify (1 min)

```bash
# Check pod is running
kubectl get pods -n home -l app.kubernetes.io/name=telegram-bot

# Check logs
kubectl logs -n home -l app.kubernetes.io/name=telegram-bot -f
```

## Test

### Send Message via Telegram

Message your bot:
```
/help
```

You should see all available commands.

### Send Notification via API

```bash
# Port-forward (or use k9s)
kubectl port-forward -n home svc/telegram-bot 9999:9999

# Send notification
curl -X POST http://localhost:9999/api/notify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Notification",
    "message": "Hello from the bot!",
    "service": "test"
  }'
```

Check Telegram — you should receive the notification!

## Next Steps

- **Add commands:** Edit [src/main.py](./src/main.py), add handler, push
- **Send notifications:** Use the `/api/notify` endpoint from other services
- **Check logs:** `kubectl logs -n home -f -l app.kubernetes.io/name=telegram-bot`

## Troubleshooting

### Pod won't start
```bash
kubectl describe pod -n home -l app.kubernetes.io/name=telegram-bot
# Check: Are secrets created? Is token valid?
```

### Bot doesn't respond to messages
```bash
# Check API manually
curl https://api.telegram.org/bot{TOKEN}/getMe

# Check for updates
curl https://api.telegram.org/bot{TOKEN}/getUpdates
```

### Can't send notifications
```bash
# Check service DNS
kubectl run -it --rm debug --image=alpine -- sh
nslookup telegram-bot.home.svc.cluster.local
exit

# Test connectivity
kubectl exec -it <pod-name> -n home -- curl http://telegram-bot:9999/health
```

---

**Done!** Your Telegram bot is live and ready. 🚀
