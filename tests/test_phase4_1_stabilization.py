import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from core.config import settings
from core.auth import get_current_user
from seed import auto_seed_if_empty


def test_admin_custom_claim_resolution(monkeypatch):
    """Verify that decoded Firebase ID token with custom claim 'admin: True' maps to 'admin' role."""
    from fastapi.security import HTTPAuthorizationCredentials

    mock_credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="mock.signed.jwt"
    )

    mock_decoded = {
        "uid": "firebase_admin_user_999",
        "sub": "firebase_admin_user_999",
        "admin": True,  # Firebase Custom Claim convention
        "email": "admin@repairbuddy.in"
    }

    # Mock firebase auth verify_id_token
    with patch("core.auth.firebase_auth.verify_id_token", return_value=mock_decoded), \
         patch("core.auth.FIREBASE_AUTH_AVAILABLE", True), \
         patch("core.auth.firebase_admin._apps", [True]):
        user = get_current_user(mock_credentials)
        assert user["role"] == "admin"
        assert user["uid"] == "firebase_admin_user_999"


def test_auto_seed_disabled_in_production(monkeypatch):
    """Verify that auto_seed_if_empty refuses to seed when ENV=production or staging."""
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setattr(settings, "AUTO_SEED", True)
    assert auto_seed_if_empty() is False

    monkeypatch.setattr(settings, "ENV", "staging")
    assert auto_seed_if_empty() is False


def test_dev_tokens_strictly_rejected_in_production(monkeypatch):
    """Verify that dev/mock tokens are strictly rejected with 401 in production."""
    from fastapi.security import HTTPAuthorizationCredentials
    monkeypatch.setattr(settings, "ENV", "production")

    dev_credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="token-customer-cust_priya"
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(dev_credentials)
    assert exc_info.value.status_code == 401
    assert "strictly prohibited" in exc_info.value.detail.lower()


def test_cors_production_no_arbitrary_regex(monkeypatch):
    """Verify production CORS rejects wildcard vercel.app regex and requires explicit origins."""
    from core.config import Settings
    prod_settings = Settings(
        ENV="production",
        CUSTOMER_APP_ORIGIN="https://repair-buddy-customer.vercel.app",
        PARTNER_APP_ORIGIN="https://repair-buddy-partner.vercel.app"
    )
    assert prod_settings.CORS_ORIGIN_REGEX is None
    assert "https://repair-buddy-customer.vercel.app" in prod_settings.ALLOWED_ORIGINS
    assert "https://repair-buddy-partner.vercel.app" in prod_settings.ALLOWED_ORIGINS
    assert "http://localhost:5173" not in prod_settings.ALLOWED_ORIGINS

