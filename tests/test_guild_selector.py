"""Playwright test for guild/channel selector and CONNECT button state.

Uses Playwright's sync API. Serves the test fixture via a local HTTP server
so that HTMX requests go over http:// and can be intercepted by Playwright.
"""

import functools
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
TEST_HTML = "test_guild_selector.html"

MOCK_CHANNELS_HTML = (
    '<select id="channel-select" name="channel_id" aria-label="Select voice channel">'
    '  <option value="">SELECT CHANNEL</option>'
    '  <option value="101">General (3)</option>'
    '  <option value="102">Music (1)</option>'
    '  <option value="103">AFK (0)</option>'
    '</select>'
)


@pytest.fixture(scope="module")
def http_server():
    """Start a local HTTP server on port 0 serving tests/ directory."""
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(HERE))
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        server.shutdown()


@pytest.fixture(scope="module")
def pw_browser():
    """Launch a single Chromium instance for all tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


def _open_page(browser, port):
    """Open the test page with HTMX route interception."""
    page = browser.new_page()
    page.goto(f"http://127.0.0.1:{port}/{TEST_HTML}")
    page.wait_for_function(
        "window.Harpi && window.Harpi.components && window.Harpi.components.guildSelector"
    )
    # Intercept /htmx/channels requests and return mock channel options
    page.route("**/htmx/channels*", lambda route: route.fulfill(
        status=200, content_type="text/html", body=MOCK_CHANNELS_HTML
    ))
    return page


def test_connect_button_starts_disabled(pw_browser, http_server):
    """CONNECT button is disabled when no guild/channel selected."""
    page = _open_page(pw_browser, http_server)
    try:
        btn = page.locator('#guild-channel-selector button[type="submit"]')
        btn.wait_for(state="visible")
        assert btn.is_disabled(), "CONNECT button should be disabled initially"
    finally:
        page.close()


def test_guild_select_enables_channel_select(pw_browser, http_server):
    """Selecting a guild loads channels and enables the channel dropdown."""
    page = _open_page(pw_browser, http_server)
    try:
        page.locator("#guild-select").select_option("111")
        channel_select = page.locator("#channel-select")
        channel_select.wait_for(state="visible")
        time.sleep(0.3)
        assert not channel_select.is_disabled(), \
            "Channel select should be enabled after guild selection"
    finally:
        page.close()


def test_connect_button_disabled_before_channel_selection(pw_browser, http_server):
    """CONNECT button is disabled when guild selected but no channel yet."""
    page = _open_page(pw_browser, http_server)
    try:
        btn = page.locator('#guild-channel-selector button[type="submit"]')
        page.locator("#guild-select").select_option("111")
        page.locator("#channel-select").wait_for(state="visible")
        time.sleep(0.3)
        assert btn.is_disabled(), \
            "CONNECT button should be disabled before channel selection"
    finally:
        page.close()


def test_connect_button_enables_after_channel_selection(pw_browser, http_server):
    """CONNECT button enables after both guild and channel are selected."""
    page = _open_page(pw_browser, http_server)
    try:
        btn = page.locator('#guild-channel-selector button[type="submit"]')
        page.locator("#guild-select").select_option("111")
        channel_select = page.locator("#channel-select")
        channel_select.wait_for(state="visible")
        time.sleep(0.3)

        channel_select.select_option("101")
        time.sleep(0.3)

        assert not btn.is_disabled(), \
            "CONNECT button should be enabled after channel selection"
    finally:
        page.close()


def test_button_enabled_via_programmatic_change(pw_browser, http_server):
    """Button enables when channel is changed via dispatched change event."""
    page = _open_page(pw_browser, http_server)
    try:
        btn = page.locator('#guild-channel-selector button[type="submit"]')
        page.locator("#guild-select").select_option("111")
        page.locator("#channel-select").wait_for(state="visible")
        time.sleep(0.3)

        page.evaluate("""
            const sel = document.getElementById('channel-select');
            sel.value = '101';
            sel.dispatchEvent(new Event('change', { bubbles: true }));
        """)
        time.sleep(0.3)

        assert not btn.is_disabled(), \
            "CONNECT button should be enabled after programmatic channel change"
    finally:
        page.close()
