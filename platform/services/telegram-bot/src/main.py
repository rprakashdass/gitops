#!/usr/bin/env python3
"""
Centralized Telegram Bot for Homelab Platform

Commands:
  /help       — Show available commands
  /me         — Show bot info and status
  /resume     — Get latest resume/CV
  /deploy     — Deploy a service (future)
  /backup     — Trigger backup (future)
  /expenses   — View expenses (future)
  /notion     — Notion integration (future)
  /github     — GitHub integration (future)
  /health     — Cluster health status (future)
  /status     — System status (future)

Features:
  • Hourly heartbeat (silent, no notification)
  • Service notifications via /api/notify
  • Startup notification on bot launch
"""

import os
import logging
import asyncio
import json
import io
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    Minio = None
    S3Error = None

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get config from environment
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
API_PORT = int(os.getenv("API_PORT", "9999"))

# Global notification queue (will be set by bot thread)
notification_queue: Optional[asyncio.Queue] = None

# MinIO storage configuration
MINIO_HOST = os.getenv("MINIO_HOST", "minio.home:9000")
MINIO_ROOT_USER = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_ROOT_PASSWORD = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET = "telegram-bot-data"

# Initialize MinIO client
minio_client = None
if Minio:
    try:
        minio_client = Minio(
            MINIO_HOST,
            access_key=MINIO_ROOT_USER,
            secret_key=MINIO_ROOT_PASSWORD,
            secure=False,
        )
        logger.info(f"MinIO client initialized: {MINIO_HOST}")
    except Exception as e:
        logger.error(f"Failed to initialize MinIO: {e}")


def ensure_bucket_exists() -> bool:
    """Ensure MinIO bucket exists, create if needed"""
    if not minio_client:
        return False

    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
            logger.info(f"Created MinIO bucket: {MINIO_BUCKET}")
        return True
    except Exception as e:
        logger.error(f"Failed to ensure bucket: {e}")
        return False


def store_message(user_id: int, username: str, text: str) -> str:
    """Store user message in MinIO with metadata"""
    if not minio_client or not ensure_bucket_exists():
        logger.warning("MinIO not available, message not stored")
        return ""

    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        message_id = f"{user_id}-{timestamp.replace(':', '-').replace('.', '-')}"

        message = {
            "timestamp": timestamp,
            "user_id": user_id,
            "username": username,
            "text": text,
            "type": "text",
        }

        key = f"messages/text/{user_id}/{message_id}.json"
        data = json.dumps(message).encode()

        minio_client.put_object(
            MINIO_BUCKET,
            key,
            io.BytesIO(data),
            len(data),
            content_type="application/json",
        )

        logger.info(f"Stored message from {username}: {text[:50]}")
        return message_id
    except Exception as e:
        logger.error(f"Failed to store message: {e}")
        return ""


async def store_media(user_id: int, username: str, file_path: str, media_type: str, file_name: str) -> str:
    """Store media file in MinIO and track metadata"""
    if not minio_client or not ensure_bucket_exists():
        logger.warning("MinIO not available, media not stored")
        return ""

    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        file_id = f"{user_id}-{timestamp.replace(':', '-').replace('.', '-')}"

        # Upload file to MinIO
        key = f"media/{user_id}/{media_type}/{file_id}-{file_name}"

        with open(file_path, "rb") as f:
            file_data = f.read()

        minio_client.put_object(
            MINIO_BUCKET,
            key,
            io.BytesIO(file_data),
            len(file_data),
        )

        # Store metadata
        metadata = {
            "file_id": file_id,
            "timestamp": timestamp,
            "user_id": user_id,
            "username": username,
            "type": media_type,
            "original_name": file_name,
            "minio_key": key,
        }

        metadata_key = f"metadata/{user_id}/files.json"
        try:
            # Try to read existing metadata
            response = minio_client.get_object(MINIO_BUCKET, metadata_key)
            files = json.loads(response.read())
        except:
            files = []

        # Append new file
        files.append(metadata)

        # Store updated metadata
        metadata_data = json.dumps(files, indent=2).encode()
        minio_client.put_object(
            MINIO_BUCKET,
            metadata_key,
            io.BytesIO(metadata_data),
            len(metadata_data),
            content_type="application/json",
        )

        logger.info(f"Stored media from {username}: {media_type}/{file_name}")
        return file_id

    except Exception as e:
        logger.error(f"Failed to store media: {e}")
        return ""


