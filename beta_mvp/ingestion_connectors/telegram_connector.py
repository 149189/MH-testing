from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from telegram import Message, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from . import enqueue_normalized_post
from ..utils.language_processor import process_text_for_ingestion


def build_payload_from_message(msg: Message) -> Dict[str, Any]:
    media: List[Dict[str, Any]] = []

    if msg.photo:
        largest = msg.photo[-1]
        media.append(
            {
                "type": "photo",
                "file_id": largest.file_id,
                "width": largest.width,
                "height": largest.height,
            }
        )

    if msg.document:
        media.append(
            {
                "type": "document",
                "file_id": msg.document.file_id,
                "file_name": msg.document.file_name,
                "mime_type": msg.document.mime_type,
                "file_size": msg.document.file_size,
            }
        )

    forward_from: Optional[Dict[str, Any]] = None
    if msg.forward_from:
        forward_from = {
            "id": msg.forward_from.id,
            "username": msg.forward_from.username,
            "first_name": msg.forward_from.first_name,
            "last_name": msg.forward_from.last_name,
        }
    elif msg.forward_from_chat:
        forward_from = {
            "id": msg.forward_from_chat.id,
            "title": msg.forward_from_chat.title,
            "type": msg.forward_from_chat.type,
        }

    raw_text = msg.text or msg.caption or ""
    lp = process_text_for_ingestion(raw_text)

    return {
        "platform": "telegram",
        "platform_message_id": msg.message_id,
        "timestamp": (
            msg.date.isoformat() + "Z"
            if msg.date
            else datetime.utcnow().isoformat() + "Z"
        ),
        "author": {
            "id": msg.from_user.id if msg.from_user else None,
            "username": msg.from_user.username if msg.from_user else None,
            "first_name": msg.from_user.first_name if msg.from_user else None,
            "last_name": msg.from_user.last_name if msg.from_user else None,
            "is_bot": msg.from_user.is_bot if msg.from_user else None,
        },
        "context": {
            "chat_id": msg.chat.id,
            "chat_title": msg.chat.title,
            "chat_type": msg.chat.type,
            "is_reply": msg.reply_to_message is not None,
            "forward_from": forward_from,
        },
        "content": {
            "raw_text": raw_text,
            "media": media,
        },
        "language_analysis": lp,
        "meta": {
            "raw": msg.to_dict(),
        },
    }


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    payload = build_payload_from_message(update.message)
    enqueue_normalized_post(payload)
    print(f"[Telegram] Enqueued message {update.message.message_id}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text("Hello! Send me a post to be processed.")


def run_telegram_bot() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(
        MessageHandler(
            filters.ALL & ~filters.StatusUpdate.ALL,
            handle_message,
        )
    )

    print("[Telegram] Bot polling started")
    app.run_polling()


if __name__ == "__main__":
    run_telegram_bot()
