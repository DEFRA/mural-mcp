from pymongo.asynchronous import collection

from app.mural.connectivity import models, ports


class MongoTokenStore(ports.TokenStore):
    def __init__(self, mural_collection: collection.AsyncCollection) -> None:  # type: ignore[type-arg]
        self._collection = mural_collection

    async def store_tokens(self, user_id: str, token: models.MuralToken) -> None:
        doc = {"user_id": user_id, **token.model_dump()}

        await self._collection.replace_one(
            {"user_id": user_id}, {"$set": doc}, upsert=True
        )

    async def get_tokens(self, user_id: str) -> models.MuralToken | None:
        doc = await self._collection.find_one({"user_id": user_id}, {"_id": 0})

        if doc is None:
            return None

        return models.MuralToken.model_validate(doc)

    async def delete_tokens(self, user_id: str) -> None:
        await self._collection.delete_one({"user_id": user_id})
