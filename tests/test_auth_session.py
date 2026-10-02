from aliali.api.auth import create_session_token, validate_session_token


def test_session_token_round_trip() -> None:
    identity = {"user": {"id": 12345}}
    token = create_session_token(identity, "bot-token", ttl_seconds=60)
    session = validate_session_token(token, "bot-token")
    assert session["user_id"] == 12345
    assert int(session["exp"]) > 0


def test_session_token_rejects_wrong_secret() -> None:
    identity = {"user": {"id": 12345}}
    token = create_session_token(identity, "bot-token", ttl_seconds=60)
    try:
        validate_session_token(token, "different-token")
    except Exception as exc:
        assert "signature" in str(exc).lower()
    else:
        raise AssertionError("session token must reject a different bot token")
