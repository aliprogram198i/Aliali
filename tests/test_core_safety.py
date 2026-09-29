import asyncio

import pytest

from aliali.core.errors import ErrorCode
from aliali.core.execution import ExecutionPolicy, execute
from aliali.core.learning import LearningEngine
from aliali.core.security import AuthorizationContext, AuthorizationLevel


@pytest.mark.asyncio
async def test_execution_fails_closed_without_authorization():
    context = AuthorizationContext(1, "case-1", AuthorizationLevel.PUBLIC)

    async def operation():
        return {"secret": "should-not-run"}

    result = await execute(
        "restricted.module",
        operation,
        context,
        ExecutionPolicy(required_authorization=AuthorizationLevel.AUTHORIZED),
    )

    assert result.ok is False
    assert result.error_code == ErrorCode.NOT_AUTHORIZED


@pytest.mark.asyncio
async def test_execution_converts_timeout_to_structured_error():
    context = AuthorizationContext(1, "case-1", AuthorizationLevel.PUBLIC)

    async def operation():
        await asyncio.sleep(0.05)
        return {}

    result = await execute(
        "slow.module",
        operation,
        context,
        ExecutionPolicy(timeout_seconds=0.001),
    )

    assert result.ok is False
    assert result.error_code == ErrorCode.TIMEOUT


def test_learning_requires_valid_confidence():
    engine = LearningEngine()
    with pytest.raises(ValueError):
        engine.record("module", "bad", 1.5)
