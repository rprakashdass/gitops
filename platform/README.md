# platform/

Reusable platform capabilities shared across all services and automations.

## Contents

| Directory | Purpose |
|-----------|---------|
| `base-chart/` | Universal Helm chart (all services extend this) |
| `libraries/` | Reusable code libraries (Go, Python) |
| `notifications/` | Notification abstractions (Telegram, email, webhooks) |
| `common/` | Common utilities (config, logging, metrics) |
| `templates/` | Reusable Kubernetes manifest templates |
| `rbac/` | RBAC policy templates and examples |
| `policies/` | Security policies (NetworkPolicy, PodSecurityPolicy) |
| `secrets/` | Secret management setup (SOPS, age, Vault) |
| `workflowtemplates/` | Argo Workflows templates (future) |

## What Belongs Here

**Anything that is:**
- Reusable across multiple automations
- A shared capability or abstraction
- A library, utility, or template
- Foundational to the platform

**Examples:**
- ✅ A Python library to send Telegram notifications
- ✅ A Go package to read Kubernetes resources
- ✅ Helm templates for RBAC patterns
- ✅ Configuration loaders and validators
- ✅ Prometheus metric definitions
- ✅ Structured logging setup

## What Does NOT Belong Here

- **Service-specific code** → goes to the service chart
- **Automation-specific logic** → goes to the automation chart
- **Third-party software** → goes to `apps/`
- **Per-automation configuration** → goes to `services/` or `charts/`

## Base Chart

The **base-chart** is the foundation. All service charts extend it.

See [base-chart/README.md](base-chart/README.md) for:
- How to use the chart
- Supported workload types
- Values reference
- Examples

## Libraries

### Purpose

Encapsulate common logic so every automation doesn't rewrite it.

### Structure

```
platform/libraries/
├── python/
│   ├── setup.py
│   ├── homelab/
│   │   ├── __init__.py
│   │   ├── k8s.py          ← Kubernetes client helpers
│   │   ├── telegram.py     ← Telegram bot abstraction
│   │   ├── github.py       ← GitHub API helpers
│   │   └── logging.py      ← Structured logging
│   └── requirements.txt
├── go/
│   ├── go.mod
│   ├── k8s/                ← Kubernetes client wrappers
│   ├── telegram/           ← Telegram bot package
│   └── ...
└── shell/
    ├── common.sh           ← Common shell functions
    └── k8s-helpers.sh
```

### Example: Python Library

Create `platform/libraries/python/homelab/telegram.py`:

```python
import os
import requests

class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, text: str):
        """Send a message to the configured chat."""
        response = requests.post(
            f"{self.api_url}/sendMessage",
            json={"chat_id": self.chat_id, "text": text}
        )
        response.raise_for_status()
```

Then use it in your automations:

```python
# In a service automation
from homelab.telegram import TelegramBot

bot = TelegramBot(
    token=os.environ["TELEGRAM_BOT_TOKEN"],
    chat_id=os.environ["TELEGRAM_CHAT_ID"]
)
bot.send_message("Hello from my automation!")
```

### Example: Go Library

Create `platform/libraries/go/pkg/telegram/telegram.go`:

```go
package telegram

import (
    "fmt"
    "net/http"
)

type Bot struct {
    Token  string
    ChatID string
}

func (b *Bot) SendMessage(text string) error {
    // Send Telegram message
    url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", b.Token)
    // ... implementation
    return nil
}
```

Then use it in your Go automations:

```go
import "homelab/pkg/telegram"

func main() {
    bot := telegram.Bot{
        Token:  os.Getenv("TELEGRAM_BOT_TOKEN"),
        ChatID: os.Getenv("TELEGRAM_CHAT_ID"),
    }
    bot.SendMessage("Hello from my automation!")
}
```

## Notifications

Abstractions for sending notifications to multiple channels.

```
platform/notifications/
├── telegram.yaml           ← Telegram notification template
├── email.yaml              ← Email notification template
├── webhook.yaml            ← Webhook notification template
└── router.yaml             ← Route notifications by type
```

## Common

Shared utilities and configurations.

```
platform/common/
├── logging.yaml            ← Structured logging setup
├── metrics.yaml            ← Prometheus metrics definitions
├── config.yaml             ← Configuration patterns
└── error-handling.yaml     ← Error handling conventions
```

## RBAC

Reusable RBAC patterns for common scenarios.

```
platform/rbac/
├── read-pods.yaml          ← Read pods in a namespace
├── read-events.yaml        ← Read events (logs)
├── read-pvc.yaml           ← Read PersistentVolumeClaims
├── write-configmaps.yaml   ← Create/update ConfigMaps
└── full-namespace-admin.yaml
```

Example usage in a service:

```yaml
# charts/my-automation/values.yaml
base-chart:
  rbac:
    create: true
    rules:
      - apiGroups: [""]
        resources: ["pods", "pods/log"]
        verbs: ["get", "list", "watch"]
```

## Policies

Security policies for cluster-wide enforcement.

```
platform/policies/
├── network-policies/       ← NetworkPolicy for namespaces
├── pod-security/           ← PodSecurityPolicy patterns
└── resource-quotas/        ← ResourceQuota examples
```

## Secrets

Secret management setup and best practices.

```
platform/secrets/
├── setup.md                ← SOPS + age setup guide
├── examples/               ← Example encrypted files
└── rotation.md             ← Secret rotation patterns
```

## Philosophy

**The platform is the foundation that enables services.**

Services should focus on business logic:
- What do I want to automate?
- When should it run?
- What inputs/outputs matter?

The platform handles the mechanics:
- How do I send notifications?
- How do I authenticate with APIs?
- How do I log and monitor?
- How do I manage secrets?

This separation makes services:
- Easier to understand
- Faster to write
- Testable in isolation
- Reusable across the platform

## Best Practices

1. **One concern per file/module** → easier to maintain
2. **Backward-compatible changes** → updates don't break services
3. **Documented interfaces** → clear usage patterns
4. **Tested libraries** → confidence when using them
5. **Version your libraries** → pin specific versions in charts

## Future Abstractions

As you build automations, you'll identify patterns worth extracting to the platform:

- Notion API client → `platform/libraries/python/homelab/notion.py`
- GitHub activity summarizer → `platform/libraries/go/pkg/github/`
- Resume builder → `platform/libraries/python/homelab/resume.py`
- Markdown renderer → `platform/common/markdown/`
- Database schema helpers → `platform/libraries/go/pkg/db/`

Extract them when you notice:
- "I wrote this before in another automation"
- "This is too complex for an automation script"
- "Multiple automations need this"

---

See also: [base-chart/README.md](base-chart/README.md), [../services/README.md](../services/README.md)
