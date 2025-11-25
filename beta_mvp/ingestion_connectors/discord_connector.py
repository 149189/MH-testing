from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

import discord

from . import enqueue_normalized_post
from ..utils.language_processor import process_text_for_ingestion


def build_payload_from_message(message: discord.Message) -> Dict[str, Any]:
    attachments: List[Dict[str, Any]] = []
    for a in message.attachments:
        attachments.append(
            {
                "id": a.id,
                "filename": a.filename,
                "url": a.url,
                "content_type": a.content_type,
                "size": a.size,
            }
        )

    raw_text = message.content or ""
    lp = process_text_for_ingestion(raw_text)

    return {
        "platform": "discord",
        "platform_message_id": str(message.id),
        "timestamp": (
            message.created_at.isoformat() + "Z"
            if message.created_at
            else datetime.utcnow().isoformat() + "Z"
        ),
        "author": {
            "id": str(message.author.id),
            "username": str(message.author),
            "display_name": message.author.display_name,
            "bot": message.author.bot,
        },
        "context": {
            "guild_id": str(message.guild.id) if message.guild else None,
            "guild_name": message.guild.name if message.guild else None,
            "channel_id": str(message.channel.id),
            "channel_name": getattr(message.channel, "name", None),
        },
        "content": {
            "raw_text": raw_text,
            "attachments": attachments,
        },
        "language_analysis": lp,
        "meta": {
            "raw_type": str(message.type),
            "is_reply": message.reference is not None,
        },
    }


class DiscordIngestionClient(discord.Client):
    async def on_ready(self) -> None:
        print(f"[Discord] Logged in as {self.user} (id={self.user.id})")

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return

        payload = build_payload_from_message(message)
        enqueue_normalized_post(payload)
        print(f"[Discord] Enqueued message {message.id}")


def run_discord_bot() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN environment variable is not set")

    intents = discord.Intents.default()
    intents.message_content = True
    intents.messages = True
    intents.guilds = True

    client = DiscordIngestionClient(intents=intents)
    client.run(token)


if __name__ == "__main__":
    run_discord_bot()
