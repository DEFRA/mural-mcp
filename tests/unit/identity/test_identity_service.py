import pytest

from app.identity import service as identity_service
from tests.fakes import in_memory_identity_store


@pytest.fixture
def users() -> in_memory_identity_store.InMemoryUserStore:
    return in_memory_identity_store.InMemoryUserStore()


@pytest.fixture
def service(
    users: in_memory_identity_store.InMemoryUserStore,
) -> identity_service.IdentityService:
    return identity_service.IdentityService(users)


@pytest.mark.asyncio
async def test_resolve_or_create_creates_a_new_user(
    service: identity_service.IdentityService,
) -> None:
    user = await service.resolve_or_create("entra-oid-123", email="a@example.com")

    assert user.external_id == "entra-oid-123"
    assert user.email == "a@example.com"
    assert user.user_id.startswith("usr_")


@pytest.mark.asyncio
async def test_resolve_or_create_is_idempotent_per_external_id(
    service: identity_service.IdentityService,
) -> None:
    first = await service.resolve_or_create("entra-oid-123", email="a@example.com")
    second = await service.resolve_or_create("entra-oid-123", email="a@example.com")

    assert first.user_id == second.user_id


@pytest.mark.asyncio
async def test_resolve_or_create_different_external_ids_get_different_users(
    service: identity_service.IdentityService,
) -> None:
    first = await service.resolve_or_create("entra-oid-123")
    second = await service.resolve_or_create("entra-oid-456")

    assert first.user_id != second.user_id


@pytest.mark.asyncio
async def test_get_by_user_id_found(
    service: identity_service.IdentityService,
) -> None:
    created = await service.resolve_or_create("entra-oid-123")

    found = await service.get_by_user_id(created.user_id)

    assert found is not None
    assert found.user_id == created.user_id


@pytest.mark.asyncio
async def test_get_by_user_id_not_found(
    service: identity_service.IdentityService,
) -> None:
    assert await service.get_by_user_id("usr_does-not-exist") is None
