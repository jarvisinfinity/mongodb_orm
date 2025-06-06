import os
import pydantic
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient as Client, \
    AsyncIOMotorDatabase as Database, \
        AsyncIOMotorCollection as Collection

class BaseModel(pydantic.BaseModel):
    """
    By Inheriting this Class you can make your class a MongoDB Model.
    The defentiion of the Meta class is optional,
    the following are the default values,
        mongo_uri: str = os.environ.get("MONGO_URI")
        database_name: str = os.environ.get("MONGO_DATABASE")
        collection_name: str = cls.__name__
    """
    id: int = pydantic.Field(default=None)
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    @classmethod
    def __initialize__(cls, client: Client=None):
        print(f"Initializing {cls.__name__} Model")
        class Meta:
            mongo_uri: str = os.environ.get("MONGO_URI")
            database_name: str = os.environ.get("MONGO_DATABASE")
            collection_name: str = cls.__name__

        cls.default_meta = Meta()
        cls.custome_meta = getattr(cls, "Meta", Meta)()

        for key, value in Meta.__dict__.items():
            if not key.startswith('__'):  # Exclude special attributes
                setattr(cls, key, getattr(cls.custome_meta, key, value))

        if client and isinstance(client, Client):
            cls.client = client
        else:
            cls.client = Client(cls.mongo_uri)
        cls.database: Database = cls.client[cls.database_name]

        cls.collection: Collection = cls.database[cls.collection_name]
        cls.id_sequences: Collection = cls.database["id_sequences"]

    def dict(self):
        return super().model_dump()

    def json(self):
        return super().model_dump_json()

    async def _get_id(self):
        if not self.id:
            sequence = await self.id_sequences.find_one_and_update(
                {"_id": self.collection_name},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=pymongo.ReturnDocument.AFTER
            )
            self.id = sequence["seq"]
            return self.id

    @classmethod
    async def get(cls, **kwargs):
        resp = await cls.collection.find_one(kwargs)
        return cls(**resp) if resp else None

    @classmethod
    async def filter(cls, **kwargs):
        sort_by = kwargs.pop("sort_by", {"id": 1})
        distinct = kwargs.pop("distinct", None)
        limit = kwargs.pop("_limit", 0)
        skip = kwargs.pop("_skip", 0)
        only_count = kwargs.pop("only_count", False)
        projection: dict = kwargs.pop("projection", {})
        flat_projection = projection.pop("flat", False)
        if "_id" not in projection.keys():
            projection["_id"] = 0

        if distinct:
            responses = await cls.collection.distinct(distinct, filter=kwargs)
            if only_count:
                return len(responses)
            return responses
        elif only_count:
            return await cls.collection.count_documents(filter=kwargs)

        responses = cls.collection.find(filter=kwargs, projection=projection, limit=limit, skip=skip)
        if sort_by:
            responses = responses.sort(sort_by)
        if len(projection) == 1 and ("_id" in projection.keys()):
            resp = [cls(**resp) async for resp in responses] if responses else []
        elif len(projection) == 2 and ("_id" in projection.keys()) and flat_projection:
            projection.pop("_id")
            key = list(projection.keys())[0]
            resp = [resp[key] async for resp in responses] if responses else []
        else:
            resp = [resp async for resp in responses] if responses else []
        return resp

    @classmethod
    async def all(cls):
        return await cls.filter()

    @classmethod
    async def create(cls, **kwargs):
        self = cls(**kwargs)
        if not self.id:
            self.id = await self._get_id()
        result = await cls.collection.insert_one(self.dict())
        return await self.get(_id=result.inserted_id)

    @classmethod
    async def get_or_create(cls, **kwargs):
        resp = await cls.get(**kwargs)
        if resp:
            return (resp, False)
        return (await cls.create(**kwargs), True)

    async def save(self, only_update=False):
        if not self.id:
            if only_update:
                return False
            else:
                self.id = await self._get_id()
        await self.collection.update_one({"id": self.id}, {"$set": self.dict()}, upsert=not only_update)
        return self

    async def delete(self):
        return await self.collection.delete_one({"id": self.id})

    @classmethod
    async def direct_delete(self, **kwargs):
        return await self.collection.delete_many(filter=kwargs)

    @classmethod
    async def aggregate(cls, *args, **kwargs):
        data = await cls.collection.aggregate(*args, **kwargs)
        return list(data) if data else None

    async def refresh_from_db(self):
        if self.id:
            resp = await self.get(id=self.id)
            if resp:
                self.__dict__.update(resp.__dict__)
                return self
        return None

    @classmethod
    async def make_unique(cls, field, order=pymongo.ASCENDING):
        contraint_key = field + "_" + "1" if order == pymongo.ASCENDING else "-1"
        if contraint_key not in await cls.collection.index_information():
            print('Index Added', await cls.collection.create_index(field, unique=True))
        else:
            print('Index already exists')

    @classmethod
    async def make_unique_together(cls, fields):
        constraints = []
        contraint_keys = []
        for key, value in fields.items():
            constraints.append((key, value))
            contraint_keys.append(key + "_" + "1" if value == pymongo.ASCENDING else "-1")
            if "_".join(contraint_keys) not in await cls.collection.index_information():
                print('Index Added', await cls.collection.create_index(constraints, unique=value))
            else:
                print('Index already exists')