async def retrieve_media(user_id: int, file_id: str) -> tuple:
    """Retrieve media file from MinIO by file_id"""
    if not minio_client or not ensure_bucket_exists():
        return None, None

    try:
        # Read metadata to find the file
        metadata_key = f"metadata/{user_id}/files.json"
        response = minio_client.get_object(MINIO_BUCKET, metadata_key)
        files = json.loads(response.read())

        # Find matching file
        file_meta = None
        for f in files:
            if f["file_id"] == file_id:
                file_meta = f
                break

        if not file_meta:
            logger.warning(f"File {file_id} not found for user {user_id}")
            return None, None

        # Download file from MinIO
        response = minio_client.get_object(MINIO_BUCKET, file_meta["minio_key"])
        file_data = response.read()

        return file_data, file_meta

    except Exception as e:
        logger.error(f"Failed to retrieve media: {e}")
        return None, None


async def list_user_media(user_id: int) -> list:
    """List all media files for a user"""
    if not minio_client or not ensure_bucket_exists():
        return []

    try:
        metadata_key = f"metadata/{user_id}/files.json"
        response = minio_client.get_object(MINIO_BUCKET, metadata_key)
        files = json.loads(response.read())
        return sorted(files, key=lambda f: f["timestamp"], reverse=True)
    except:
        return []


def get_user_messages(user_id: int, limit: int = 10) -> list:
    """Get user's recent messages from MinIO"""
    if not minio_client or not ensure_bucket_exists():
        return []

    try:
        prefix = f"messages/text/{user_id}/"
        objects = minio_client.list_objects(MINIO_BUCKET, prefix=prefix)

        messages = []
        for obj in objects:
            if not obj.object_name:
                continue
            try:
                response = minio_client.get_object(MINIO_BUCKET, obj.object_name)
                data = json.loads(response.read())
                messages.append(data)
            except Exception as e:
                logger.warning(f"Failed to read message {obj.object_name}: {e}")

        return sorted(messages, key=lambda m: m["timestamp"], reverse=True)[:limit]
    except Exception as e:
        logger.error(f"Failed to retrieve messages: {e}")
        return []


# Pydantic models for API
class NotificationRequest(BaseModel):
    """Notification payload from other services"""

    message: str
    title: Optional[str] = None
    chat_id: Optional[str] = None  # Override default chat ID
    service: Optional[str] = None  # Service that sent the notification


# FastAPI app for notifications API
api_app = FastAPI(
    title="Telegram Bot API",
    description="Centralized notification API for homelab services",
)


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for MarkdownV2"""
    special_chars = r"_*[]()~`>#+-=|{}.!"
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    if not update.message:
        return

    await update.message.reply_text(
        "👋 Welcome to Homelab Control Bot!\n\n" "Use /help to see available commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show all available commands"""
    if not update.message:
        return

    help_text = """
🤖 Homelab Control Bot - Available Commands

IMPLEMENTED:
• /help - Show this help message
• /me - Show bot info and status
• /k8s_report - Get cluster health report
• /resume - Get your resume/CV (latest version)
• /my_messages - View your recent text messages
• /my_files - View your stored media files
• /get_file <id> - Retrieve a stored file

MEDIA STORAGE:
Send photos, documents, audio, or videos and they'll be stored in MinIO.
• Photos are saved as JPG
• Documents keep original format
• Audio and video files supported
All files get a unique ID for later retrieval.

FEATURES:
• 🫀 Hourly heartbeat (automatic)
• 📨 Service notifications
• 🔔 Startup notification
• 💾 Persistent media storage in MinIO
• 📝 Message history tracking

COMING SOON:
• /deploy - Deploy a service
• /backup - Trigger system backup
• /expenses - View expense tracking
• /notion - Notion integration
• /github - GitHub notifications
• /health - Cluster health report
• /status - System status overview

FOR DEVELOPERS:
Send notifications via HTTP POST to http://telegram-bot:9999/api/notify

Example payload:
{
  "title": "Backup Complete",
  "message": "Daily backup finished",
  "service": "backup-job"
}

Need help? Type /help again or use /me for bot status.
"""
    await update.message.reply_text(help_text)


async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /resume command - send resume/CV"""
    if not update.message or not update.effective_user:
        return

    logger.info(f"Resume requested by user {update.effective_user.id}")

    resume_text = """
📄 Your Resume/CV

Name: Your Name
Title: Software Engineer | Platform Engineering

Summary:
Lorem ipsum dolor sit amet, consectetur adipiscing elit.

Experience:
• Position 1 (Company A)
• Position 2 (Company B)

