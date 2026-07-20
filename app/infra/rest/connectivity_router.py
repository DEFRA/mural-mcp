import fastapi
from dishka.integrations import fastapi as dishka_fastapi

from app.auth import service as bearer_service_module
from app.mural.connectivity import oauth_client, state_store
from app.mural.connectivity import ports as token_store

router = fastapi.APIRouter()


@router.get("/mural/callback")
@dishka_fastapi.inject
async def mural_callback(
    code: str,
    state: str,
    store: dishka_fastapi.FromDishka[token_store.TokenStore],
    bearer_service: dishka_fastapi.FromDishka[bearer_service_module.BearerTokenService],
    states: dishka_fastapi.FromDishka[state_store.OAuthStateStore],
    oauth: dishka_fastapi.FromDishka[oauth_client.OAuthClient],
) -> dict[str, str]:
    try:
        oauth_state = states.consume(state)
    except ValueError as exc:
        raise fastapi.HTTPException(status_code=400, detail=str(exc)) from exc

    if not await bearer_service.email_exists(oauth_state.user_id):
        raise fastapi.HTTPException(status_code=403, detail="Forbidden")

    token = await oauth.exchange_code(code)

    await store.store_tokens(oauth_state.user_id, token)

    return {"status": "connected"}
