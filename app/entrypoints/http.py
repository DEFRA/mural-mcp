import collections
import contextlib
import logging

import fastapi
import fastmcp.utilities.lifespan as fastmcp_lifespan
import uvicorn

from app import config as app_config
from app.common import tracing
from app.di import container as di_container
from app.health import router as health_router
from app.infra.mcp import mcp
from app.infra.mcp import tools as mural_tools
from app.infra.rest import board_router as mural_board_router
from app.infra.rest import connectivity_router as mural_connect_router

logger = logging.getLogger(__name__)


def create_app(cfg: app_config.AppConfig) -> fastapi.FastAPI:
    container = di_container.build_async_container()
    mcp_fastmcp = mcp.build_mcp_app(container)
    mural_tools.register_tools(mcp_fastmcp)
    mcp_app = mcp_fastmcp.http_app(path="/")

    @contextlib.asynccontextmanager
    async def lifespan(_: fastapi.FastAPI) -> collections.abc.AsyncGenerator[None]:
        async with container:
            _.state.dishka_container = container
            yield

    fastapi_app = fastapi.FastAPI(
        lifespan=fastmcp_lifespan.combine_lifespans(lifespan, mcp_app.lifespan)
    )

    fastapi_app.mount("/mcp", mcp_app)

    fastapi_app.add_middleware(tracing.ContainerMiddleware)
    fastapi_app.add_middleware(tracing.TraceIdMiddleware, cfg=cfg)
    fastapi_app.include_router(health_router.router)
    fastapi_app.include_router(mural_connect_router.router, prefix="/connect")
    fastapi_app.include_router(mural_board_router.router, prefix="/boards")

    return fastapi_app


def main() -> None:  # pragma: no cover
    with di_container.build_sync_container() as _container:
        cfg = _container.get(app_config.AppConfig)

    fastapi_app = create_app(cfg)

    uvicorn.run(
        fastapi_app,
        host=cfg.host,
        port=cfg.port,
        log_config=cfg.log_config,
        reload=cfg.python_env == "development",
    )


if __name__ == "__main__":  # pragma: no cover
    main()
