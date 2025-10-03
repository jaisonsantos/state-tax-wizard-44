import uuid
from types import SimpleNamespace

import uuid
from types import SimpleNamespace

import pytest
import stripe

from app.core.config import settings
from app.models.models import Store, StoreSetting, User
from app.services.stripe_service import StripeCustomerMissingError, StripeService


@pytest.fixture(autouse=True)
def reset_stripe_api_key(monkeypatch):
    monkeypatch.setattr(stripe, "api_key", None, raising=False)


def _build_store(db_session, *, contact_email: str | None) -> Store:
    store = Store(
        id=uuid.uuid4(),
        name="Test Store",
        platform="shopify",
        domain="test-store.example",
        country="US",
        state="MN",
        contact_email=contact_email,
    )
    setting = StoreSetting(
        store_id=store.id,
        enable_mn=True,
        enable_co=True,
        absorb_fee=False,
        label_override="Delivery Fee",
        plan="starter",
    )
    store.settings = setting
    db_session.add(store)
    db_session.add(setting)
    db_session.commit()
    return store


def test_create_checkout_session_uses_store_contact_email(db_session, monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test", raising=False)

    store = _build_store(db_session, contact_email="owner@example.com")

    captured = {}

    def fake_customer_create(**kwargs):
        captured["customer_email"] = kwargs["email"]
        return SimpleNamespace(id="cus_test")

    def fake_session_create(**kwargs):
        captured["session_metadata"] = kwargs["metadata"]
        return SimpleNamespace(id="cs_test", url="https://checkout.example")

    monkeypatch.setattr(stripe.Customer, "create", staticmethod(fake_customer_create))
    monkeypatch.setattr(stripe.checkout.Session, "create", staticmethod(fake_session_create))

    result = StripeService.create_checkout_session(
        db=db_session,
        store_id=str(store.id),
        price_id="price_test",
        success_url="https://app.example/success",
        cancel_url="https://app.example/cancel",
        plan_tier="pro",
    )

    assert result["session_id"] == "cs_test"
    assert captured["customer_email"] == "owner@example.com"
    assert captured["session_metadata"]["store_id"] == str(store.id)

    db_session.refresh(store)
    assert store.stripe_customer_id == "cus_test"
    assert store.contact_email == "owner@example.com"


def test_create_checkout_session_falls_back_to_user_email(db_session, monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test", raising=False)

    store = _build_store(db_session, contact_email=None)
    user = User(id=uuid.uuid4(), email="member@example.com")
    store.users.append(user)
    db_session.add(user)
    db_session.commit()

    captured = {}

    def fake_customer_create(**kwargs):
        captured["customer_email"] = kwargs["email"]
        return SimpleNamespace(id="cus_member")

    def fake_session_create(**kwargs):
        return SimpleNamespace(id="cs_member", url="https://checkout.example/member")

    monkeypatch.setattr(stripe.Customer, "create", staticmethod(fake_customer_create))
    monkeypatch.setattr(stripe.checkout.Session, "create", staticmethod(fake_session_create))

    result = StripeService.create_checkout_session(
        db=db_session,
        store_id=str(store.id),
        price_id="price_test",
        success_url="https://app.example/success",
        cancel_url="https://app.example/cancel",
        plan_tier="starter",
    )

    assert result["session_id"] == "cs_member"
    assert captured["customer_email"] == "member@example.com"

    db_session.refresh(store)
    assert store.contact_email == "member@example.com"


def test_create_portal_session_missing_customer(db_session, monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test", raising=False)

    store = _build_store(db_session, contact_email="owner@example.com")

    with pytest.raises(StripeCustomerMissingError):
        StripeService.create_portal_session(
            db=db_session,
            store_id=str(store.id),
            return_url="https://app.example/billing",
        )
