"""Tests for scripts/common/config.py."""
from __future__ import annotations

import os

import pytest

from scripts.common.config import get_env, load_config, require_env


# ---------------------------------------------------------------------------
# require_env
# ---------------------------------------------------------------------------

class TestRequireEnv:
    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_VAR", "my_value")
        assert require_env("MY_VAR") == "my_value"

    def test_raises_when_missing_and_no_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MISSING_VAR", raising=False)
        with pytest.raises(RuntimeError, match="MISSING_VAR"):
            require_env("MISSING_VAR")

    def test_returns_default_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ABSENT_VAR", raising=False)
        assert require_env("ABSENT_VAR", default="fallback") == "fallback"

    def test_env_takes_precedence_over_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRESENT_VAR", "actual")
        assert require_env("PRESENT_VAR", default="ignored") == "actual"

    def test_error_message_contains_var_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SPECIAL_VAR", raising=False)
        with pytest.raises(RuntimeError) as exc_info:
            require_env("SPECIAL_VAR")
        assert "SPECIAL_VAR" in str(exc_info.value)


# ---------------------------------------------------------------------------
# get_env
# ---------------------------------------------------------------------------

class TestGetEnv:
    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("G_VAR", "hello")
        assert get_env("G_VAR") == "hello"

    def test_returns_empty_string_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("G_MISSING", raising=False)
        assert get_env("G_MISSING") == ""

    def test_returns_custom_default_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("G_CUSTOM", raising=False)
        assert get_env("G_CUSTOM", default="custom") == "custom"

    def test_env_takes_precedence_over_custom_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("G_PRIO", "env_val")
        assert get_env("G_PRIO", default="default_val") == "env_val"


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_returns_dict(self) -> None:
        cfg = load_config()
        assert isinstance(cfg, dict)

    def test_contains_current_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_TEST_KEY", "test_value")
        cfg = load_config()
        assert cfg.get("MY_TEST_KEY") == "test_value"

    def test_dotenv_path_none_does_not_crash(self) -> None:
        # Should never raise even if no .env file exists
        cfg = load_config(dotenv_path=None)
        assert isinstance(cfg, dict)

    def test_nonexistent_dotenv_path_does_not_crash(self, tmp_path: Path) -> None:
        cfg = load_config(dotenv_path=str(tmp_path / "nonexistent.env"))
        assert isinstance(cfg, dict)

    def test_loads_from_dotenv_file(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("DOTENV_LOADED_VAR=dotenv_value\n", encoding="utf-8")
        # Ensure the var isn't already set
        os.environ.pop("DOTENV_LOADED_VAR", None)
        cfg = load_config(dotenv_path=str(env_file))
        assert cfg.get("DOTENV_LOADED_VAR") == "dotenv_value"
        # Clean up
        os.environ.pop("DOTENV_LOADED_VAR", None)

    def test_existing_env_takes_precedence_over_dotenv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("PRIO_VAR=from_file\n", encoding="utf-8")
        monkeypatch.setenv("PRIO_VAR", "from_env")
        cfg = load_config(dotenv_path=str(env_file))
        assert cfg.get("PRIO_VAR") == "from_env"
        # Clean up
        os.environ.pop("PRIO_VAR", None)
