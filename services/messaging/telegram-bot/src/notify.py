#!/usr/bin/env python3
"""
Notification helper for other services to easily send Telegram messages.

Usage in your service:
    from notify import notify_user

    notify_user(
        title="Backup Complete",
        message="Daily backup finished successfully",
        service="backup-job"
    )
"""

import os
import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Get telegram-bot service endpoint from environment
TELEGRAM_BOT_HOST = os.getenv("TELEGRAM_BOT_HOST", "telegram-bot")
TELEGRAM_BOT_PORT = os.getenv("TELEGRAM_BOT_PORT", "9999")
TELEGRAM_BOT_URL = f"http://{TELEGRAM_BOT_HOST}:{TELEGRAM_BOT_PORT}/api/notify"


def notify_user(
    title: str,
    message: str,
    service: str,
    chat_id: Optional[str] = None,
    timeout: int = 5,
) -> bool:
    """
    Send notification via Telegram bot.

    Args:
        title: Notification title
        message: Notification message body
        service: Service name sending the notification
        chat_id: Optional override for chat ID
        timeout: Request timeout in seconds

    Returns:
        True if notification sent successfully, False otherwise

    Example:
        notify_user(
            title="Backup Complete",
            message="Backup finished at 2024-06-13T10:30:00Z",
            service="backup-job"
        )
    """
    try:
        payload = {
            "title": title,
            "message": message,
            "service": service,
        }

        if chat_id:
            payload["chat_id"] = chat_id

        response = requests.post(TELEGRAM_BOT_URL, json=payload, timeout=timeout)

        if response.status_code == 200:
            logger.info(f"Notification sent successfully: {title}")
            return True
        else:
            logger.error(
                f"Failed to send notification: {response.status_code} "
                f"{response.text}"
            )
            return False

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Cannot reach telegram-bot service: {e}")
        return False
    except requests.exceptions.Timeout:
        logger.error("Telegram-bot service timeout")
        return False
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return False


def notify_critical(title: str, message: str, service: str) -> None:
    """
    Send critical notification (must succeed or raise exception).

    Args:
        title: Notification title
        message: Notification message body
        service: Service name sending the notification

    Raises:
        Exception: If notification fails to send

    Example:
        notify_critical(
            title="Critical: Disk Space Low",
            message="Less than 10% disk space remaining",
            service="monitoring"
        )
    """
    if not notify_user(title, message, service):
        raise Exception(f"Failed to send critical notification: {title}")


# Convenience functions for common notifications


def notify_success(message: str, service: str) -> bool:
    """Send success notification."""
    return notify_user(title="✅ Success", message=message, service=service)


def notify_error(message: str, service: str) -> bool:
    """Send error notification."""
    return notify_user(title="❌ Error", message=message, service=service)


def notify_warning(message: str, service: str) -> bool:
    """Send warning notification."""
    return notify_user(title="⚠️ Warning", message=message, service=service)


def notify_info(message: str, service: str) -> bool:
    """Send info notification."""
    return notify_user(title="ℹ️ Info", message=message, service=service)


if __name__ == "__main__":
    # Quick test
    print("Testing Telegram bot notifications...")

    success = notify_info(
        message="This is a test notification from the notify helper",
        service="test-service",
    )

    if success:
        print("✅ Notification sent successfully!")
    else:
        print("❌ Failed to send notification")
