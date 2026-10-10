import pytest

from pretty_notebook.appearance import validate_appearance
from pretty_notebook.settings import NotebookSettings, SettingsError
from pretty_notebook import Notebook
from pretty_notebook._internal import publishing


@pytest.mark.parametrize('value', [
    {'palette': '../escape'}, {'accent': '</style><script>'}, {'radius': True},
    {'radius': 21}, {'reading_width': 80, 'site_width': 60}, {'font': 'url(remote)'},
    {'custom_css': 'true'}, {'unknown': 'value'},
])
def test_portable_settings_reject_unsafe_appearance(value):
    with pytest.raises(SettingsError):
        NotebookSettings(appearance=value)


def test_appearance_is_portable_and_independent():
    original = {'palette': 'paper', 'font': 'mono', 'mode': 'system', 'accent': '#275d3e'}
    settings = NotebookSettings(appearance=original)
    portable = settings.to_dict()
    assert portable['APPEARANCE'] == original
    portable['APPEARANCE']['font'] = 'serif'
    assert settings.appearance['font'] == 'mono'
    assert validate_appearance({})['palette'] == 'slate'


def test_publishing_preserves_appearance_without_sending_credentials(tmp_path, monkeypatch):
    notebook = Notebook.open(tmp_path, settings={'API_BASE': 'https://example.test',
                                                'APPEARANCE': {'palette': 'paper', 'font': 'serif'}},
                             api_token='synthetic-token')
    captured = {}
    class Response:
        status_code = 201
        def raise_for_status(self):
            pass
    def post(url, **kwargs):
        captured.update(kwargs)
        return Response()
    monkeypatch.setattr(publishing.requests, 'post', post)
    notebook.web_settings_post()
    assert captured['json']['APPEARANCE'] == {'palette': 'paper', 'font': 'serif'}
    assert 'API_TOKEN' not in captured['json'] and 'API_BASE' not in captured['json']
