"""Operator alerts queue, coalesce, and never reach the request path."""

from __future__ import annotations

from app import app as quart_app
from src import alerts


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _collector(sent: list[str]) -> alerts.Sender:
    async def sender(text: str) -> None:
        sent.append(text)

    return sender


async def test_repeated_identical_alerts_send_once():
    sent: list[str] = []
    clock = FakeClock()
    dispatcher = alerts.AlertDispatcher(_collector(sent), clock=clock)
    try:
        dispatcher.notify("unauthorized", "GET /api/status ip=203.0.113.9")
        dispatcher.notify("unauthorized", "GET /api/status ip=203.0.113.9")
        await dispatcher.flush()
    finally:
        await dispatcher.stop()

    assert sent == ["[harpi] 401 unauthorized: GET /api/status ip=203.0.113.9"]


async def test_distinct_alerts_both_send():
    sent: list[str] = []
    dispatcher = alerts.AlertDispatcher(_collector(sent))
    try:
        dispatcher.notify("forbidden", "GET /api/guilds/8/channels")
        dispatcher.notify("rate_limited", "POST /api/search")
        await dispatcher.flush()
    finally:
        await dispatcher.stop()

    assert len(sent) == 2


async def test_an_alert_sends_again_after_the_coalescing_window():
    sent: list[str] = []
    clock = FakeClock()
    dispatcher = alerts.AlertDispatcher(_collector(sent), clock=clock)
    try:
        dispatcher.notify("server_error", "GET /api/status")
        await dispatcher.flush()
        clock.advance(alerts.COALESCE_SECONDS + 1)
        dispatcher.notify("server_error", "GET /api/status")
        await dispatcher.flush()
    finally:
        await dispatcher.stop()

    assert len(sent) == 2


async def test_a_failing_sender_never_raises_into_the_caller():
    async def sender(text: str) -> None:
        raise RuntimeError("webhook refused")

    dispatcher = alerts.AlertDispatcher(sender)
    try:
        dispatcher.notify("server_error", "GET /api/status")
        await dispatcher.flush()
    finally:
        await dispatcher.stop()


async def test_a_full_queue_drops_alerts_without_raising():
    sent: list[str] = []

    async def sender(text: str) -> None:
        sent.append(text)

    dispatcher = alerts.AlertDispatcher(sender, queue_size=1)
    try:
        dispatcher.notify("server_error", "first")
        dispatcher.notify("server_error", "second")
        dispatcher.notify("server_error", "third")
        await dispatcher.flush()
    finally:
        await dispatcher.stop()

    assert len(sent) == 1


def test_an_unset_webhook_makes_alerts_a_no_op():
    assert alerts.configure_alerts(None) is None
    assert alerts.configure_alerts("") is None

    alerts.notify("server_error", "GET /api/status")


async def test_an_unauthenticated_api_call_alerts_the_operator():
    sent: list[str] = []
    dispatcher = alerts.configure_alerts(
        "https://discord.com/api/webhooks/1/token",
        sender=_collector(sent),
    )
    assert dispatcher is not None
    try:
        response = await quart_app.test_client().get("/api/status")
        await dispatcher.flush()
    finally:
        await alerts.stop_alerts()

    assert response.status_code == 401
    assert any("401 unauthorized" in text for text in sent)
