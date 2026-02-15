import io
import time

import pytest
from PIL import Image

from gancio_py import Gancio, GancioError


def _test_image():
    """Creates a minimal valid PNG image in memory."""
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color="red").save(buf, format="PNG")
    buf.seek(0)
    return buf

pytestmark = pytest.mark.integration


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
    def test_event_lifecycle(self, client, create_event):
        """Create with all fields, update, verify, delete."""
        future = int(time.time()) + 7 * 24 * 60 * 60

        # Create with all optional fields
        created = create_event(description="A detailed description",
                               end_datetime=future + 3600,
                               place_latitude=52.3676,
                               place_longitude=4.9041,
                               online_locations=["https://example.com/stream"],
                               tags=["test", "music", "live"])
        assert "slug" in created

        # Verify all fields persisted
        fetched = client.get_event(created["slug"])
        assert fetched["title"] == "Test: Event"
        assert fetched["description"] == "A detailed description"
        assert fetched["end_datetime"] is not None
        assert fetched["place"]["name"] == "Test Place"
        assert len(fetched["tags"]) == 3
        assert "https://example.com/stream" in fetched["online_locations"]

        # Update
        updated = client.update_event(event_id=created["id"],
                                      title="Test: Updated Event",
                                      place_name="Test Place",
                                      place_address="123 Test Street")
        assert updated["title"] == "Test: Updated Event"

        fetched = client.get_event(created["slug"])
        assert fetched["title"] == "Test: Updated Event"

        # Delete
        client.delete_event(created["id"])
        time.sleep(1)

        with pytest.raises(GancioError) as exc_info:
            client.get_event(created["slug"])
        assert exc_info.value.status_code == 404

    def test_multiple_events_filters_and_places(self, client, create_event):
        """Create events across places and tags, verify filtering and place lookup."""
        create_event(suffix=" One", tags=["test", "music"])
        create_event(suffix=" Two", tags=["test", "art"],
                     place_name="Test Venue B", place_address="456 Other Street")

        # Filter by tag
        all_events = client.get_events(tags=["test"])
        assert len(all_events) >= 2

        music_events = client.get_events(tags=["music"])
        music_titles = [e["title"] for e in music_events]
        assert any("One" in t for t in music_titles)
        assert not any("Two" in t for t in music_titles)

    def test_event_with_image(self, client, create_event):
        """Create with image, then update another event's image."""
        # Create with image
        created = create_event(suffix=" With Image", image=_test_image())
        fetched = client.get_event(created["slug"])
        assert fetched["media"] is not None

        # Update a different event to add an image
        plain = create_event(suffix=" No Image")
        client.update_event(event_id=plain["id"],
                            place_name="Test Place",
                            place_address="123 Test Street",
                            image=_test_image())
        fetched = client.get_event(plain["slug"])
        assert fetched["media"] is not None


class TestPlaces:
    def test_search_and_get_place(self, client, create_event):
        create_event(suffix=" One")
        create_event(suffix=" Two",
                     place_name="Test Venue B", place_address="456 Other Street")

        results = client.search_place("Test Place")
        assert len(results) > 0
        assert results[0]["name"] == "Test Place"

        place = client.get_place("Test Venue B")
        assert place is not None
        assert place["name"] == "Test Venue B"


class TestGancioError:
    def test_gancio_error_on_bad_request(self, client):
        with pytest.raises(GancioError) as exc_info:
            client.get_event("nonexistent-slug-that-does-not-exist")
        assert exc_info.value.status_code is not None
        assert exc_info.value.response_body is not None

    def test_access_token_constructor(self):
        """Verify that passing an access_token in the constructor sets auth."""
        c = Gancio(url="http://localhost:13120", access_token="fake-token")
        with pytest.raises(GancioError):
            c.get_user()
