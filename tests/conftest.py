import os
import time

import pytest
import requests

from gancio_py import Gancio

GANCIO_URL = os.environ.get("GANCIO_URL", "http://localhost:13120")
GANCIO_ADMIN_EMAIL = os.environ.get("GANCIO_ADMIN_EMAIL")
GANCIO_ADMIN_PASSWORD = os.environ.get("GANCIO_ADMIN_PASSWORD")


def _wait_for_gancio(path="/", timeout=120):
    """Waits until Gancio responds without error at the given path."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{GANCIO_URL}{path}", timeout=2)
            if r.status_code < 500:
                return
        except requests.ConnectionError:
            pass
        time.sleep(2)
    raise TimeoutError(f"Gancio not reachable at {GANCIO_URL}{path} after {timeout}s")


@pytest.fixture(scope="session")
def admin_credentials():
    """Returns admin credentials, running first-time setup if needed."""
    if GANCIO_ADMIN_EMAIL and GANCIO_ADMIN_PASSWORD:
        return {"email": GANCIO_ADMIN_EMAIL, "password": GANCIO_ADMIN_PASSWORD}

    _wait_for_gancio()

    c = Gancio(url=GANCIO_URL)
    c.setup_db()
    creds = c.setup_restart()

    # Gancio restarts after setup, wait for the API to be ready
    time.sleep(5)
    _wait_for_gancio(path="/api/events")

    return creds


@pytest.fixture(scope="session")
def client(admin_credentials):
    """Creates a Gancio client authenticated with the admin account."""
    c = Gancio(url=GANCIO_URL)
    c.login(username=admin_credentials["email"], password=admin_credentials["password"])
    return c


@pytest.fixture(autouse=True)
def cleanup_events(client):
    """Deletes any test events created during a test."""
    yield
    events = client.get_events()
    for event in events:
        if event["title"].startswith("Test:"):
            client.delete_event(event["id"])