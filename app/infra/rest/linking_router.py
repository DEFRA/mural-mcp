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


class MuralStatusResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )

    linked: bool
    access_token_expires_at: datetime.datetime | None = pydantic.Field(
        default=None, alias="accessTokenExpiresAt"
    )


@router.get("/authorization-url")
@dishka_fastapi.inject
async def get_mural_authorization_url(
    linking: dishka_fastapi.FromDishka[linking_service.LinkingService],
    principal: Annotated[
        principal_module.Principal, fastapi.Depends(auth_deps.get_principal)
    ],
) -> AuthorizationUrlResponse:
    # principal.user_id is resolved/minted transparently on every request by
    # get_principal's UserResolver (TrustedHeaderUserResolver by default) —
    # see app/infra/rest/auth/resolver.py. It isn't something the caller
    # must already have; a first-time caller here has no PAT yet, only the
    # portal-asserted email in the trusted header.
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
