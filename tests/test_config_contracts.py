import json

from click.testing import CliRunner

import pnbp.cli as cli_module
from pnbp import Notebook
from pnbp.cli import cli


def test_settings_off_ignores_existing_settings_file(monkeypatch, tmp_path):
	monkeypatch.setenv("NOTE_PATH", str(tmp_path))
	monkeypatch.setenv("PNBP_SETTINGS", "off")
	(tmp_path / "pnbp_settings.json").write_text(
		json.dumps(
			{
				"API_BASE": "https://remote.example",
				"API_TOKEN": "should-not-load",
				"TITLE": "Configured title",
			}
		),
		encoding="utf-8",
	)

	nb = Notebook()

	assert nb.settings_file is False
	assert nb.API_BASE is None
	assert nb.API_TOKEN is None
	assert "TITLE" not in nb.config


def test_generated_settings_include_required_title(monkeypatch, tmp_path):
	monkeypatch.setenv("NOTE_PATH", str(tmp_path))
	monkeypatch.delenv("PNBP_SETTINGS", raising=False)
	monkeypatch.setattr("builtins.input", lambda prompt="": "y")

	nb = Notebook()
	generated = json.loads((tmp_path / "pnbp_settings.json").read_text(encoding="utf-8"))

	assert "TITLE" in generated
	assert "TITLE" in nb.config


def test_commit_settings_uses_remote_by_default_and_local_only_when_requested(monkeypatch):
	targets = []

	class FakeNotebook:
		def __init__(self):
			self.API_BASE = "https://remote.example"

		def web_settings_post(self):
			targets.append(self.API_BASE)

	monkeypatch.setattr(cli_module, "Notebook", FakeNotebook)
	runner = CliRunner()

	remote = runner.invoke(cli, ["commit-settings"])
	local = runner.invoke(cli, ["commit-settings", "--local"])

	assert remote.exit_code == 0, remote.output
	assert local.exit_code == 0, local.output
	assert targets == ["https://remote.example", "http://127.0.0.1:8000"]


def test_refresh_token_redacts_token_output(monkeypatch, tmp_path, capsys):
	monkeypatch.setenv("NOTE_PATH", str(tmp_path))
	monkeypatch.delenv("PNBP_SETTINGS", raising=False)
	settings = {
		"API_BASE": "https://remote.example",
		"API_TOKEN": "old-token",
	}
	(tmp_path / "pnbp_settings.json").write_text(json.dumps(settings), encoding="utf-8")
	nb = Notebook()

	class Response:
		status_code = 200
		text = '{"access_token":"new-secret-token","token_type":"bearer"}'

		def json(self):
			return {"access_token": "new-secret-token", "token_type": "bearer"}

		def __str__(self):
			return "<Response [200]>"

	monkeypatch.setattr("builtins.input", lambda prompt="": "ella")
	monkeypatch.setattr("getpass.getpass", lambda prompt="": "password")
	monkeypatch.setattr("pnbp.models.notebook.requests.post", lambda *args, **kwargs: Response())

	nb.refresh_token()
	output = capsys.readouterr().out

	assert "new-secret-token" not in output
	assert "old-token" not in output
	assert "<redacted>" in output
	assert nb.API_TOKEN == "new-secret-token"
	persisted = json.loads((tmp_path / "pnbp_settings.json").read_text(encoding="utf-8"))
	assert persisted["API_TOKEN"] == "new-secret-token"
