import datetime
from typing import Annotated

import fastapi
import pydantic
from dishka.integrations import fastapi as dishka_fastapi
from pydantic import alias_generators

from app.auth import principal as principal_module
from app.infra.rest.auth import dependencies as auth_deps
from app.integration.linking import exceptions
from app.integration.linking import service as linking_service
from app.integration.mural import connection_test_service as mural_test_service

router = fastapi.APIRouter()


class MuralCallbackQuery(pydantic.BaseModel):
    code: str
    state: str


class AuthorizationUrlResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    authorization_url: str


class CallbackResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    status: str


class TestConnectionResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    status: str


class MuralStatusResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    linked: bool
    access_token_expires_at: datetime.datetime | None = pydantic.Field(default=None)


@router.get("/authorization-url")
@dishka_fastapi.inject
async def get_mural_authorization_url(
    linking: dishka_fastapi.FromDishka[linking_service.LinkingService],
    principal: Annotated[
        principal_module.Principal, fastapi.Depends(auth_deps.get_principal)
    ],
) -> AuthorizationUrlResponse:
    url = await linking.get_authorization_url(principal.user_id)

    return AuthorizationUrlResponse(authorization_url=url)


@router.get("/callback")
@dishka_fastapi.inject
async def mural_callback(
    query: Annotated[MuralCallbackQuery, fastapi.Query()],
    linking: dishka_fastapi.FromDishka[linking_service.LinkingService],
    principal: Annotated[
        principal_module.Principal, fastapi.Depends(auth_deps.get_principal)
    ],
) -> CallbackResponse:
    try:
        await linking.complete_connection(principal.user_id, query.code, query.state)
    except exceptions.OAuthStateError as exc:
        raise fastapi.HTTPException(status_code=400, detail=str(exc)) from exc
    except exceptions.LinkMismatchError as exc:
        raise fastapi.HTTPException(status_code=403, detail="Forbidden") from exc
    except exceptions.MuralUnavailableError as exc:
        raise fastapi.HTTPException(
            status_code=502, detail="Mural API is unreachable"
        ) from exc
    except exceptions.MuralApiError as exc:
        raise fastapi.HTTPException(status_code=502, detail=str(exc)) from exc

    return CallbackResponse(status="success")


@router.get("/status")
@dishka_fastapi.inject
async def get_mural_status(
    linking: dishka_fastapi.FromDishka[linking_service.LinkingService],
    principal: Annotated[
        principal_module.Principal, fastapi.Depends(auth_deps.get_principal)
    ],
) -> MuralStatusResponse:
    status = await linking.get_connection_status(principal.user_id)

    return MuralStatusResponse(
        linked=status.linked,
        access_token_expires_at=status.access_token_expires_at,
    )


@router.get("/test-connection")
@dishka_fastapi.inject
async def test_connection(
    test_svc: dishka_fastapi.FromDishka[mural_test_service.MuralConnectionTestService],
    principal: Annotated[
        principal_module.Principal, fastapi.Depends(auth_deps.get_principal)
    ],
) -> TestConnectionResponse:
    try:
        await test_svc.test_connection(principal.user_id)
    except exceptions.MuralTokenError as exc:
        raise fastapi.HTTPException(
            status_code=401,
            detail="Mural MCP does not have a valid access token for this user",
        ) from exc
    except exceptions.MuralApiError as exc:
        if exc.status_code == 401:
            raise fastapi.HTTPException(
                status_code=401, detail="Mural API has rejected the access token"
            ) from exc

        raise fastapi.HTTPException(status_code=502, detail=str(exc)) from exc
    except exceptions.MuralUnavailableError as exc:
        raise fastapi.HTTPException(
            status_code=502, detail="Mural API is unreachable"
        ) from exc

    return TestConnectionResponse(status="success")
