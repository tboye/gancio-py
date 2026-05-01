import io
import time

import pytest
from PIL import Image

from gancio_py import BoolSetting, Gancio, GancioError, JsonSetting, StrSetting


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
        """Image is preserved on update when no new image is provided."""
        event = create_event(suffix=" With Image", image=_test_image())
        assert client.get_event(event["slug"])["media"] is not None

        # Update title only — image must survive
        client.update_event(event_id=event["id"],
                            title="Test: Updated With Image",
                            place_name="Test Place",
                            place_address="123 Test Street")
        assert client.get_event(event["slug"])["media"] is not None

        # Replace image
        client.update_event(event_id=event["id"],
                            place_name="Test Place",
                            place_address="123 Test Street",
                            image=_test_image())
        assert client.get_event(event["slug"])["media"] is not None

        # Remove image
        client.update_event(event_id=event["id"],
                            place_name="Test Place",
                            place_address="123 Test Street",
                            image=False)
        assert client.get_event(event["slug"])["media"] == []


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

    def test_get_place_events(self, client, create_event):
        create_event(place_name="Test Venue C", place_address="789 Other Street")

        result = client.get_place_events("Test Venue C")
        assert result is not None
        assert result["place"]["name"] == "Test Venue C"
        assert "events" in result
        assert "pastEvents" in result

    def test_get_place_events_not_found(self, client):
        assert client.get_place_events("nonexistent-place-xyz") is None


class TestSettings:
    def test_get_settings(self, client):
        settings = client.get_settings()
        assert isinstance(settings, dict)
        assert 'title' in settings

    def test_set_str_setting(self, client):
        settings = client.get_settings()
        cases = [
            (StrSetting.TITLE,                      "Test Title"),
            (StrSetting.DESCRIPTION,                "Test description"),
            (StrSetting.ABOUT,                      "<p>Test about</p>"),
            (StrSetting.BASEURL,                    "http://localhost:13120"),
            (StrSetting.ADMIN_EMAIL,                "test@example.com"),
            (StrSetting.INSTANCE_TIMEZONE,          "Europe/Amsterdam"),
            (StrSetting.INSTANCE_LOCALE,            "en"),
            (StrSetting.INSTANCE_NAME,              "test-relay"),
            (StrSetting.CUSTOM_JS,                  "console.log('test')"),
            (StrSetting.CUSTOM_CSS,                 "body { color: red; }"),
            (StrSetting.GEOCODING_PROVIDER,         "https://nominatim.openstreetmap.org/search"),
            (StrSetting.GEOCODING_PROVIDER_TYPE,    "Nominatim"),
            (StrSetting.TILELAYER_PROVIDER,         "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"),
            (StrSetting.TILELAYER_PROVIDER_ATTRIBUTION, "Test attribution"),
        ]
        for key, value in cases:
            original = settings.get(key)
            try:
                client.set_str_setting(key, value)
                assert client.get_settings().get(key) == value
            finally:
                client.set_str_setting(key, original or "")

    def test_set_bool_setting(self, client):
        settings = client.get_settings()
        for key in BoolSetting:
            original = settings.get(key)
            try:
                client.set_bool_setting(key, not original)
                assert client.get_settings().get(key) == (not original)
            finally:
                client.set_bool_setting(key, original)

    def test_set_json_setting(self, client):
        settings = client.get_settings()
        cases = [
            (JsonSetting.GEOCODING_COUNTRYCODES,  ["NL"]),
            (JsonSetting.DEFAULT_FEDI_HASHTAGS,   ["test"]),
            (JsonSetting.FOOTER_LINKS,            [{"href": "/", "label": "common.home"}]),
            (JsonSetting.DARK_COLORS,             {"primary": "#FF0000", "error": "#FF5252", "info": "#2196F3",
                                                   "success": "#4CAF50", "warning": "#FB8C00"}),
            (JsonSetting.LIGHT_COLORS,            {"primary": "#FF0000", "error": "#FF5252", "info": "#2196F3",
                                                   "success": "#4CAF50", "warning": "#FB8C00"}),
            (JsonSetting.PLUGINS,                 []),
            (JsonSetting.COLLECTION_IN_HOME,      None),
            (JsonSetting.CALENDAR_FIRST_DAY_OF_WEEK, 1),
            # SMTP is excluded: restoring without the original password would wipe credentials
        ]
        for key, value in cases:
            original = settings.get(key)
            try:
                client.set_json_setting(key, value)
                assert client.get_settings().get(key) == value
            finally:
                client.set_json_setting(key, original)

    def test_get_smtp(self, client):
        smtp = client.get_smtp()
        assert isinstance(smtp, dict)

    def test_logo(self, client):
        client.set_logo(_test_image())
        assert isinstance(client.get_logo(), bytes)

    def test_fallback_image(self, client):
        client.set_fallback_image(_test_image())
        assert isinstance(client.get_fallback_image(), bytes)

    def test_header_image(self, client):
        client.set_header_image(_test_image())
        assert isinstance(client.get_header_image(), bytes)


class TestPages:
    def test_create_and_get_page(self, client, create_page):
        page = create_page(title="Test Page", content="<p>Hello</p>")
        assert page['title'] == "Test Page"
        assert 'slug' in page

        fetched = client.get_page(page['slug'])
        assert fetched is not None
        assert fetched['id'] == page['id']
        assert fetched['title'] == "Test Page"
        assert fetched['content'] == "<p>Hello</p>"

    def test_update_page(self, client, create_page):
        page = create_page(title="Original Title", content="<p>Original</p>")

        client.update_page(page_id=page['id'], title="Updated Title", content="<p>Updated</p>")

        fetched = client.get_page(page['slug'])
        assert fetched['title'] == "Updated Title"
        assert fetched['content'] == "<p>Updated</p>"

    def test_partial_update_page(self, client, create_page):
        page = create_page(title="Original Title", content="<p>Original</p>")

        client.update_page(page_id=page['id'], title="New Title")
        fetched = client.get_page(page['slug'])
        assert fetched['title'] == "New Title"
        assert fetched['content'] == "<p>Original</p>"

        client.update_page(page_id=page['id'], content="<p>New Content</p>")
        fetched = client.get_page(page['slug'])
        assert fetched['title'] == "New Title"
        assert fetched['content'] == "<p>New Content</p>"

    def test_delete_page(self, client, create_page):
        page = create_page()
        slug = page['slug']

        client.delete_page(page['id'])

        assert client.get_page(slug) is None

    def test_get_page_not_found(self, client):
        assert client.get_page("nonexistent-slug-xyz") is None


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
