from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


@dataclass(frozen=True)
class PaymentRequest:
    authority: str
    redirect_url: str
    provider_data: dict


@dataclass(frozen=True)
class PaymentVerification:
    successful: bool
    reference: str
    provider_data: dict


class PaymentProvider(Protocol):
    name: str

    def request(self, *, amount: int, callback_url: str, description: str) -> PaymentRequest: ...

    def verify(self, *, authority: str, amount: int) -> PaymentVerification: ...


class MockPaymentProvider:
    """Deterministic local provider which can be replaced by a real gateway adapter."""

    name = "mock"

    def request(self, *, amount: int, callback_url: str, description: str) -> PaymentRequest:
        authority = f"mock-{uuid4().hex}"
        return PaymentRequest(
            authority=authority,
            redirect_url=f"{callback_url}?authority={authority}",
            provider_data={"amount": amount, "description": description},
        )

    def verify(self, *, authority: str, amount: int) -> PaymentVerification:
        return PaymentVerification(
            successful=authority.startswith("mock-"),
            reference=f"ref-{authority.removeprefix('mock-')[:16]}",
            provider_data={"verified_amount": amount},
        )


def get_payment_provider(name: str = "mock") -> PaymentProvider:
    if name == "mock":
        return MockPaymentProvider()
    raise ValueError("ارائه‌دهنده پرداخت پشتیبانی نمی‌شود.")