Skills:
• Python, Go, Kubernetes
• Cloud (GCP, AWS)
• DevOps, CI/CD

Contact:
📧 Email: your.email@example.com
🔗 GitHub: github.com/yourname
🔗 LinkedIn: linkedin.com/in/yourname

Last updated: 2024-06-13

💡 Tip: Use /deploy, /backup, /health for other actions.
"""

    await update.message.reply_text(resume_text, parse_mode="MarkdownV2")
    if update.effective_user:
        logger.info(f"Resume sent to user {update.effective_user.id}")


async def me_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /me command - show bot info"""
    if not update.message:
        return

    import socket
    from datetime import datetime, timezone

    hostname = socket.gethostname()
    uptime = datetime.now(timezone.utc).isoformat()

    info_text = f"""
🤖 Homelab Bot Information

Hostname: {hostname}
Status: Running ✅
Started: {uptime}

Features:
• 📨 Notifications from services
• 📊 Cluster health reports
• 💼 Resume delivery
• 🔔 Hourly heartbeat

API Port: 9999
Chat ID: {TELEGRAM_CHAT_ID[:10]}...

Use /help for more commands.
"""
    await update.message.reply_text(info_text, parse_mode="MarkdownV2")


async def k8s_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /k8s_report command - show cluster health report"""
    if not update.message:
        return

    from datetime import datetime, timezone

    logger.info("Cluster health report requested")

    try:
        report_text = """
📊 *Kubernetes Cluster Health Report*

_Note: Detailed reports are generated weekly via the k8s\\-health\\-report CronJob \\(Sundays 06:00 UTC\\)_

*Quick Status:*
• Use the web dashboard for real\\-time monitoring
• Check ArgoCD for application deployment status
• View pod logs with: `kubectl logs -n home -f <pod-name>`

*Common Issues:*
• Pod not starting\\? → Check events: `kubectl describe pod -n home <pod-name>`
• Service unreachable\\? → Verify service exists: `kubectl get svc -n home`
• High resource usage\\? → Check limits: `kubectl top nodes/pods -n home`

*Next Scheduled Report:*
_Sunday 06:00 UTC \\(via k8s\\-health\\-report CronJob\\)_

For immediate cluster diagnostics, contact cluster admin or check the detailed weekly reports\\.
"""
        await update.message.reply_text(report_text, parse_mode="MarkdownV2")

    except Exception as e:
        logger.error(f"Failed to send report: {e}")
        await update.message.reply_text(
            f"❌ Failed to send report: {e}",
            parse_mode="Markdown"
        )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown commands"""
    if not update.message:
        return

    await update.message.reply_text(
        f"❌ Unknown command: {update.message.text}\n\n"
        "Use /help to see available commands."
    )


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE, media_type: str) -> None:
    """Handle file uploads (photos, documents, audio, video)"""
    if not update.message or not update.effective_user:
        return

    try:
        # Get file based on type
        file_obj = None
        file_name: str = ""

        if media_type == "photo" and update.message.photo:
            file_obj = update.message.photo[-1]  # Get highest resolution
            file_name = f"photo_{file_obj.file_id}.jpg"
        elif media_type == "document" and update.message.document:
            file_obj = update.message.document
            file_name = update.message.document.file_name or f"document_{file_obj.file_id}"
        elif media_type == "audio" and update.message.audio:
            file_obj = update.message.audio
            file_name = (update.message.audio.file_name or f"audio_{file_obj.file_id}.mp3")
        elif media_type == "video" and update.message.video:
            file_obj = update.message.video
            file_name = (update.message.video.file_name or f"video_{file_obj.file_id}.mp4")

        if not file_obj or not file_name:
            return

        # Download file from Telegram
        file = await context.bot.get_file(file_obj.file_id)
        file_path = f"/tmp/{file_obj.file_id}"
        await file.download_to_drive(file_path)

        # Store in MinIO
        user_id = update.effective_user.id if update.effective_user else 0
        username = (update.effective_user.username or "unknown") if update.effective_user else "unknown"
        file_id = await store_media(
            user_id,
            username,
            file_path,
            media_type,
            file_name,
        )

        if file_id:
            await update.message.reply_text(
                f"✅ {media_type.capitalize()} stored!\n"
                f"File ID: `{file_id}`\n"
                f"Retrieve with: /get_file {file_id}"
            )
            logger.info(f"Stored {media_type} from {update.effective_user.username}: {file_name}")
        else:
            await update.message.reply_text(f"❌ Failed to store {media_type}")

    except Exception as e:
        logger.error(f"Failed to handle {media_type}: {e}")
        await update.message.reply_text(f"❌ Error storing {media_type}: {str(e)[:50]}")


