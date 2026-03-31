"""Unit tests for DomainEventBus."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from dacke.domain.events.domain import DomainEvent
from dacke.infrastructure.bus import DomainEventBus


# ---------------------------------------------------------------------------
# Minimal stub event
# ---------------------------------------------------------------------------


class _StubEvent(DomainEvent):
    pass


class _OtherEvent(DomainEvent):
    pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDomainEventBus:
    def test_register_and_publish_sync_handler(self) -> None:
        bus = DomainEventBus()
        received: list[DomainEvent] = []
        bus.register(_StubEvent, received.append)

        import asyncio
        asyncio.get_event_loop().run_until_complete(bus.publish(_StubEvent()))

        assert len(received) == 1
        assert isinstance(received[0], _StubEvent)

    @pytest.mark.asyncio
    async def test_register_and_publish_async_handler(self) -> None:
        bus = DomainEventBus()
        received: list[DomainEvent] = []

        async def async_handler(event: DomainEvent) -> None:
            received.append(event)

        bus.register(_StubEvent, async_handler)
        await bus.publish(_StubEvent())

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_multiple_handlers_all_called(self) -> None:
        bus = DomainEventBus()
        calls: list[str] = []

        async def h1(e: DomainEvent) -> None:
            calls.append("h1")

        async def h2(e: DomainEvent) -> None:
            calls.append("h2")

        bus.register(_StubEvent, h1)
        bus.register(_StubEvent, h2)
        await bus.publish(_StubEvent())

        assert "h1" in calls
        assert "h2" in calls

    @pytest.mark.asyncio
    async def test_no_handler_registered_does_not_raise(self) -> None:
        bus = DomainEventBus()
        await bus.publish(_StubEvent())  # should not raise

    @pytest.mark.asyncio
    async def test_handler_not_called_for_different_event_type(self) -> None:
        bus = DomainEventBus()
        called = False

        async def handler(e: DomainEvent) -> None:
            nonlocal called
            called = True

        bus.register(_StubEvent, handler)
        await bus.publish(_OtherEvent())

        assert not called

    @pytest.mark.asyncio
    async def test_handler_exception_propagates(self) -> None:
        bus = DomainEventBus()

        async def bad_handler(e: DomainEvent) -> None:
            raise ValueError("boom")

        bus.register(_StubEvent, bad_handler)

        with pytest.raises(ValueError, match="boom"):
            await bus.publish(_StubEvent())
