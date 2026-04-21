"""Tests for scripts/common/logger.py."""
from __future__ import annotations

import logging
import os

import pytest

import scripts.common.logger as logger_module
from scripts.common.logger import get_logger


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------

class TestGetLogger:
    def setup_method(self) -> None:
        # Reset the module-level flag so each test gets a clean slate.
        logger_module._root_configured = False
        # Clear all handlers from root logger to avoid cross-test bleed.
        root = logging.getLogger()
        root.handlers.clear()

    def test_returns_logger_with_correct_name(self) -> None:
        log = get_logger("my.module")
        assert log.name == "my.module"

    def test_returns_logging_logger_instance(self) -> None:
        log = get_logger("some.logger")
        assert isinstance(log, logging.Logger)

    def test_root_configured_once(self) -> None:
        assert not logger_module._root_configured
        get_logger("first")
        assert logger_module._root_configured
        get_logger("second")  # should not re-configure
        assert logger_module._root_configured

    def test_explicit_level_applied(self) -> None:
        log = get_logger("debug.logger", level=logging.DEBUG)
        assert log.level == logging.DEBUG

    def test_no_explicit_level_leaves_logger_level_default(self) -> None:
        log = get_logger("default.logger")
        # Logger level defaults to NOTSET (0) unless explicitly set
        assert log.level == logging.NOTSET

    def test_log_level_env_var_respected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        logger_module._root_configured = False
        logging.getLogger().handlers.clear()
        get_logger("env.test")
        assert logging.getLogger().level == logging.WARNING

    def test_invalid_log_level_falls_back_to_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "NOTAVALIDLEVEL")
        logger_module._root_configured = False
        logging.getLogger().handlers.clear()
        get_logger("fallback.test")
        assert logging.getLogger().level == logging.INFO

    def test_root_logger_gets_handler(self) -> None:
        logging.getLogger().handlers.clear()
        get_logger("handler.test")
        assert len(logging.getLogger().handlers) > 0
