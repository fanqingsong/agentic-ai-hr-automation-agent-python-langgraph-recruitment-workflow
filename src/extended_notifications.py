# ============================================================================
# EXTENDED NOTIFICATIONS
# ============================================================================

"""
Extended notification channels: Telegram, Discord, and more
"""

import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# NOTIFICATION CHANNELS
# ============================================================================

class NotificationChannel(str, Enum):
    """Available notification channels"""
    EMAIL = "email"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WEBHOOK = "webhook"


# ============================================================================
# TELEGRAM NOTIFICATIONS
# ============================================================================

class TelegramNotifier:
    """
    Send notifications via Telegram Bot API
    """

    def __init__(self, bot_token: str):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token from @BotFather
        """
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True
    ) -> Dict[str, Any]:
        """
        Send text message via Telegram

        Args:
            chat_id: Target chat ID (can be user, group, or channel)
            text: Message text
            parse_mode: HTML or Markdown
            disable_web_page_preview: Disable link previews

        Returns:
            API response
        """
        url = f"{self.base_url}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()

                if result.get("ok"):
                    logger.info(f"Telegram message sent to {chat_id}")
                    return {
                        "success": True,
                        "message_id": result.get("result", {}).get("message_id"),
                        "channel": "telegram"
                    }
                else:
                    logger.error(f"Telegram API error: {result.get('description')}")
                    return {
                        "success": False,
                        "error": result.get("description"),
                        "channel": "telegram"
                    }

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "channel": "telegram"
            }

    async def send_candidate_alert(
        self,
        chat_id: str,
        candidate_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send formatted candidate alert

        Args:
            chat_id: Target chat ID
            candidate_data: Candidate information

        Returns:
            API response
        """
        score = candidate_data.get("evaluation_score", 0)
        evaluation = candidate_data.get("evaluation", {})

        # Format message
        message = f"""
🔔 <b>New High-Scoring Candidate Alert</b>

👤 <b>Candidate:</b> {candidate_data.get('candidate_name')}
📧 <b>Email:</b> {candidate_data.get('candidate_email')}
💼 <b>Position:</b> {candidate_data.get('job_title')}

📊 <b>Score:</b> {score}/100
✅ <b>Decision:</b> {evaluation.get('decision', 'N/A')}

📝 <b>Summary:</b>
{candidate_data.get('summary', 'N/A')[:200]}...

🔗 <b>CV Link:</b> {candidate_data.get('cv_link', 'N/A')}
⏰ <b>Time:</b> {candidate_data.get('timestamp', 'N/A')}
        """.strip()

        return await self.send_message(chat_id, message)


# ============================================================================
# DISCORD NOTIFICATIONS
# ============================================================================

