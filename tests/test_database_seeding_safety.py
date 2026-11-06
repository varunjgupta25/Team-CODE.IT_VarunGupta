import os
import subprocess
import sys
import pytest
from seed import seed_database, auto_seed_if_empty
from core.config import settings


def test_seed_rejected_in_production(monkeypatch):
    """Verify that seed_database raises RuntimeError if ENV is production."""
    monkeypatch.setattr(settings, "ENV", "production")
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        seed_database(confirm=True)
    assert "prohibited in the production environment" in str(exc_info.value)


def test_seed_rejected_in_staging_by_default(monkeypatch):
    """Verify that seed_database raises RuntimeError in staging unless ALLOW_STAGING_SEED=true."""
    monkeypatch.setattr(settings, "ENV", "staging")
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.delenv("ALLOW_STAGING_SEED", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        seed_database(confirm=True)
    assert "ALLOW_STAGING_SEED=true" in str(exc_info.value)


def test_seed_allowed_in_staging_with_explicit_opt_in(monkeypatch):
    """Verify that staging seeding proceeds if ALLOW_STAGING_SEED=true and confirm=True."""
    monkeypatch.setattr(settings, "ENV", "staging")
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.setenv("ALLOW_STAGING_SEED", "true")
    monkeypatch.setenv("ALLOW_SEEDING", "true")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    # Should not raise
    seed_database(clear_existing=False, confirm=True)


def test_seed_rejected_in_dev_without_opt_in(monkeypatch):
    """Verify that development seed raises RuntimeError if neither confirm nor ALLOW_SEEDING is set."""
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.delenv("ALLOW_SEEDING", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        seed_database(clear_existing=False, confirm=False)
    assert "ALLOW_SEEDING=true" in str(exc_info.value)


def test_seed_allowed_in_dev_with_opt_in(monkeypatch):
    """Verify that development seed succeeds with confirm=True or ALLOW_SEEDING=true."""
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("ALLOW_SEEDING", "true")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    seed_database(clear_existing=False, confirm=True)


def test_destructive_seed_rejected_without_confirmation(monkeypatch):
    """Verify that clear_existing=True raises RuntimeError if ALLOW_DESTRUCTIVE_SEED is not set."""
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("ALLOW_SEEDING", "true")
    monkeypatch.delenv("ALLOW_DESTRUCTIVE_SEED", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        seed_database(clear_existing=True, confirm=True)
    assert "ALLOW_DESTRUCTIVE_SEED=true" in str(exc_info.value)


def test_destructive_seed_allowed_with_confirmation(monkeypatch):
    """Verify that clear_existing=True succeeds when ALLOW_DESTRUCTIVE_SEED=true."""
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("ALLOW_SEEDING", "true")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_SEED", "true")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    seed_database(clear_existing=True, confirm=True)


def test_cli_execution_safety_abort():
    """Verify that directly running `python seed.py` without flags exits with error code 1."""
    env = os.environ.copy()
    env.pop("PYTEST_CURRENT_TEST", None)
    env.pop("ALLOW_SEEDING", None)
    env["ENV"] = "development"

    res = subprocess.run(
        [sys.executable, "seed.py"],
        capture_output=True,
        text=True,
        env=env
    )
    assert res.returncode == 1
    assert "Seeding aborted" in res.stderr or "ALLOW_SEEDING=true" in res.stderr


def test_auto_seed_startup_protection(monkeypatch):
    """Verify auto_seed_if_empty strictly returns False in production and staging."""
    monkeypatch.setattr(settings, "ENV", "production")
    assert auto_seed_if_empty() is False

    monkeypatch.setattr(settings, "ENV", "staging")
    assert auto_seed_if_empty() is False