async def my_files_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /my_files command - show stored files"""
    if not update.message or not update.effective_user:
        return

    logger.info(f"User {update.effective_user.username} requested file list")

    files = await list_user_media(update.effective_user.id)
    if not files:
        await update.message.reply_text("No files stored yet.")
        return

    file_list = "Your stored files:\n\n"
    for f in files[-10:]:  # Last 10 files
        timestamp = f["timestamp"][:10]  # YYYY-MM-DD
        file_list += f"📁 [{f['type']}] {f['original_name']}\n"
        file_list += f"   ID: `{f['file_id']}`\n"
        file_list += f"   Date: {timestamp}\n\n"

    file_list += "Retrieve with: /get_file <file_id>"
    await update.message.reply_text(file_list)


async def get_file_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /get_file command - retrieve and send stored file"""
    if not update.message or not update.effective_user:
        return

    if not context.args or len(context.args) == 0:
        await update.message.reply_text("Usage: /get_file <file_id>")
        return

    file_id = context.args[0]

    try:
        await update.message.reply_text("⏳ Retrieving file...")

        file_data, metadata = await retrieve_media(update.effective_user.id, file_id)

        if not file_data or not metadata:
            await update.message.reply_text("❌ File not found")
            return

        # Send file back to user
        if not update.effective_chat or not update.effective_chat.id:
            await update.message.reply_text("❌ Chat ID not available")
            return

        chat_id = update.effective_chat.id
        media_type = metadata["type"]

        if media_type == "photo":
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=io.BytesIO(file_data),
                caption=f"📷 {metadata['original_name']}\nStored: {metadata['timestamp'][:16]}",
            )
        elif media_type == "document":
            await context.bot.send_document(
                chat_id=chat_id,
                document=io.BytesIO(file_data),
                filename=metadata["original_name"],
                caption=f"📄 Stored: {metadata['timestamp'][:16]}",
            )
        elif media_type == "audio":
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=io.BytesIO(file_data),
                title=metadata["original_name"],
                caption=f"🎵 Stored: {metadata['timestamp'][:16]}",
            )
        elif media_type == "video":
            await context.bot.send_video(
                chat_id=chat_id,
                video=io.BytesIO(file_data),
                filename=metadata["original_name"],
                caption=f"🎬 Stored: {metadata['timestamp'][:16]}",
            )

        logger.info(f"Sent {media_type} to {update.effective_user.username}: {metadata['original_name']}")

    except Exception as e:
        logger.error(f"Failed to send file: {e}")
        await update.message.reply_text(f"❌ Error retrieving file: {str(e)[:50]}")


async def my_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /my_messages command - show recent messages"""
    if not update.message or not update.effective_user:
        return

    logger.info(f"User {update.effective_user.username} requested message history")

    user_messages = get_user_messages(update.effective_user.id, 10)
    if not user_messages:
        await update.message.reply_text("No messages stored yet.")
        return

    message_list = "Your recent messages:\n\n"
    for msg in user_messages:
        timestamp = msg["timestamp"][:16]  # YYYY-MM-DD HH:MM
        text = msg["text"][:50]
        message_list += f"[{timestamp}] {text}\n"

    await update.message.reply_text(message_list)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular messages"""
    if not update.message or not update.message.text or not update.effective_user:
        return

    logger.info(f"Message from {update.effective_user.username}: {update.message.text}")

    # Store the message
    store_message(
        update.effective_user.id,
        update.effective_user.username or "unknown",
        update.message.text
    )

    if update.message.text.startswith("/"):
        await unknown_command(update, context)
    else:
        # Echo back for debugging
        await update.message.reply_text(
            f"I received your message: {update.message.text[:50]}\n\n"
            "Use /help to see available commands."
        )


# API Endpoints
@api_app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "telegram-bot"}


