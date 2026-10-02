import base64
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from ..core.errors import ErrorCode, SecurityError


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 3600,
) -> dict[str, object]:
    if not init_data.strip():
        raise SecurityError(ErrorCode.NOT_AUTHORIZED, "Telegram init data is required")
    if not bot_token.strip():
        raise SecurityError(ErrorCode.INTERNAL, "Bot token is not configured")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise SecurityError(ErrorCode.NOT_AUTHORIZED, "Telegram init data hash is missing")

    try:
        auth_date = int(pairs.get("auth_date") or "")
    except ValueError as exc:
        raise SecurityError(ErrorCode.NOT_AUTHORIZED, "Telegram auth date is invalid") from exc

    if abs(time.time() - auth_date) > max_age_seconds:
        raise SecurityError(ErrorCode.NOT_AUTHORIZED, "Telegram init data has expired")

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(pairs.items())
    )
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise SecurityError(ErrorCode.NOT_AUTHORIZED, "Telegram init data signature is invalid")

    user: dict[str, object] = {}
    if raw_user := pairs.get("user"):
        try:
            parsed_user = json.loads(raw_user)
        except json.JSONDecodeError as exc:
            raise SecurityError(ErrorCode.NOT_AUTHORIZED, "Telegram user payload is invalid") from exc
        if not isinstance(parsed_user, dict):
            raise SecurityError(ErrorCode.NOT_AUTHORIZED, "Telegram user payload is invalid")
        user = parsed_user

    return {"auth_date": auth_date, "user": user}

def create_session_token(identity: dict[str, object], bot_token: str, *, ttl_seconds: int = 21600) -> str:
    user = identity.get("user")
    user_id = user.get("id") if isinstance(user, dict) else None
    if user_id is None:
        raise SecurityError(ErrorCode.NOT_AUTHORIZED, "Telegram user identity is missing")
    payload = {"user_id": user_id, "exp": int(time.time()) + ttl_seconds}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    encoded = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    key = hmac.new(b"AlialiSession", bot_token.encode(), hashlib.sha256).digest()
    signature = hmac.new(key, encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def validate_session_token(token: str, bot_token: str) -> dict[str, object]:
    try:
        encoded, received_signature = token.split(".", 1)
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        payload = json.loads(raw)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SecurityError(ErrorCode.NOT_AUTHORIZED, "Aliali session is invalid") from exc
    if not isinstance(payload, dict) or int(payload.get("exp", 0)) < int(time.time()):
        raise SecurityError(ErrorCode.NOT_AUTHORIZED, "Aliali session has expired")
    key = hmac.new(b"AlialiSession", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(key, encoded.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_signature):
        raise SecurityError(ErrorCode.NOT_AUTHORIZED, "Aliali session signature is invalid")
    return {"user_id": payload.get("user_id"), "exp": payload["exp"]}

