---
lang: python
keywords: pytest, fixture, test, tmp_path, parametrize, conftest, monkeypatch, assert, unittest
---

# pytest fixtures and parametrize

pytest fixtures are dependency-injected setup/teardown: a test that takes `tmp_path` as an
argument automatically gets a fresh temp directory per test. Parametrize runs the same test
body over many inputs, turning a loop of assertions into one matrix.

```python
# pip install pytest
import json

import pytest


@pytest.fixture
def config_file(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"retries": 3, "host": "localhost", "port": 8080}))
    return path


@pytest.mark.parametrize("key,expected", [
    ("retries", 3),
    ("host", "localhost"),
    ("port", 8080),
])
def test_config_has_expected_value(config_file, key, expected):
    data = json.loads(config_file.read_text())
    assert data[key] == expected


@pytest.fixture
def client(monkeypatch):
    seen = []

    def fake_send(host, port):
        seen.append((host, port))
        return b"ok"

    monkeypatch.setattr("module_under_test.send", fake_send)   # patch a real import path
    return seen
```

Gotchas:
- A fixture that shares one object between tests must set `scope="session"` or `"module"`;
  default scope is per-test (function), which is usually what you want for isolation.
- Fixtures can depend on other fixtures (`config_file` uses `tmp_path`) — order is automatic;
  don't call fixtures manually, just name them as parameters.
- `parametrize` argument names must exactly match the test function parameter names.
- Tests run from an arbitrary rootdir — always use `tmp_path` for file I/O, never hardcoded
  relative paths or the current directory.
- Use `monkeypatch.setattr("pkg.module.attr", fake)` on the *import location*, not the object's
  source module, or the patch won't take effect.
- An assertion failure inside a fixture makes every dependent test error — keep fixtures cheap
  and their assertions out.
