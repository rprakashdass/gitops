#!/usr/bin/env python3
"""
Hello-World Heartbeat Logger

Simple health check that logs a heartbeat with metadata.
Useful for:
  - Verifying CronJob execution
  - Testing automation pipelines
  - Monitoring cluster time synchronization
  - Validating container runtime

Usage:
  python app.py              # Print to stdout
  python app.py --json       # JSON structured logging
  python app.py --webhook    # Send to webhook (if configured)
  python app.py --telegram   # Send to telegram-bot (if configured)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


class Heartbeat:
    """Heartbeat logger with multiple output formats."""

    def __init__(self):
        """Initialize heartbeat with environment and pod metadata."""
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.hostname = os.environ.get("HOSTNAME", "unknown")
        self.pod_name = os.environ.get("HOSTNAME", "unknown")  # K8s sets HOSTNAME to pod name
        self.namespace = os.environ.get("POD_NAMESPACE", "unknown")
        self.node_name = os.environ.get("NODE_NAME", "unknown")

    def as_text(self) -> str:
        """Format as human-readable text."""
        return (
            f"┌─ Personal Platform Heartbeat ─┐\n"
            f"│ Timestamp:  {self.timestamp}\n"
            f"│ Pod:        {self.pod_name}\n"
            f"│ Namespace:  {self.namespace}\n"
            f"│ Node:       {self.node_name}\n"
            f"└────────────────────────────────┘"
        )

    def as_json(self) -> str:
        """Format as JSON for structured logging."""
        data = {
            "message": "Personal platform heartbeat",
            "timestamp": self.timestamp,
            "pod_name": self.pod_name,
            "namespace": self.namespace,
            "node_name": self.node_name,
            "status": "healthy",
        }
        return json.dumps(data, indent=2)

    def as_compact(self) -> str:
        """Format as single-line JSON."""
        data = {
            "message": "heartbeat",
            "timestamp": self.timestamp,
            "pod": self.pod_name,
            "namespace": self.namespace,
            "node": self.node_name,
            "status": "ok",
        }
        return json.dumps(data)

    def send_to_webhook(self, webhook_url: str) -> bool:
        """
        Send heartbeat to webhook endpoint.

        Args:
            webhook_url: HTTP endpoint to POST heartbeat to

        Returns:
            True if successful, False otherwise
        """
        if not requests:
            print(
                "[ERROR] requests library not installed. "
                "Add 'requests' to requirements.txt",
                file=sys.stderr,
            )
            return False

        try:
            payload = {
                "message": "Personal platform heartbeat",
                "timestamp": self.timestamp,
                "pod": self.pod_name,
                "namespace": self.namespace,
                "node": self.node_name,
                "status": "healthy",
            }

            response = requests.post(
                webhook_url,
                json=payload,
                timeout=5,
            )

            if response.status_code in (200, 201, 204):
                print(f"[INFO] Webhook sent successfully: {webhook_url}")
                return True
            else:
                print(
                    f"[ERROR] Webhook failed: {response.status_code} {response.text}",
                    file=sys.stderr,
                )
                return False

        except Exception as e:
            print(f"[ERROR] Webhook request failed: {e}", file=sys.stderr)
            return False

    def send_to_telegram(self) -> bool:
        """
        Send heartbeat notification via Telegram bot service.

        Uses environment variables:
        - TELEGRAM_BOT_HOST: hostname of telegram-bot service
        - TELEGRAM_BOT_PORT: port of telegram-bot service

        Returns:
            True if successful, False otherwise.
        """
        if not requests:
            print(
                "[WARNING] requests library not installed. Skipping Telegram notification.",
                file=sys.stderr,
            )
            return False

        try:
            host = os.getenv("TELEGRAM_BOT_HOST", "telegram-bot")
            port = os.getenv("TELEGRAM_BOT_PORT", "9999")
            endpoint = f"http://{host}:{port}/api/notify"

            payload = {
                "title": "❤️ Platform Heartbeat",
                "message": (
                    f"*Timestamp:* {self.timestamp}\n"
                    f"*Pod:* {self.pod_name}\n"
                    f"*Namespace:* {self.namespace}\n"
                    f"*Node:* {self.node_name}\n"
                    f"*Status:* Healthy ✅"
                ),
                "service": "hello-world",
            }

            response = requests.post(endpoint, json=payload, timeout=5)

            if response.status_code in (200, 201, 204):
                print(f"[INFO] Telegram notification sent successfully")
                return True
            else:
                print(
                    f"[WARNING] Telegram notification failed: "
                    f"{response.status_code} {response.text}",
                    file=sys.stderr,
                )
                return False

        except requests.exceptions.ConnectionError:
            print(
                "[WARNING] Cannot reach telegram-bot service. "
                "Continuing without notification.",
                file=sys.stderr,
            )
            return False
        except Exception as e:
            print(
                f"[WARNING] Failed to send Telegram notification: {e}",
                file=sys.stderr,
            )
            return False

    def log(self, format: str = "text") -> bool:
        """
        Log heartbeat in specified format.

        Args:
            format: Output format ('text', 'json', 'compact')

        Returns:
            True if successful
        """
        try:
            if format == "json":
                print(self.as_json())
            elif format == "compact":
                print(self.as_compact())
            else:  # text (default)
                print(self.as_text())

            return True
        except Exception as e:
            print(f"[ERROR] Failed to log heartbeat: {e}", file=sys.stderr)
            return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Personal Platform Heartbeat Logger"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "compact"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--webhook",
        help="Send heartbeat to webhook URL",
    )
    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Send heartbeat notification via Telegram bot",
    )

    args = parser.parse_args()

    # Create heartbeat
    hb = Heartbeat()

    # Log to stdout
    success = hb.log(format=args.format)

    # Send to webhook if configured
    if args.webhook:
        webhook_success = hb.send_to_webhook(args.webhook)
        success = success and webhook_success

    # Send to telegram if requested
    if args.telegram:
        telegram_success = hb.send_to_telegram()
        success = success and telegram_success

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
