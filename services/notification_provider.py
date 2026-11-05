import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx
from core.config import settings


class NotificationProvider(ABC):
    """
    Abstract notification provider for emergency alerts (SMS / WhatsApp).
    All credentials come strictly from environment variables.
    """

    @abstractmethod
    def send_alert(self, to_phone: str, message: str, channel: str = "sms") -> Tuple[bool, Optional[str]]:
        """
        Sends an alert message to to_phone via channel ('sms' or 'whatsapp').
        Returns (success: bool, error_message: Optional[str]).
        """
        pass


class ConsoleProvider(NotificationProvider):
    """
    Zero-dependency, offline provider for development and testing.
    Captures sent notifications in an in-memory audit list for test assertions.
    """

    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.should_fail: bool = False

    def send_alert(self, to_phone: str, message: str, channel: str = "sms") -> Tuple[bool, Optional[str]]:
        if self.should_fail:
            return False, "Simulated notification provider delivery failure"

        record = {
            "to": to_phone,
            "message": message,
            "channel": channel,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.sent_messages.append(record)
        print(f"[SOS Notification Provider - {channel.upper()}] To: {to_phone} | Msg: {message}")
        return True, None

    def clear(self):
        self.sent_messages.clear()
        self.should_fail = False


class TwilioProvider(NotificationProvider):
    """
    Twilio provider for production SMS and WhatsApp delivery.
    Note: Standard Indian SMS requires DLT (Distributed Ledger Technology) template registration.
    For demos and hackathons, Twilio WhatsApp Sandbox is the recommended immediate zero-registration path.
    """

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_phone: Optional[str] = None,
        whatsapp_from: Optional[str] = None
    ):
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
        self.from_phone = from_phone or settings.TWILIO_FROM_PHONE
        self.whatsapp_from = whatsapp_from or settings.TWILIO_WHATSAPP_FROM

    def send_alert(self, to_phone: str, message: str, channel: str = "sms") -> Tuple[bool, Optional[str]]:
        if not (self.account_sid and self.auth_token):
            return False, "Twilio credentials unconfigured on server"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

        if channel == "whatsapp":
            from_sender = f"whatsapp:{self.whatsapp_from or self.from_phone}"
            to_recipient = f"whatsapp:{to_phone}"
        else:
            from_sender = self.from_phone
            to_recipient = to_phone

        if not from_sender:
            return False, f"Twilio from_phone unconfigured for channel '{channel}'"

        data = {
            "From": from_sender,
            "To": to_recipient,
            "Body": message
        }

        try:
            with httpx.Client(timeout=6.0) as client:
                res = client.post(url, auth=(self.account_sid, self.auth_token), data=data)
                if res.status_code in (200, 201):
                    return True, None
                err_detail = res.json().get("message", res.text[:120]) if res.content else f"HTTP {res.status_code}"
                return False, f"Twilio API error {res.status_code}: {err_detail}"
        except Exception as exc:
            return False, f"Twilio network/connection error: {str(exc)}"


# Global default provider
_default_provider: Optional[NotificationProvider] = None


def get_notification_provider() -> NotificationProvider:
    global _default_provider
    if _default_provider is None:
        if settings.NOTIFICATION_PROVIDER.lower() == "twilio":
            _default_provider = TwilioProvider()
        else:
            _default_provider = ConsoleProvider()
    return _default_provider


def set_notification_provider(provider: Optional[NotificationProvider]) -> None:
    """Helper for testing to inject mock/console providers."""
    global _default_provider
    _default_provider = provider