@api_app.post("/api/notify")
async def send_notification(notification: NotificationRequest):
    """
    Receive notification from other services and send via Telegram

    Example:
    POST /api/notify
    {
      "title": "Backup Complete",
      "message": "Daily backup finished successfully",
      "service": "backup-job"
    }
    """
    try:
        logger.info(f"Notification from {notification.service}: {notification.title}")

        # Format message
        chat_id = notification.chat_id or TELEGRAM_CHAT_ID

        if notification.title:
            formatted_message = f"*{notification.title}*\n\n{notification.message}"
        else:
            formatted_message = notification.message

        if notification.service:
            formatted_message += f"\n\n_From: {notification.service}_"

        # Queue message for bot thread to send (avoids event loop issues)
        if notification_queue is None:
            raise HTTPException(status_code=503, detail="Bot not ready")

        notification_data = {
            "chat_id": chat_id,
            "text": formatted_message,
            "service": notification.service
        }
        assert notification_queue is not None
        notification_queue.put_nowait(notification_data)
        logger.info(f"Notification queued for delivery")

        return {"status": "queued", "message_id": None, "service": notification.service}

    except Exception as e:
        logger.error(f"Failed to queue notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_app.get("/api/commands")
async def get_commands():
    """List all available commands"""
    return {
        "commands": {
            "help": "Show available commands",
            "resume": "Get your resume/CV",
            "deploy": "Deploy a service (coming soon)",
            "backup": "Trigger backup (coming soon)",
            "expenses": "View expenses (coming soon)",
            "notion": "Notion integration (coming soon)",
            "github": "GitHub integration (coming soon)",
            "health": "Cluster health (coming soon)",
            "status": "System status (coming soon)",
        }
    }


async def hourly_heartbeat(application):
    """Send hourly heartbeat without notifying (silent background task)"""
    from datetime import datetime, timezone

    while True:
        try:
            await asyncio.sleep(3600)  # 1 hour
            timestamp = datetime.now(timezone.utc).isoformat()
            message = f"🫀 *Heartbeat*\n\nBot is alive at {timestamp}"

            await application.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode="MarkdownV2"
            )
            logger.info(f"Hourly heartbeat sent at {timestamp}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Failed to send hourly heartbeat: {e}")


async def process_notification_queue(application, queue: asyncio.Queue):
    """Process notifications from the queue in the bot's event loop"""
    while True:
        try:
            # Wait for notification (non-blocking in event loop)
            notification = await queue.get()
            try:
                msg = await application.bot.send_message(
                    chat_id=notification["chat_id"],
                    text=notification["text"],
                    parse_mode="Markdown"
                )
                logger.info(f"Notification sent from {notification['service']} (message_id={msg.message_id})")
            except Exception as e:
                logger.error(f"Failed to send notification from {notification['service']}: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error processing notification queue: {e}")


async def run_bot():
    """Run the Telegram bot"""
    global notification_queue
    logger.info("Starting Telegram bot...")

    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
        return

    # Create notification queue in this event loop
    notification_queue = asyncio.Queue()

    # Create bot application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("resume", resume_command))
    application.add_handler(CommandHandler("me", me_command))
    application.add_handler(CommandHandler("k8s_report", k8s_report_command))
    application.add_handler(CommandHandler("my_messages", my_messages_command))
    application.add_handler(CommandHandler("my_files", my_files_command))
    application.add_handler(CommandHandler("get_file", get_file_command))

    # Photo handler
    async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await handle_media(update, context, "photo")

    # Document handler
    async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await handle_media(update, context, "document")

    # Audio handler
    async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await handle_media(update, context, "audio")

    # Video handler
    async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await handle_media(update, context, "video")

    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.AUDIO, handle_audio))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))

    # Handle unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Handle regular messages
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Start bot
    await application.initialize()
    await application.start()

    # Send startup notification
    try:
        startup_msg = "🟢 Bot is online and ready to receive commands"
        await application.bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=startup_msg,
            parse_mode="Markdown"
        )
        logger.info("Startup notification sent")
    except Exception as e:
        logger.error(f"Failed to send startup notification: {e}")

    # Start background tasks
    queue_task = asyncio.create_task(process_notification_queue(application, notification_queue))
    heartbeat_task = asyncio.create_task(hourly_heartbeat(application))

    if application.updater:
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot is running and polling for updates")
    else:
        logger.error("Failed to initialize bot updater")

    # Keep running until interrupted
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Bot shutting down")
        queue_task.cancel()
        heartbeat_task.cancel()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    import threading
    import time

    # Run bot in background thread with its own event loop
    def run_bot_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_bot())
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()

    bot_thread = threading.Thread(target=run_bot_thread, daemon=True)
    bot_thread.start()

    # Give bot thread time to initialize before starting API
    time.sleep(2)

    # Start FastAPI server in main thread
    logger.info(f"Starting API server on port {API_PORT}")
    uvicorn.run(api_app, host="0.0.0.0", port=API_PORT, log_level="info")
