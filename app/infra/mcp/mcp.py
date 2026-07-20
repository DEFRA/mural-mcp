import contextlib
from collections.abc import AsyncGenerator
from typing import Any

import dishka
import fastmcp

from app.auth import verifier as auth_verifier


def build_mcp_app(container: dishka.AsyncContainer) -> fastmcp.FastMCP:
    verifier = auth_verifier.BearerTokenVerifier(container)

    @contextlib.asynccontextmanager
    async def _lifespan(_server: fastmcp.FastMCP) -> AsyncGenerator[dict[str, Any]]:
        yield {"container": container}

    return fastmcp.FastMCP("mural-mcp", lifespan=_lifespan, auth=verifier)
