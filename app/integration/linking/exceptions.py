class MuralTokenError(Exception):
    """Raised when no valid Mural access token is available for a user."""


class OAuthStateError(Exception):
    """Raised when an OAuth state token is unknown, already consumed, or
    expired."""


class LinkMismatchError(Exception):
    """Raised when a completed OAuth callback's state was issued for a
    different user than the one completing it."""


class MuralApiError(Exception):
    """Raised when the Mural API returns a non-2xx response.

    Wraps the underlying httpx.HTTPStatusError so callers never see raw vendor
    URLs, headers, or response bodies escape to a REST client or an LLM tool
    caller.
    """

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Mural API request failed with status {status_code}.")


class MuralUnavailableError(Exception):
    """Raised when a request to the Mural API fails before any response is
    received (e.g. Mural is unreachable, DNS resolution fails, or the
    connection times out).

    Wraps the underlying httpx.RequestError, distinct from MuralApiError
    which means Mural *did* respond, just with a non-2xx status.
    """
