import fastapi.testclient
import pytest

import app.entrypoints.http as main_mod


@pytest.fixture
def client(fake_config):
    with fastapi.testclient.TestClient(main_mod.create_app(fake_config)) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root(client):
    response = client.get("/")
    assert response.status_code == 404
