import time

import pytest

from gancio_py import Gancio, GancioError

pytestmark = pytest.mark.integration


def _future_timestamp():
    """Return a timestamp 7 days in the future."""
    return int(time.time()) + 7 * 24 * 60 * 60


def _create_test_event(client, suffix=""):
    """Helper to create a test event and return it."""
    return client.create_event(
        title=f"Test: Event{suffix}",
        start_datetime=_future_timestamp(),
        place_name="Test Place",
        place_address="123 Test Street",
        description="A test event",
        tags=["test"],
    )


class TestLogin:
    def test_login(self, admin_credentials):
        c = Gancio(url="http://localhost:13120")
        data = c.login(username=admin_credentials["email"], password=admin_credentials["password"])
        assert "access_token" in data
        assert data["username"] == "admin"

    def test_login_invalid_credentials(self):
        c = Gancio(url="http://localhost:13120")
        with pytest.raises(GancioError) as exc_info:
            c.login(username="bad@example.com", password="wrong")
        assert exc_info.value.status_code is not None


class TestUser:
    def test_get_user(self, client):
        user = client.get_user()
        assert "email" in user
        assert "settings" in user


class TestEvents:
    def test_create_and_get_event(self, client):
        created = _create_test_event(client)
        assert created["title"] == "Test: Event"
        assert "slug" in created

        fetched = client.get_event(created["slug"])
        assert fetched["title"] == "Test: Event"
        assert fetched["place"]["name"] == "Test Place"

    def test_update_event(self, client):
        created = _create_test_event(client)
        updated = client.update_event(
            event_id=created["id"],
            title="Test: Updated Event",
        )
        assert updated["title"] == "Test: Updated Event"

        fetched = client.get_event(created["slug"])
        assert fetched["title"] == "Test: Updated Event"

    def test_delete_event(self, client):
        created = _create_test_event(client)
        client.delete_event(created["id"])

        with pytest.raises(GancioError) as exc_info:
            client.get_event(created["slug"])
        assert exc_info.value.status_code == 404

    def test_get_events_with_filters(self, client):
        _create_test_event(client, suffix=" Filtered")
        events = client.get_events(tags=["test"])
        titles = [e["title"] for e in events]
        assert any("Filtered" in t for t in titles)

    def test_confirm_event(self, client):
        created = _create_test_event(client)
        # Should not raise
        client.confirm_event(created["id"])


class TestPlaces:
    def test_search_place(self, client):
        _create_test_event(client)
        results = client.search_place("Test Place")
        assert len(results) > 0
        assert results[0]["name"] == "Test Place"

    def test_get_place(self, client):
        _create_test_event(client)
        place = client.get_place("Test Place")
        assert place is not None
        assert place["name"] == "Test Place"


class TestGancioError:
    def test_gancio_error_on_bad_request(self, client):
        with pytest.raises(GancioError) as exc_info:
            client.get_event("nonexistent-slug-that-does-not-exist")
        assert exc_info.value.status_code is not None
        assert exc_info.value.response_body is not None

    def test_token_constructor(self):
        """Verify that passing a token in the constructor sets auth."""
        c = Gancio(url="http://localhost:13120", token="fake-token")
        with pytest.raises(GancioError):
            c.get_user()
