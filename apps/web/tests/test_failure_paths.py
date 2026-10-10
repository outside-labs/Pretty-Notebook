"""Consequential failure boundaries missing from the earlier coverage denominator."""

import asyncio
import json
import os
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from api import auth_api
from api.process_lock import ProcessLock
from fastapi.testclient import TestClient
from main import create_app
import install_assets
import web_config


def test_blank_account_names_and_unsupported_login_passwords_fail_closed(client, bootstrap_headers):
    response = client.post('/api/users', headers=bootstrap_headers,
                           json={'username': '  ', 'password_hash': 'long-enough-test-password'})
    assert response.status_code == 422
    for password in ('tiny', 'x' * 73):
        response = client.post('/api/token', data={'username': 'owner', 'password': password})
        assert response.status_code == 401


def test_account_removed_after_authentication_cannot_reset_password(client, root_user):
    cached = auth_api.User_Pydantic.model_validate(root_user)
    async def deleted_after_authentication():
        await auth_api.User.filter(id=cached.id).delete()
        return cached
    client.app.dependency_overrides[auth_api.get_current_user] = deleted_after_authentication
    response = client.post('/api/users/me', json={'password_hash': 'replacement-test-password'})
    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'


def test_navigation_limits_reject_oversized_or_unsafe_groups(client, auth_headers, layout_payload):
    cases = [
        {str(index): '/contact' for index in range(101)},
        {'': '/contact'}, {'x' * 201: '/contact'},
        {'Group': [{str(index): '/contact'} for index in range(101)]},
        {'Group': [{'': '/contact'}]}, {'Group': [{'x' * 201: '/contact'}]},
        {'Broken': '/bad\npath'}, {'Broken': '/bad\\path'},
    ]
    for pages in cases:
        layout_payload['NAV_PAGES'] = pages
        response = client.post('/api/layout', headers=auth_headers, json=layout_payload)
        assert response.status_code == 422


def test_stylesheet_storage_failure_preserves_previous_css(client, auth_headers, web_storage, monkeypatch):
    from api import site_api
    target = web_storage.settings.parent / 'appearance.css'
    target.write_text('original CSS')
    async def failed(*args): raise OSError('synthetic storage failure')
    monkeypatch.setattr(site_api, 'atomic_write_bytes', failed)
    response = client.put('/api/appearance/stylesheet', content='replacement', headers=auth_headers)
    assert response.status_code == 503
    assert target.read_text() == 'original CSS'


def test_custom_stylesheet_missing_or_symlink_fails_closed(client, auth_headers, web_storage, layout_payload):
    layout_payload['APPEARANCE']['custom_css'] = True
    assert client.post('/api/layout', json=layout_payload, headers=auth_headers).status_code == 201
    assert client.get('/static/custom/appearance.css').status_code == 404
    target = web_storage.settings.parent / 'appearance.css'
    private = web_storage.settings.parent / 'private.txt'
    private.write_text('synthetic-private-data')
    target.symlink_to(private)
    response = client.get('/static/custom/appearance.css')
    assert response.status_code == 503 and 'synthetic-private-data' not in response.text


@pytest.mark.parametrize('hosts', ['', '*', 'https://notes.example.com', 'notes.example.com/path'])
def test_host_configuration_rejects_invalid_public_profiles(monkeypatch, hosts):
    monkeypatch.setenv('PNBP_ALLOWED_HOSTS', hosts)
    with pytest.raises(RuntimeError): web_config.allowed_hosts()


def test_worker_lock_rejects_a_nonregular_coordination_file(tmp_path):
    path = tmp_path / 'site.lock'
    os.mkfifo(path, mode=0o600)
    lock = ProcessLock(path)
    async def scenario():
        with pytest.raises(RuntimeError, match='regular local lock file'):
            async with lock: pass
        assert not lock.local.locked() and lock.descriptor is None
    asyncio.run(scenario())


def test_tampered_migration_name_stops_startup_without_rewriting_state(tmp_path, web_storage):
    database = tmp_path / 'site.db'
    with TestClient(create_app(db_url=f'sqlite://{database}')): pass
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE pnbp_schema_migrations SET name='tampered' WHERE version=2")
        connection.commit()
    with pytest.raises(RuntimeError, match='Inconsistent migration history'):
        with TestClient(create_app(db_url=f'sqlite://{database}')): pass
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute('SELECT name FROM pnbp_schema_migrations WHERE version=2').fetchone()[0] == 'tampered'


def missing_asset(tmp_path):
    root = tmp_path / 'static'
    shutil.copytree(Path(install_assets.__file__).parent / 'static', root)
    manifest = json.loads((root / 'asset-manifest.json').read_text())
    entry = next(iter(manifest['assets'].values()))
    target = root / entry['path']
    content = target.read_bytes()
    target.unlink()
    return root, target, entry, content


class Download:
    def __init__(self, url, content): self.url, self.content = url, content
    def __enter__(self): return self
    def __exit__(self, *exception): pass
    def geturl(self): return self.url
    def read(self, limit): return self.content[:limit]


def test_asset_install_rejects_redirect_and_bad_digest_without_writing(tmp_path, monkeypatch):
    root, target, entry, content = missing_asset(tmp_path)
    for url, body, reason in [(entry['cdn'] + '/redirect', content, 'redirected'),
                              (entry['cdn'], b'bad-content', 'checksum')]:
        monkeypatch.setattr(install_assets, 'urlopen', lambda *args, url=url, body=body, **kwargs: Download(url, body))
        with pytest.raises(RuntimeError, match=reason): install_assets.install(root)
        assert not target.exists() and not list(root.rglob('.asset-*'))


def test_asset_install_rename_failure_cleans_staging_file(tmp_path, monkeypatch):
    root, target, entry, content = missing_asset(tmp_path)
    monkeypatch.setattr(install_assets, 'urlopen', lambda *args, **kwargs: Download(entry['cdn'], content))
    def failed(*args): raise OSError('synthetic rename failure')
    monkeypatch.setattr(install_assets.os, 'replace', failed)
    with pytest.raises(OSError): install_assets.install(root)
    assert not target.exists() and not list(root.rglob('.asset-*'))


def test_asset_check_cli_is_read_only(tmp_path, monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, 'argv', ['install_assets.py', '--check'])
    monkeypatch.setattr(install_assets, 'urlopen', lambda *args, **kwargs: pytest.fail('Check must not download'))
    install_assets.main()
    assert json.loads(capsys.readouterr().out)['valid'] is True
