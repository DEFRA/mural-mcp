class AccessRequestNotFoundError(Exception):
    """Raised when an access request id does not exist."""


class AccessRequestAlreadyDecidedError(Exception):
    """Raised when approving/rejecting a request that is no longer pending."""


class AccessRequestAlreadyOpenError(Exception):
    """Raised when a user already has a non-rejected request for a board."""
