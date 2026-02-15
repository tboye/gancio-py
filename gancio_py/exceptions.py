class GancioError(Exception):
    """
    Raised when a Gancio API request fails.

    Example: 'GancioError: POST /oauth/login -> 500: Internal Server Error'
    """

    def __init__(self, response):
        self.status_code = response.status_code
        self.response_body = response.text
        super().__init__(f"{response.request.method} {response.request.path_url} -> {response.status_code}: {response.text}")
