import os
import subprocess
import sys
import pytest
from seed import seed_database, auto_seed_if_empty
from core.config import settings
from core.database import db


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


def test_destructive_staging_always_rejected(monkeypatch):
    """Verify that destructive seeding (clear_existing=True) is strictly prohibited in staging."""
    monkeypatch.setattr(settings, "ENV", "staging")
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.setenv("ALLOW_STAGING_SEED", "true")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_SEED", "true")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        seed_database(clear_existing=True, confirm=True, confirm_clear=True)
    assert "strictly prohibited in the staging environment" in str(exc_info.value)


def test_seed_allowed_in_staging_with_explicit_opt_in(monkeypatch):
    """Verify that staging non-destructive seeding proceeds if ALLOW_STAGING_SEED=true and confirm=True."""
    monkeypatch.setattr(settings, "ENV", "staging")
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.setenv("ALLOW_STAGING_SEED", "true")
    monkeypatch.setenv("ALLOW_SEEDING", "true")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    seed_database(clear_existing=False, confirm=True)


def test_unknown_environment_rejected_fail_closed(monkeypatch):
    """Verify that an unknown or ambiguous environment fails closed and raises RuntimeError."""
    monkeypatch.setattr(settings, "ENV", "unrecognized_cluster")
    monkeypatch.setenv("ENV", "unrecognized_cluster")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        seed_database(confirm=True)
    assert "unknown or ambiguous environment" in str(exc_info.value)


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
    """Verify that clear_existing=True raises RuntimeError without explicit confirmation."""
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("ALLOW_SEEDING", "true")
    monkeypatch.delenv("ALLOW_DESTRUCTIVE_SEED", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        seed_database(clear_existing=True, confirm=True, confirm_clear=False)
    assert "Destructive database clearing requires explicit confirmation" in str(exc_info.value)


def test_destructive_seed_allowed_with_confirmation(monkeypatch):
    """Verify that clear_existing=True succeeds when explicit confirmations are provided."""
    monkeypatch.setattr(settings, "ENV", "development")
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("ALLOW_SEEDING", "true")
    monkeypatch.setenv("ALLOW_DESTRUCTIVE_SEED", "true")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    seed_database(clear_existing=True, confirm=True, confirm_clear=True)


def test_default_cli_invocation_shows_usage_without_modifications():
    """Verify that running `python seed.py` with zero arguments displays safe usage and exits 0."""
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
    assert res.returncode == 0
    assert "Safe default execution engaged: No database modifications made." in res.stdout
    assert "--confirm-seed" in res.stdout


def test_cli_destructive_dual_confirmation():
    """Verify CLI requires both --force-clear and --confirm-clear for destructive seeding."""
    env = os.environ.copy()
    env.pop("PYTEST_CURRENT_TEST", None)
    env.pop("ALLOW_SEEDING", None)
    env["ENV"] = "development"

    # 1. Missing confirm-clear -> rejected
    res_partial = subprocess.run(
        [sys.executable, "seed.py", "--confirm-seed", "--clear", "--force-clear"],
        capture_output=True,
        text=True,
        env=env
    )
    assert res_partial.returncode == 1
    assert "Destructive database clearing requires explicit confirmation" in res_partial.stderr

    # 2. Both flags present -> accepted
    res_full = subprocess.run(
        [sys.executable, "seed.py", "--confirm-seed", "--force-clear", "--confirm-clear"],
        capture_output=True,
        text=True,
        env=env
    )
    assert res_full.returncode == 0
    assert "Seeding complete!" in res_full.stdout


def test_module_import_without_side_effects():
    """Verify that importing seed module has no side effects and does not touch the database."""
    # Ensure imported module does not clear collections automatically
    initial_count = len(db.list_collection("workers"))
    import importlib
    import seed
    importlib.reload(seed)
    after_count = len(db.list_collection("workers"))
    assert initial_count == after_count


def test_auto_seed_startup_protection(monkeypatch):
    """Verify auto_seed_if_empty strictly returns False in production and staging."""
    monkeypatch.setattr(settings, "ENV", "production")
    assert auto_seed_if_empty() is False

    monkeypatch.setattr(settings, "ENV", "staging")
    assert auto_seed_if_empty() is False
