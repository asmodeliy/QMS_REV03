import json
from types import SimpleNamespace
from urllib.error import HTTPError

import app_desktop_qt as appmod

class DummyResponse:
    def __init__(self, data):
        self._data = data
    def read(self):
        return self._data

class DummyOpener:
    def __init__(self, sequence):
        self._seq = sequence
        self._idx = 0
    def open(self, req, timeout=3):
        if self._idx >= len(self._seq):
            raise RuntimeError("No more responses")
        action = self._seq[self._idx]
        self._idx += 1
        if isinstance(action, Exception):
            raise action
        return action

def test_api_request_follow_redirect(monkeypatch):
                                                                                     
    hdrs = {'Location': '/api/test'}
    http_error = HTTPError('http://server/main/api/test', 307, 'Temporary Redirect', hdrs, None)
    final = DummyResponse(b'{"ok": true, "value": 123}')

    opener = DummyOpener([http_error, final])

    def fake_build_opener(proc):
        return opener

    monkeypatch.setattr(appmod, 'build_opener', fake_build_opener)

                           
    dummy = SimpleNamespace()
    dummy.server_url = 'http://server'
    dummy.cookie_jar = type('CJ', (), {'add_cookie_header': lambda *a, **k: None, 'extract_cookies': lambda *a, **k: None})()

    result = appmod.QMSDesktopClient.api_request(dummy, '/main/api/test')
    assert isinstance(result, dict)
    assert result.get('ok') is True
    assert result.get('value') == 123
