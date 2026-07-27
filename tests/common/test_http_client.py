from app.common import http_client


def test_create_async_client_bakes_trace_id_into_headers(fake_config):
    client = http_client.create_async_client(
        tracing_header=fake_config.tracing_header,
        trace_id="trace-id-value",
    )

    assert client.headers[fake_config.tracing_header] == "trace-id-value"


def test_create_async_client_omits_header_when_trace_id_missing(fake_config):
    client = http_client.create_async_client(
        tracing_header=fake_config.tracing_header,
        trace_id=None,
    )

    assert fake_config.tracing_header not in client.headers


def test_create_client_bakes_trace_id_into_headers(fake_config):
    client = http_client.create_client(
        tracing_header=fake_config.tracing_header,
        trace_id="trace-id-value",
    )

    assert client.headers[fake_config.tracing_header] == "trace-id-value"