class DiscordNotifier:
    """
    Send notifications via Discord Webhooks
    """

    def __init__(self, webhook_url: str):
        """
        Initialize Discord notifier

        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url

    async def send_message(
        self,
        content: str,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        embeds: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Send message via Discord webhook

        Args:
            content: Message content
            username: Override username
            avatar_url: Override avatar
            embeds: List of embed objects

        Returns:
            Response status
        """
        payload = {"content": content}

        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url
        if embeds:
            payload["embeds"] = embeds

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()

                logger.info(f"Discord message sent via webhook")
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "channel": "discord"
                }

        except Exception as e:
            logger.error(f"Failed to send Discord message: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "channel": "discord"
            }

    async def send_candidate_alert(
        self,
        candidate_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send formatted candidate alert with embed

        Args:
            candidate_data: Candidate information

        Returns:
            Response status
        """
        score = candidate_data.get("evaluation_score", 0)
        evaluation = candidate_data.get("evaluation", {})

        # Determine color based on score
        color = 0x00FF00 if score >= 70 else 0xFFFF00 if score >= 50 else 0xFF0000

        # Create embed
        embed = {
            "title": "🎉 New High-Scoring Candidate",
            "color": color,
            "fields": [
                {
                    "name": "👤 Candidate",
                    "value": candidate_data.get("candidate_name"),
                    "inline": True
                },
                {
                    "name": "📧 Email",
                    "value": candidate_data.get("candidate_email"),
                    "inline": True
                },
                {
                    "name": "💼 Position",
                    "value": candidate_data.get("job_title"),
                    "inline": True
                },
                {
                    "name": "📊 Score",
                    "value": f"{score}/100",
                    "inline": True
                },
                {
                    "name": "✅ Decision",
                    "value": evaluation.get("decision", "N/A"),
                    "inline": True
                },
                {
                    "name": "📝 Summary",
                    "value": candidate_data.get("summary", "N/A")[:300] + "...",
                    "inline": False
                }
            ],
            "url": candidate_data.get("cv_link"),
            "timestamp": datetime.now().isoformat()
        }

        content = f"@everyone A new candidate with score {score}/100 has been evaluated!"

        return await self.send_message(
            content=content,
            username="HR Automation Bot",
            embeds=[embed]
        )


# ============================================================================
# NOTIFICATION MANAGER
# ============================================================================

class NotificationManager:
    """
    Unified notification manager for all channels
    """

    def __init__(self):
        """Initialize notification manager"""
        self.channels: Dict[str, Any] = {}
        self.default_channels: list = []

    def register_telegram(self, bot_token: str, default_chat_id: str = None):
        """Register Telegram notifier"""
        self.channels["telegram"] = TelegramNotifier(bot_token)
        if default_chat_id:
            self.default_channels.append(("telegram", default_chat_id))
        logger.info("Telegram notifier registered")

    def register_discord(self, webhook_url: str):
        """Register Discord notifier"""
        self.channels["discord"] = DiscordNotifier(webhook_url)
        self.default_channels.append(("discord", None))
        logger.info("Discord notifier registered")

    async def send_to_channel(
        self,
        channel: NotificationChannel,
        target: str,
        message_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send notification to specific channel

        Args:
            channel: Notification channel
            target: Target (chat_id, webhook_url, etc.)
            message_data: Message payload

        Returns:
            Send result
        """
        if channel.value not in self.channels:
            logger.error(f"Channel not registered: {channel.value}")
            return {
                "success": False,
                "error": f"Channel not registered: {channel.value}",
                "channel": channel.value
            }

        notifier = self.channels[channel.value]

        if channel == NotificationChannel.TELEGRAM:
            return await notifier.send_candidate_alert(target, message_data)

        elif channel == NotificationChannel.DISCORD:
            return await notifier.send_candidate_alert(message_data)

        else:
            logger.error(f"Unsupported channel: {channel.value}")
            return {
                "success": False,
                "error": f"Unsupported channel: {channel.value}",
                "channel": channel.value
            }

    async def broadcast(
        self,
        message_data: Dict[str, Any],
        channels: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Broadcast notification to multiple channels

        Args:
            message_data: Message payload
            channels: List of (channel, target) tuples

        Returns:
            Combined results
        """
        if channels is None:
            channels = self.default_channels

        results = {}
        for channel_name, target in channels:
            try:
                channel = NotificationChannel(channel_name)
                result = await self.send_to_channel(channel, target, message_data)
                results[channel_name] = result
            except Exception as e:
                logger.error(f"Failed to send to {channel_name}: {str(e)}")
                results[channel_name] = {
                    "success": False,
                    "error": str(e)
                }

        return {
            "total_channels": len(channels),
            "successful": sum(1 for r in results.values() if r.get("success")),
            "results": results
        }


# ============================================================================
# LANGGRAPH NOTIFICATION NODES
# ============================================================================

async def send_extended_notifications_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node for sending extended notifications

    Args:
        state: Agent state

    Returns:
        Updated state
    """
    # Only notify if score meets threshold
    score = state.get("evaluation_score", 0)

    if score < 70:
        logger.info(f"Score {score} below threshold, skipping extended notifications")
        return state

    # Initialize notification manager
    manager = NotificationManager()

    # Register channels from environment
    import os

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")

    if telegram_token and telegram_chat_id:
        manager.register_telegram(telegram_token, telegram_chat_id)

    if discord_webhook:
        manager.register_discord(discord_webhook)

    # Broadcast to all registered channels
    results = await manager.broadcast(state)

    # Log results
    logger.info(f"Extended notifications sent: {results.get('successful')}/{results.get('total_channels')} successful")

    # Update state
    state["extended_notifications_sent"] = True
    state["extended_notification_results"] = results

    return state


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

# Global notification manager instance
notification_manager = NotificationManager()


def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance"""
    return notification_manager


def setup_notifications_from_env():
    """
    Setup notification channels from environment variables
    """
    import os

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")

    if telegram_token and telegram_chat_id:
        notification_manager.register_telegram(telegram_token, telegram_chat_id)
        logger.info("✅ Telegram notifications enabled")

    if discord_webhook:
        notification_manager.register_discord(discord_webhook)
        logger.info("✅ Discord notifications enabled")


async def send_candidate_notification(
    candidate_data: Dict[str, Any],
    channels: Optional[list] = None
) -> Dict[str, Any]:
    """
    Send candidate notification to specified channels

    Args:
        candidate_data: Candidate information
        channels: Optional list of (channel, target) tuples

    Returns:
        Combined results
    """
    return await notification_manager.broadcast(candidate_data, channels)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import asyncio
    import os

    async def example_extended_notifications():
        """Example of extended notifications"""

        # Setup from environment
        setup_notifications_from_env()

        # Example candidate data
        candidate = {
            "candidate_name": "John Doe",
            "candidate_email": "john@example.com",
            "job_title": "Senior AI Engineer",
            "evaluation_score": 85,
            "evaluation": {
                "decision": "Strong Hire",
                "reasoning": "Excellent match..."
            },
            "summary": "Experienced software engineer with 5 years...",
            "cv_link": "https://storage.googleapis.com/...",
            "timestamp": datetime.now().isoformat()
        }

        # Send notifications
        results = await send_candidate_notification(candidate)

        print(f"Notification results: {results}")

    # asyncio.run(example_extended_notifications())
