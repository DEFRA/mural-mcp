import dishka
from pymongo.asynchronous import database

from app.identity import mongo_store, ports, service


class IdentityProvider(dishka.Provider):
    scope = dishka.Scope.APP

    @dishka.provide
    def provide_pat_store(
        self,
        db: database.AsyncDatabase,  # type: ignore[type-arg]
    ) -> ports.PersonalAccessTokenStore:
        return mongo_store.MongoPersonalAccessTokenStore(db["personal_access_tokens"])

    @dishka.provide
    def provide_personal_token_service(
        self, tokens: ports.PersonalAccessTokenStore
    ) -> service.PersonalTokenService:
        return service.PersonalTokenService(tokens)
