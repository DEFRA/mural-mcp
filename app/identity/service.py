import datetime
import hashlib
import secrets
import uuid

from app.identity import exceptions, models, ports

_TOKEN_ENTROPY_BYTES = 32
_PREFIX_DISPLAY_LENGTH = 8

TOKEN_PREFIX = "mmcp_"  # noqa: S105
DEFAULT_TTL_DAYS = 90
MAX_TTL_DAYS = 365
LAST_USED_THROTTLE_SECONDS = 300


class PersonalTokenService:
    """Mints, verifies, lists and revokes personal access tokens.

    The plaintext secret exists only in memory between generation and the
    single mint-time response — only its SHA-256 hash is ever persisted, so
    there is no code path that can return it a second time. A plain hash
    (not a password KDF) is correct here: the secret is 256 bits of random
    entropy, not a human-chosen password, so there is nothing a KDF's
    slow-hashing would protect against.
    """

    def __init__(
        self,
        tokens: ports.PersonalAccessTokenStore,
        *,
        token_prefix: str = TOKEN_PREFIX,
        default_ttl_days: int = DEFAULT_TTL_DAYS,
        max_ttl_days: int = MAX_TTL_DAYS,
        last_used_throttle_seconds: int = LAST_USED_THROTTLE_SECONDS,
    ) -> None:
        self._tokens = tokens
        self._token_prefix = token_prefix
        self._default_ttl_days = default_ttl_days
        self._max_ttl_days = max_ttl_days
        self._last_used_throttle_seconds = last_used_throttle_seconds

    @staticmethod
    def _hash(secret: str) -> str:
        return hashlib.sha256(secret.encode()).hexdigest()

    async def mint(
        self, user_id: str, label: str, ttl_days: int | None = None
    ) -> tuple[models.PersonalAccessToken, str]:
        days = min(ttl_days or self._default_ttl_days, self._max_ttl_days)
        secret = self._token_prefix + secrets.token_urlsafe(_TOKEN_ENTROPY_BYTES)
        now = datetime.datetime.now(datetime.UTC)

        token = models.PersonalAccessToken(
            id=f"pat_{uuid.uuid4().hex}",
            user_id=user_id,
            token_hash=self._hash(secret),
            prefix=secret[: len(self._token_prefix) + _PREFIX_DISPLAY_LENGTH],
            label=label,
            created_at=now,
            expires_at=now + datetime.timedelta(days=days),
        )
        await self._tokens.create(token)
        return token, secret

    async def verify(self, secret: str) -> models.PersonalAccessToken:
        if not secret.startswith(self._token_prefix):
            msg = "Presented token does not have the expected prefix."
            raise exceptions.UnknownTokenError(msg)

        record = await self._tokens.get_by_hash(self._hash(secret))
        if record is None:
            msg = "No personal access token matches the presented secret."
            raise exceptions.UnknownTokenError(msg)

        if record.revoked_at is not None:
            msg = f"Personal access token {record.id} has been revoked."
            raise exceptions.TokenRevokedError(msg)

        now = datetime.datetime.now(datetime.UTC)
        if record.expires_at <= now:
            msg = f"Personal access token {record.id} expired at {record.expires_at.isoformat()}."
            raise exceptions.TokenExpiredError(msg)

        stale = record.last_used_at is None or (
            now - record.last_used_at
        ) > datetime.timedelta(seconds=self._last_used_throttle_seconds)
        if stale:
            await self._tokens.touch_last_used(record.id, now)

        return record

    async def list_for_user(self, user_id: str) -> list[models.PersonalAccessToken]:
        return await self._tokens.list_for_user(user_id)

    async def revoke(self, user_id: str, token_id: str) -> None:
        record = await self._tokens.get(token_id)
        if record is None or record.user_id != user_id:
            msg = f"Personal access token {token_id} not found."
            raise exceptions.TokenNotFoundError(msg)
        await self._tokens.revoke(token_id)
