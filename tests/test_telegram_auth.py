import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from aliali.api.auth import validate_telegram_init_data
from aliali.core.errors import SecurityError


def make_init_data(bot_token: str, *, auth_date: int | None = None) -> str:
    auth_date = auth_date or int(time.time())
    pairs = {
        "auth_date": str(auth_date),
        "query_id": "AAEAA",
        "user": json.dumps({"id": 123}),
    }
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(pairs.items())
    )
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(
        secret,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(pairs)


def test_valid_telegram_init_data() -> None:
    result = validate_telegram_init_data(make_init_data("test-token"), "test-token")
    assert result["user"] == {"id": 123}


def test_invalid_signature_is_rejected() -> None:
    with pytest.raises(SecurityError):
        validate_telegram_init_data(make_init_data("test-token"), "wrong-token")


def test_expired_init_data_is_rejected() -> None:
    with pytest.raises(SecurityError):
        validate_telegram_init_data(
            make_init_data("test-token", auth_date=int(time.time()) - 7200),
            "test-token",
        )
