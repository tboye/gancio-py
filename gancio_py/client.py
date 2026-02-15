import io
import json
import logging

import requests

from gancio_py.exceptions import GancioError


class Gancio:
    """Client for the Gancio API."""

    def __init__(self, url: str, access_token: str = None):
        self.url = url.rstrip("/")
        self.access_token = access_token
        self.refresh_token = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Send a request to the Gancio API and return the response.

        Raises GancioError on HTTP errors.
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
        """Configure the database during first-run setup."""
        db = {'dialect': dialect}
        if dialect == "sqlite":
            db['storage'] = storage
        self._request('POST', '/api/setup/db', json={"db": db})

    def setup_restart(self) -> dict:
        """Complete first-run setup. Creates admin user and restarts Gancio.

        Returns dict with 'email' and 'password' of the created admin.
        """
        return self._request('POST', '/api/setup/restart').json()

    # --- Auth ---

    def login(self, username: str, password: str) -> dict:
        """Logs in and stores tokens for future requests.

        Returns:
            Login response dict containing access_token, refresh_token and username.

        Raises:
            GancioError: Error occurred while executing the request.
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
        """Returns the currently authenticated user."""
        return self._request('GET', '/api/user').json()

    # --- Events ---

    def get_events(self, start: int = None, end: int = None, tags: list = None,
                   places: list = None, query: str = None, max: int = None,
                   page: int = None, show_recurrent: bool = None,
                   show_multidate: bool = None) -> list[dict]:
        """Returns events matching the given filters."""
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
        """Gets event by its slug."""
        return self._request('GET', f'/api/event/detail/{slug}').json()

    def create_event(self, title: str, start_datetime: int, place_name: str, place_address: str,
                     description: str = None, end_datetime: int = None,
                     place_latitude: float = None, place_longitude: float = None,
                     tags: list[str] = None, online_locations: list[str] = None,
                     image: io.BytesIO = None, image_url: str = None,
                     multidate: bool = None, recurrent: dict = None) -> dict:
        """Creates an event. Returns the created event."""
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
        """Updates an event. Returns the updated event."""
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
        """Deletes an event by ID."""
        self._request('DELETE', f'/api/event/{event_id}')
        self.logger.info(f"Deleted event with ID '{event_id}'")

    def confirm_event(self, event_id: int) -> None:
        """Confirms an event by ID."""
        self._request('PUT', f'/api/event/confirm/{event_id}')
        self.logger.info(f"Confirmed event '{event_id}'")

    # --- Places ---

    def search_place(self, query: str) -> list[dict]:
        """Searches for places by name. Returns list of matching places."""
        return self._request('GET', '/api/place', params=dict(search=query)).json()

    def get_place(self, place_name: str) -> dict | None:
        """Gets a place by exact name. Returns None if not found."""
        results = self.search_place(place_name)
        return results[0] if results else None

    def get_place_events(self, place_name: str) -> dict | None:
        """Gets a place and its future events by place name.

        Returns None if place not found.
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
        """Updates a page by ID. Returns the updated page."""
        data = dict(content=content)
        if title is not None:
            data['title'] = title
        if visible is not None:
            data['visible'] = visible

        result = self._request('PUT', f'/api/pages/{page_id}', data=data).json()
        self.logger.info(f"Updated page {result}")
        return result
