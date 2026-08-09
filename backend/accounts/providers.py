import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SMSProvider(ABC):
    @abstractmethod
    def send_otp(self, phone: str, code: str) -> str:
        """Send an OTP and return the provider reference."""

    @abstractmethod
    def send_message(self, phone: str, message: str) -> str:
        """Send a transactional message and return the provider reference."""


class MockSMSProvider(SMSProvider):
    def send_otp(self, phone: str, code: str) -> str:
        logger.info("Mock OTP for %s: %s", phone, code)
        return f"mock-{phone[-4:]}"

    def send_message(self, phone: str, message: str) -> str:
        logger.info("Mock SMS for %s: %s", phone, message)
        return f"mock-message-{phone[-4:]}"


def get_sms_provider(name: str) -> SMSProvider:
    providers = {"mock": MockSMSProvider}
    try:
        return providers[name]()
    except KeyError as exc:
        raise ValueError(f"ارائه‌دهنده پیامک ناشناخته است: {name}") from exc
