import abc

from pymongo.asynchronous import collection


class BearerTokenService(abc.ABC):
    @abc.abstractmethod
    async def resolve_email(self, token: str) -> str | None: ...

    @abc.abstractmethod
    async def email_exists(self, email: str) -> bool: ...

    @abc.abstractmethod
    async def store_token(self, email: str, token: str) -> None: ...

    @abc.abstractmethod
    async def delete_token(self, email: str) -> None: ...


class MongoBearerTokenService(BearerTokenService):
    def __init__(self, bearer_collection: collection.AsyncCollection) -> None:  # type: ignore[type-arg]
        self._collection = bearer_collection

    async def resolve_email(self, token: str) -> str | None:
        doc = await self._collection.find_one({"token": token}, {"_id": 0, "email": 1})

        if doc is None:
            return None

        return str(doc["email"])

    async def email_exists(self, email: str) -> bool:
        doc = await self._collection.find_one({"email": email}, {"_id": 1})
        return doc is not None

    async def store_token(self, email: str, token: str) -> None:
        doc = {"email": email, "token": token}

        await self._collection.replace_one({"email": email}, doc, upsert=True)

    async def delete_token(self, email: str) -> None:
        await self._collection.delete_one({"email": email})
