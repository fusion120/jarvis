---
lang: python
keywords: mock, patch, unittest.mock, mocking, stub, side_effect, requests, fake, testing, external
---

# Mocking external calls in tests

Unit tests must not hit the network, the clock, or the filesystem. `unittest.mock.patch`
replaces a real object with a `Mock` for the duration of a test, so you control return values,
raise errors, and assert what was called.

```python
# pip install requests
from unittest import mock

import requests


def get_user(user_id: int) -> dict:
    resp = requests.get(f"https://api.example.com/users/{user_id}", timeout=5)
    resp.raise_for_status()
    return resp.json()


def test_get_user_success():
    fake = mock.Mock()
    fake.json.return_value = {"id": 1, "name": "Ada"}
    fake.raise_for_status.return_value = None

    with mock.patch("requests.get", return_value=fake) as mocked:
        result = get_user(1)

    assert result["name"] == "Ada"
    mocked.assert_called_once()
    mocked.assert_called_with(
        "https://api.example.com/users/1", timeout=5
    )


def test_get_user_retries_once_on_503():
    flaky = mock.Mock()
    flaky.raise_for_status.side_effect = requests.HTTPError("503")
    good = mock.Mock()
    good.raise_for_status.return_value = None
    good.json.return_value = {"id": 1, "name": "Ada"}

    with mock.patch("requests.get", side_effect=[flaky, good]):
        result = get_user(1)

    assert result["name"] == "Ada"
```

Gotchas:
- Patch where the name is *looked up*: if `get_user` lives in `app.client`, patch
  `"app.client.requests.get"`, not `"requests.get"` — otherwise the real module is untouched.
- `side_effect` can be a callable (raise based on args), an iterable (return values in order),
  or an exception class to always raise.
- Calling a `Mock` never raises by default — forgetting to set `raise_for_status` means error
  paths silently pass; set both success and failure mocks.
- Assertions: `assert_called_once_with(...)` checks both call count and arguments; don't
  hand-roll the comparison.
- `patch` also works as a decorator, but `with` keeps the mock in scope for assertions after
  the block and avoids misleading call-order in the parameter list.
- `autospec=True` (`mock.patch("requests.get", autospec=True)`) rejects calls the real function
  wouldn't accept, catching signature typos at test time.
