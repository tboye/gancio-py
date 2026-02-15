import io
import json
import logging

import requests

from gancio_py.exceptions import GancioError


class Gancio:
    """Client for the Gancio API.

    Args:
        url: Base URL of the Gancio instance (e.g. 'https://gancio.example.org').
        access_token: Optional OAuth access token for authenticated requests.
    """

    def __init__(self, url: str, access_token: str = None):
        self.url = url.rstrip("/")
        self.access_token = access_token
        self.refresh_token = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Performs an HTTP request against the Gancio instance.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: API endpoint path (e.g. '/api/events').
            **kwargs: Passed to ``requests.request``.

        Returns:
            The response object.

        Raises:
            GancioError: If the server responds with an error status code.
        """
        headers = kwargs.pop('headers', {})
        if self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"

        response = requests.request(method, f"{self.url}{path}", headers=headers, **kwargs)

        if not response.ok:
            raise GancioError(response)

        return response

    # --- Setup ---

    def setup_db(self, dialect: str = 'sqlite', storage: str = '/opt/gancio/db.sqlite') -> None:
        """Configures the database during first-run setup.

        Args:
            dialect: Database dialect ('sqlite' or 'postgres').
            storage: Path to the SQLite database file. Only used when dialect is 'sqlite'.
        """
        db = {'dialect': dialect}
        if dialect == "sqlite":
            db['storage'] = storage
        self._request('POST', '/api/setup/db', json={"db": db})

    def setup_restart(self) -> dict:
        """Completes first-run setup by creating an admin user and restarting Gancio.

        Returns:
            Dict with 'email' and 'password' of the created admin.
        """
        return self._request('POST', '/api/setup/restart').json()

    # --- Auth ---

    def login(self, username: str, password: str) -> dict:
        """Logs in and stores tokens for future requests.

        Args:
            username: User email address.
            password: User password.

        Returns:
            Dict containing 'access_token', 'refresh_token', and 'username'.

        Raises:
            GancioError: If the credentials are invalid.
        """
        response = self._request('POST', '/oauth/login',
                                 data=dict(username=username,
                                           password=password,
                                           grant_type='password',
                                           client_id='self'),
                                 headers={'Content-Type': "application/x-www-form-urlencoded"})
        data = response.json()
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.logger.info(f"Logged in as '{data['username']}' @ {self.url}")
        return data

    # --- User ---

    def get_user(self) -> dict:
        """Returns the currently authenticated user.

        Returns:
            Dict with user details including 'email' and 'settings'.
        """
        return self._request('GET', '/api/user').json()

    # --- Events ---

    def get_events(self, start: int = None, end: int = None, tags: list = None,
                   places: list = None, query: str = None, max: int = None,
                   page: int = None, show_recurrent: bool = None,
                   show_multidate: bool = None) -> list[dict]:
        """Fetches events matching the given filters.

        All parameters are optional. When none are provided, returns upcoming events.

        Args:
            start: Only return events starting after this Unix timestamp.
            end: Only return events starting before this Unix timestamp.
            tags: Filter by tag names.
            places: Filter by place names.
            query: Free-text search query.
            max: Maximum number of events to return.
            page: Page number for pagination.
            show_recurrent: Include recurring events.
            show_multidate: Include multi-day events.

        Returns:
            List of event dicts.
        """
        params = {}
        if start is not None:
            params['start'] = start
        if end is not None:
            params['end'] = end
        if tags is not None:
            params['tags'] = tags
        if places is not None:
            params['places'] = places
        if query is not None:
            params['query'] = query
        if max is not None:
            params['max'] = max
        if page is not None:
            params['page'] = page
        if show_recurrent is not None:
            params['show_recurrent'] = show_recurrent
        if show_multidate is not None:
            params['show_multidate'] = show_multidate

        return self._request('GET', '/api/events', params=params).json()

    def get_event(self, slug: str) -> dict:
        """Fetches an event by its slug.

        Args:
            slug: The event's URL slug.

        Returns:
            Event dict with full details including 'place', 'tags', and 'media'.

        Raises:
            GancioError: If the event is not found (404).
        """
        return self._request('GET', f'/api/event/detail/{slug}').json()

    def create_event(self, title: str, start_datetime: int, place_name: str, place_address: str,
                     description: str = None, end_datetime: int = None,
                     place_latitude: float = None, place_longitude: float = None,
                     tags: list[str] = None, online_locations: list[str] = None,
                     image: io.BytesIO = None, image_url: str = None,
                     multidate: bool = None, recurrent: dict = None) -> dict:
        """Creates a new event.

        Args:
            title: Event title.
            start_datetime: Start time as a Unix timestamp.
            place_name: Name of the venue.
            place_address: Address of the venue.
            description: Event description (HTML allowed).
            end_datetime: End time as a Unix timestamp.
            place_latitude: Venue latitude.
            place_longitude: Venue longitude.
            tags: List of tag names.
            online_locations: List of URLs for online participation.
            image: Image file as a BytesIO object.
            image_url: URL of an image to attach.
            multidate: Whether the event spans multiple days.
            recurrent: Recurrence rules as a dict.

        Returns:
            The created event dict.
        """
        data = {'title': title,
                'start_datetime': start_datetime,
                'place_name': place_name,
                'place_address': place_address}

        if description is not None:
            data['description'] = description
        if end_datetime is not None:
            data['end_datetime'] = end_datetime
        if place_latitude is not None:
            data['place_latitude'] = place_latitude
        if place_longitude is not None:
            data['place_longitude'] = place_longitude
        if tags is not None:
            data['tags[]'] = tags
        if online_locations is not None:
            data['online_locations[]'] = online_locations
        if image_url is not None:
            data['image_url'] = image_url
        if multidate is not None:
            data['multidate'] = multidate
        if recurrent is not None:
            data['recurrent'] = json.dumps(recurrent)

        # Placeholder ensures multipart/form-data content type is set.
        # Other content types cause issues with single-element arrays.
        files = dict(image=image) if image else {'placeholder': ('', '')}

        result = self._request('POST', '/api/event', data=data, files=files).json()
        self.logger.info(f"Created event {result}")
        return result

    def update_event(self, event_id: int, title: str = None, start_datetime: int = None,
                     place_name: str = None, place_address: str = None,
                     description: str = None, end_datetime: int = None,
                     place_latitude: float = None, place_longitude: float = None,
                     tags: list[str] = None, online_locations: list[str] = None,
                     image: io.BytesIO = None, image_url: str = None,
                     multidate: bool = None, recurrent: dict = None) -> dict:
        """Updates an existing event.

        Only the provided fields are updated; omitted fields remain unchanged.

        Args:
            event_id: ID of the event to update.
            title: New event title.
            start_datetime: New start time as a Unix timestamp.
            place_name: New venue name.
            place_address: New venue address.
            description: New event description.
            end_datetime: New end time as a Unix timestamp.
            place_latitude: New venue latitude.
            place_longitude: New venue longitude.
            tags: New list of tag names (replaces existing tags).
            online_locations: New list of online URLs.
            image: New image file as a BytesIO object.
            image_url: URL of a new image to attach.
            multidate: Whether the event spans multiple days.
            recurrent: New recurrence rules as a dict.

        Returns:
            The updated event dict.
        """
        data = {'id': event_id}

        if title is not None:
            data['title'] = title
        if start_datetime is not None:
            data['start_datetime'] = start_datetime
        if place_name is not None:
            data['place_name'] = place_name
        if place_address is not None:
            data['place_address'] = place_address
        if description is not None:
            data['description'] = description
        if end_datetime is not None:
            data['end_datetime'] = end_datetime
        if place_latitude is not None:
            data['place_latitude'] = place_latitude
        if place_longitude is not None:
            data['place_longitude'] = place_longitude
        if tags is not None:
            data['tags[]'] = tags
        if online_locations is not None:
            data['online_locations[]'] = online_locations
        if image_url is not None:
            data['image_url'] = image_url
        if multidate is not None:
            data['multidate'] = multidate
        if recurrent is not None:
            data['recurrent'] = json.dumps(recurrent)

        # Placeholder ensures multipart/form-data content type is set.
        files = dict(image=image) if image else {"placeholder": ('', '')}

        result = self._request('PUT', '/api/event', data=data, files=files).json()
        self.logger.info(f'Updated event {result}')
        return result

    def delete_event(self, event_id: int) -> None:
        """Deletes an event.

        Args:
            event_id: ID of the event to delete.
        """
        self._request('DELETE', f'/api/event/{event_id}')
        self.logger.info(f"Deleted event with ID '{event_id}'")

    def confirm_event(self, event_id: int) -> None:
        """Confirms a pending event.

        Args:
            event_id: ID of the event to confirm.
        """
        self._request('PUT', f'/api/event/confirm/{event_id}')
        self.logger.info(f"Confirmed event '{event_id}'")

    # --- Places ---

    def search_place(self, query: str) -> list[dict]:
        """Searches for places by name.

        Args:
            query: Search query string.

        Returns:
            List of matching place dicts.
        """
        return self._request('GET', '/api/place', params=dict(search=query)).json()

    def get_place(self, place_name: str) -> dict | None:
        """Finds a place by exact name.

        Args:
            place_name: Exact name of the place.

        Returns:
            Place dict, or None if not found.
        """
        results = self.search_place(place_name)
        return results[0] if results else None

    def get_place_events(self, place_name: str) -> dict | None:
        """Fetches a place and its upcoming events.

        Args:
            place_name: Name of the place.

        Returns:
            Dict with place details and an 'events' list, or None if not found.
        """
        try:
            return self._request('GET', f'/api/place/{place_name}').json()
        except GancioError as e:
            if e.status_code == 404:
                return None
            raise

    # --- Pages ---

    def update_page(self, page_id: int, content: str, title: str = None,
                    visible: bool = None) -> dict:
        """Updates a page.

        Args:
            page_id: ID of the page to update.
            content: New page content (HTML).
            title: New page title.
            visible: Whether the page is visible in the navigation.

        Returns:
            The updated page dict.
        """
        data = dict(content=content)
        if title is not None:
            data['title'] = title
        if visible is not None:
            data['visible'] = visible

        result = self._request('PUT', f'/api/pages/{page_id}', data=data).json()
        self.logger.info(f"Updated page {result}")
        return result
