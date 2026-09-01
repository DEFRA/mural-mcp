import httpx


class MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, responses: list[httpx.Response | Exception]) -> None:
        self._queue = list(responses)
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self._queue:
            msg = "MockTransport: no more responses queued"
            raise RuntimeError(msg)
        item = self._queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_mock_client(
    responses: list[httpx.Response | Exception],
) -> tuple[httpx.AsyncClient, MockTransport]:
    transport = MockTransport(responses)
    client = httpx.AsyncClient(transport=transport)
    return client, transport
