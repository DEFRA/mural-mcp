import pytest

from app.common import mongo


@pytest.mark.asyncio
async def test_check_connection_pings_database(mocker):
    client = mocker.MagicMock()
    db_conn = mocker.MagicMock()
    client.get_database.return_value = db_conn
    db_conn.command = mocker.AsyncMock(return_value={"ok": 1})

    await mongo.check_connection(client, "my-db")

    client.get_database.assert_called_once_with("my-db")
    db_conn.command.assert_awaited_once_with("ping")


@pytest.mark.asyncio
async def test_check_connection_propagates_command_error(mocker):
    client = mocker.MagicMock()
    db_conn = mocker.MagicMock()
    client.get_database.return_value = db_conn
    db_conn.command = mocker.AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        await mongo.check_connection(client, "my-db")
