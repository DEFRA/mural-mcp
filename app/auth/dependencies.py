import dishka
import fastapi
from dishka.integrations import fastapi as dishka_fastapi

from app.auth import service


@dishka_fastapi.inject
async def get_current_user(
    request: fastapi.Request,
    bearer_service: dishka.FromDishka[service.BearerTokenService],
) -> str:
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise fastapi.HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.removeprefix("Bearer ").strip()

    email = await bearer_service.resolve_email(token)

    if email is None:
        raise fastapi.HTTPException(status_code=401, detail="Invalid token")

    return email
