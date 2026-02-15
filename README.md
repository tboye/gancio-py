# gancio-py

Python client for the [Gancio](https://gancio.org) event platform API.

## Installation

```bash
pip install gancio-py
```

## Usage

```python
from gancio_py import Gancio

# Connect and log in
gancio = Gancio("https://your-gancio-instance.org")
gancio.login("user@example.com", "password")

# Or use a pre-existing token
gancio = Gancio("https://your-gancio-instance.org", access_token="your-token")

# Create an event
event = gancio.create_event(
    title="My Event",
    start_datetime=1700000000,
    place_name="The Venue",
    place_address="123 Main St",
    tags=["music", "live"],
)

# List events
events = gancio.get_events(tags=["music"])

# Get a specific event
event = gancio.get_event("my-event")

# Update an event
gancio.update_event(event_id=1, title="Updated Title")

# Delete an event
gancio.delete_event(event_id=1)

# Search places
places = gancio.search_place("Venue")
```

## Development

Run integration tests locally with Docker:

```bash
uv sync --extra test

# Fresh container (runs first-time setup automatically):
docker compose down -v && docker compose up -d
uv run pytest -m integration -v --cov

# Or against an existing instance with known credentials:
GANCIO_URL=http://localhost:13120 \
GANCIO_ADMIN_EMAIL=admin \
GANCIO_ADMIN_PASSWORD=yourpassword \
uv run pytest -m integration -v --cov
```