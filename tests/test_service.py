"""Tests for systemd service generation and lifecycle helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import undertone.service as service


class TestInstallService:
    def test_install_service_writes_repo_aware_unit(self, tmp_path: Path) -> None:
        systemd_dir = tmp_path / "systemd"
        service_file = systemd_dir / "undertone.service"
        fake_root = Path("/tmp/undertone-project")
        fake_src = fake_root / "src"
        fake_env = Path("/tmp/undertone-config/.env")

        with (
            patch.object(service, "SYSTEMD_USER_DIR", systemd_dir),
            patch.object(service, "SERVICE_FILE", service_file),
            patch.object(service, "PROJECT_ROOT", fake_root),
            patch.object(service, "PROJECT_SRC", fake_src),
            patch.object(service, "ENV_FILE", fake_env),
            patch.object(service, "get_python_path", return_value="/tmp/venv/bin/python"),
            patch.object(service.subprocess, "run", return_value=MagicMock(returncode=0)),
        ):
            assert service.install_service() is True

        content = service_file.read_text()
        assert "WorkingDirectory=/tmp/undertone-project" in content
        assert "Environment=PYTHONPATH=/tmp/undertone-project/src" in content
        assert "ExecStart=/tmp/venv/bin/python -m undertone.runner" in content
        assert "EnvironmentFile=/tmp/undertone-config/.env" in content


class TestStartService:
    def test_start_service_refreshes_unit_before_start(self) -> None:
        with (
            patch.object(service, "install_service", return_value=True) as mock_install,
            patch.object(service.subprocess, "run", return_value=MagicMock(returncode=0)),
        ):
            assert service.start_service() is True

        mock_install.assert_called_once()
