import datetime
import unittest.mock

from pymongo import common as pymongo_common

from app.identity import models
from app.identity import mongo_store as identity_mongo_store

_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)


def _user(**overrides: object) -> models.User:
    defaults: dict[str, object] = {
        "user_id": "usr_abc",
        "external_id": "entra-oid-123",
        "email": "a@example.com",
        "created_at": _NOW,
    }
    defaults.update(overrides)
    return models.User(**defaults)  # type: ignore[arg-type]


def _pat(**overrides: object) -> models.PersonalAccessToken:
    defaults: dict[str, object] = {
        "id": "pat_abc",
        "user_id": "usr_abc",
        "token_hash": "deadbeef",
        "prefix": "mmcp_abcd1234",
        "label": "Claude Code",
        "created_at": _NOW,
        "expires_at": _NOW + datetime.timedelta(days=90),
    }
    defaults.update(overrides)
    return models.PersonalAccessToken(**defaults)  # type: ignore[arg-type]


class TestMongoUserStore:
    async def test_create_replacement_is_valid_for_real_pymongo(self) -> None:
        mock_col = unittest.mock.AsyncMock()
        store = identity_mongo_store.MongoUserStore(mock_col)

        await store.create(_user())

        replacement = mock_col.replace_one.await_args[0][1]
        pymongo_common.validate_ok_for_replace(replacement)
        assert mock_col.replace_one.await_args[1]["upsert"] is True

    async def test_get_by_external_id_found(self) -> None:
        mock_col = unittest.mock.AsyncMock()
        mock_col.find_one.return_value = _user().model_dump()
        store = identity_mongo_store.MongoUserStore(mock_col)

        result = await store.get_by_external_id("entra-oid-123")

        assert result is not None
        assert result.user_id == "usr_abc"
        mock_col.find_one.assert_awaited_once_with(
            {"external_id": "entra-oid-123"}, {"_id": 0}
        )

    async def test_get_by_external_id_not_found(self) -> None:
        mock_col = unittest.mock.AsyncMock()
        mock_col.find_one.return_value = None
        store = identity_mongo_store.MongoUserStore(mock_col)

        assert await store.get_by_external_id("unknown") is None


class TestMongoPersonalAccessTokenStore:
    async def test_create_replacement_is_valid_for_real_pymongo(self) -> None:
        mock_col = unittest.mock.AsyncMock()
        store = identity_mongo_store.MongoPersonalAccessTokenStore(mock_col)

        await store.create(_pat())

        replacement = mock_col.replace_one.await_args[0][1]
        pymongo_common.validate_ok_for_replace(replacement)
        assert mock_col.replace_one.await_args[1]["upsert"] is True

    async def test_get_by_hash_found(self) -> None:
        mock_col = unittest.mock.AsyncMock()
        mock_col.find_one.return_value = _pat().model_dump()
        store = identity_mongo_store.MongoPersonalAccessTokenStore(mock_col)

        result = await store.get_by_hash("deadbeef")

        assert result is not None
        assert result.id == "pat_abc"

    async def test_revoke_uses_set_operator(self) -> None:
        """Unlike replace_one, update_one's document IS an update spec, so
        $set is correct here -- this is the counterpart to the earlier bug
        where $set was wrongly applied to a full-document replace_one call.
        """
        mock_col = unittest.mock.AsyncMock()
        store = identity_mongo_store.MongoPersonalAccessTokenStore(mock_col)

        await store.revoke("pat_abc")

        args = mock_col.update_one.await_args
        assert args[0][0] == {"id": "pat_abc"}
        assert "$set" in args[0][1]
        assert "revoked_at" in args[0][1]["$set"]

    async def test_touch_last_used_uses_set_operator(self) -> None:
        mock_col = unittest.mock.AsyncMock()
        store = identity_mongo_store.MongoPersonalAccessTokenStore(mock_col)

        await store.touch_last_used("pat_abc", _NOW)

        mock_col.update_one.assert_awaited_once_with(
            {"id": "pat_abc"}, {"$set": {"last_used_at": _NOW}}
        )
