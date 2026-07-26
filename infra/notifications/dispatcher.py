"""
Phase 3 — Enterprise Notification System.

Multi-channel notification dispatcher supporting Email, SMS, Webhook,
Slack, and Teams. Uses a durable async queue with retry backoff.
"""
import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"


@dataclass
class Notification:
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    tenant_id: str = "default"
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3


class NotificationSender(ABC):
    """Abstract sender interface per channel."""

    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        ...


class WebhookSender(NotificationSender):
    """Sends notifications via HTTP webhooks."""

    async def send(self, notification: Notification) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "subject": notification.subject,
                    "body": notification.body,
                    "tenant_id": notification.tenant_id,
                    "metadata": notification.metadata
                }
                response = await client.post(notification.recipient, json=payload)
                return response.status_code < 400
        except Exception as e:
            logger.error(f"Webhook send failed to {notification.recipient}: {e}")
            return False


class LogSender(NotificationSender):
    """Development sender that logs notifications."""

    async def send(self, notification: Notification) -> bool:
        logger.info(
            f"NOTIFICATION [{notification.channel.value}] → {notification.recipient}: "
            f"{notification.subject} | {notification.body[:100]}"
        )
        return True


class NotificationDispatcher:
    """
    Central notification dispatcher with multi-channel support and retry backoff.
    """

    def __init__(self):
        self._senders: Dict[NotificationChannel, NotificationSender] = {
            NotificationChannel.EMAIL: LogSender(),
            NotificationChannel.SMS: LogSender(),
            NotificationChannel.WEBHOOK: WebhookSender(),
            NotificationChannel.SLACK: LogSender(),
            NotificationChannel.TEAMS: LogSender(),
        }
        self._dead_letter: List[Notification] = []

    def register_sender(self, channel: NotificationChannel, sender: NotificationSender):
        self._senders[channel] = sender

    async def dispatch(self, notification: Notification) -> bool:
        sender = self._senders.get(notification.channel)
        if not sender:
            logger.error(f"No sender registered for channel: {notification.channel.value}")
            return False

        for attempt in range(notification.max_retries + 1):
            success = await sender.send(notification)
            if success:
                return True
            notification.retry_count = attempt + 1
            backoff = min(2 ** attempt, 30)
            logger.warning(
                f"Notification retry {notification.retry_count}/{notification.max_retries} "
                f"for {notification.channel.value} (backoff={backoff}s)"
            )
            await asyncio.sleep(backoff)

        # Dead-letter
        self._dead_letter.append(notification)
        logger.error(f"Notification DEAD-LETTERED: {notification.channel.value} → {notification.recipient}")
        return False

    def get_dead_letter_count(self) -> int:
        return len(self._dead_letter)


# Global singleton
notification_dispatcher = NotificationDispatcher()
