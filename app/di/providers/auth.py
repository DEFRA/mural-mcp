import dishka
from pymongo.asynchronous import database

from app.auth import service as bearer_service


class AuthProvider(dishka.Provider):
    @dishka.provide(scope=dishka.Scope.APP)
    def provide_bearer_token_service(
        self,
        db: database.AsyncDatabase,  # type: ignore[type-arg]
    ) -> bearer_service.BearerTokenService:
        return bearer_service.MongoBearerTokenService(db["bearer_tokens"])
