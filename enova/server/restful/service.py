import math
import dataclasses
from typing import Type, Dict, List
from sqlalchemy import or_
from sqlalchemy import select, func, delete
from enova.common.logger import LOGGER
from enova.common.error import ArgsError, EmergingAIBaseError
from enova.database.relation.orm.base import EmergingAIDBModelBase
from enova.database.relation.transaction.session import get_async_session


def update_model_ins(model_ins, args):
    """"""
    for k, v in args.items():
        if v is not None and hasattr(model_ins, k) and getattr(model_ins, k) != v:
            setattr(model_ins, k, v)
    return model_ins


@dataclasses.dataclass
class SingleResource:
    db_model_cls: Type[EmergingAIDBModelBase]
    args: Dict
    model_existed_error: Type[EmergingAIBaseError] = None
    model_not_existed_error: Type[EmergingAIBaseError] = None

    def __post_init__(self):
        self._query = None
        self._filter_conditions = None

    @property
    def filter_conditions(self):
        if self._filter_conditions is None:
            self._filter_conditions = [
                getattr(self.db_model_cls, p_name) == self.args[p_name]
                for p_name in self.db_model_cls.primary_column_names
            ]
        return self._filter_conditions

    @property
    def query(self):
        if self._query is None:
            self._query = select(self.db_model_cls).filter(*self.filter_conditions)
        return self._query

    async def is_existed(self):
        async with get_async_session() as async_session:
            return await async_session.scalar(select(func.count()).select_from(self.query))

    async def delete(self, force=True):
        """"""
        if not (await self.is_existed()):
            if self.model_not_existed_error:
                raise self.model_not_existed_error()
            raise EmergingAIBaseError("resource is not existed")
        async with get_async_session() as async_session:
            if force:
                delete_query = delete(self.db_model_cls).filter(*self.filter_conditions)
                await async_session.execute(delete_query)
            else:
                model_dict = await self.get()
                model_dict["is_deleted"] = 1
                await async_session.merge(self.db_model_cls(**model_dict))

    async def update(self):
        """"""
        if not (await self.is_existed()):
            if self.model_not_existed_error:
                raise self.model_not_existed_error()
            raise EmergingAIBaseError("resource is not existed")
        async with get_async_session() as async_session:
            db_model = (await async_session.execute(self.query)).first()[0]
            update_model_ins(db_model, self.args)
            await async_session.merge(db_model)
            await async_session.flush()
            db_model_dict = db_model.dict
        return db_model_dict

    async def create(self):
        db_model = self.db_model_cls(**self.args)
        async with get_async_session() as async_session:
            async_session.add(db_model)
            await async_session.flush()
            db_model_dict = db_model.dict
        return db_model_dict

    async def get(self):
        if not (await self.is_existed()):
            if self.model_not_existed_error:
                raise self.model_not_existed_error()
            raise EmergingAIBaseError("resource is not existed")
        async with get_async_session() as async_session:
            db_model = (await async_session.execute(self.query)).first()[0]
            return db_model.dict


class BaseApiService:
    DB_MODEL_CLS: Type[EmergingAIDBModelBase] = NotImplemented
    FUZZY_FIELD_LIST: List = None
    START_TIME_FIELD: str = None
    END_TIME_FIELD: str = None
    MODEL_NOT_EXISTED_ERROR: Type[EmergingAIBaseError] = None
    MODEL_EXISTED_ERROR: Type[EmergingAIBaseError] = None
    IGNORE_CASE_FIELD_LIST: List = None

    def build_query_condition(
        self,
        args: Dict,
        db_model_cls=None,
        start_time_column=None,
        end_time_column=None,
        fuzzy_column_list=None,
    ):
        and_conditions = []
        or_conditions = []
        for k, v in args.items():
            if k in ("page", "size", "order_by", "order_type"):
                continue
            if v is not None:
                if k == "start_time":
                    if start_time_column:
                        and_conditions.append(getattr(db_model_cls, start_time_column) >= v)
                    else:
                        and_conditions.append(getattr(db_model_cls, k) >= v)
                elif k == "end_time":
                    if end_time_column:
                        and_conditions.append(getattr(db_model_cls, end_time_column) <= v)
                    else:
                        and_conditions.append(getattr(db_model_cls, k) <= v)
                elif k == "fuzzy" and fuzzy_column_list:
                    for fuzzy_column in fuzzy_column_list:
                        or_conditions.append(getattr(db_model_cls, fuzzy_column).contains(v))
                elif k in db_model_cls.column_dict:
                    if isinstance(v, list) or isinstance(v, set):
                        sub_or_conditions = [getattr(db_model_cls, k) == v_item for v_item in v]
                        and_conditions.append(or_(*sub_or_conditions))
                    else:
                        if (
                            self.IGNORE_CASE_FIELD_LIST
                            and k in self.IGNORE_CASE_FIELD_LIST
                            and k in db_model_cls.string_names
                        ):
                            and_conditions.append(func.lower(getattr(db_model_cls, k)) == v)
                        else:
                            and_conditions.append(getattr(db_model_cls, k) == v)
                else:
                    LOGGER.warning(f"key: {k} is not belongs to db_model_cls: {db_model_cls}")
        return and_conditions + ([or_(*or_conditions)] if or_conditions else [])

    async def common_list(
        self,
        args,
        db_model_cls=None,
        extra_conditions=None,
        start_time_field=None,
        end_time_field=None,
        fuzzy_field_list=None,
    ):
        """"""
        ret = {
            "total_num": 0,
            "page": args["page"],
            "size": args["size"],
            "num": 0,
            "data": [],
            "total_page": 0,
        }

        start_time_field = self.START_TIME_FIELD if start_time_field is None else start_time_field
        end_time_field = self.END_TIME_FIELD if end_time_field is None else end_time_field
        fuzzy_field_list = self.FUZZY_FIELD_LIST if fuzzy_field_list is None else fuzzy_field_list
        db_model_cls = db_model_cls if db_model_cls is not None else self.DB_MODEL_CLS
        filter_conditions = self.build_query_condition(
            args, db_model_cls, start_time_field, end_time_field, fuzzy_field_list
        )
        filter_conditions.extend(extra_conditions or [])
        async with get_async_session() as async_session:
            query = select(db_model_cls).filter(*filter_conditions)
            total_num = await async_session.scalar(select(func.count()).select_from(query))
            if args.get("order_by") and args.get("order_type"):
                query = query.order_by(getattr(getattr(db_model_cls, args["order_by"]), args["order_type"])())
            if args.get("size") is not None:
                query = query.limit(args["size"])
                if args.get("page") is not None:
                    query = query.offset(args["size"] * (args["page"] - 1))
            query_result = await async_session.execute(query)
            data = [datum[0].dict for datum in query_result.all()]
        ret["total_num"] = total_num
        ret["data"] = data
        ret["num"] = len(data)
        ret["total_page"] = int(math.ceil(total_num / ret["size"]))
        return ret

    async def common_update(self, args, db_model_cls=None):
        """basic udpate for orm"""
        db_model_cls = db_model_cls if db_model_cls is not None else self.DB_MODEL_CLS
        return await SingleResource(
            db_model_cls, args, self.MODEL_EXISTED_ERROR, self.MODEL_NOT_EXISTED_ERROR
        ).update()

    async def common_delete(self, args, db_model_cls=None, force=True):
        """basic delete for orm"""
        db_model_cls = db_model_cls if db_model_cls is not None else self.DB_MODEL_CLS
        await SingleResource(db_model_cls, args, self.MODEL_EXISTED_ERROR, self.MODEL_NOT_EXISTED_ERROR).delete(
            force=force
        )
        return "success"

    async def common_create(self, args, db_model_cls=None):
        """basic create for orm"""
        db_model_cls = db_model_cls if db_model_cls is not None else self.DB_MODEL_CLS
        return await SingleResource(
            db_model_cls, args, self.MODEL_EXISTED_ERROR, self.MODEL_NOT_EXISTED_ERROR
        ).create()

    async def common_get(self, args, db_model_cls=None, model_existed_error=None, model_not_existed_error=None):
        """basic query one for orm"""
        db_model_cls = db_model_cls if db_model_cls is not None else self.DB_MODEL_CLS
        return await SingleResource(
            db_model_cls,
            args,
            model_existed_error or self.MODEL_EXISTED_ERROR,
            model_not_existed_error or self.MODEL_NOT_EXISTED_ERROR,
        ).get()

    def build_join_condition(self, query, db_model_cls, related_db_model_clses, join_configs):
        for related_db_model_cls, join_config in zip(related_db_model_clses, join_configs):
            query = query.join(
                related_db_model_cls,
                getattr(related_db_model_cls, join_config["related_model_cls_join_key"])
                == getattr(db_model_cls, join_config["db_model_cls_join_key"]),  # noqa
                isouter=True,
            )
        return query

    async def common_list_with_join(
        self, args, db_model_cls=None, related_db_model_clses=None, join_configs=None, extra_conditions=None
    ):
        if related_db_model_clses is None:
            raise ArgsError("lack of related_db_model_clses")
        if join_configs is None:
            raise ArgsError("lack of join_config")
        if len(join_configs) != len(related_db_model_clses):
            raise ArgsError("size of join_configs is not equal to size of related_db_model_clses")
        ret = {
            "total_num": 0,
            "page": args["page"],
            "size": args["size"],
            "num": 0,
            "total_page": 0,
            "data": [],
        }
        db_model_cls = db_model_cls if db_model_cls is not None else self.DB_MODEL_CLS
        query = select(db_model_cls, *related_db_model_clses)
        filter_conditions = self.build_query_condition(
            args, db_model_cls, self.START_TIME_FIELD, self.END_TIME_FIELD, self.FUZZY_FIELD_LIST
        )
        filter_conditions.extend(extra_conditions or [])

        query = self.build_join_condition(query, db_model_cls, related_db_model_clses, join_configs)
        async with get_async_session() as async_session:
            query = query.filter(*filter_conditions)
            total_num = await async_session.scalar(select(func.count()).select_from(query))
            if args.get("order_by") and args.get("order_type"):
                query = query.order_by(getattr(getattr(db_model_cls, args["order_by"]), args["order_type"])())
            if args.get("size") is not None:
                query = query.limit(args["size"])
                if args.get("page") is not None:
                    query = query.offset(args["size"] * (args["page"] - 1))
            query_result = await async_session.execute(query)

            data = []
            for db_model, *related_db_models in query_result.all():
                single_ret = db_model.dict
                for related_db_model_cls, related_db_model in zip(related_db_model_clses, related_db_models):
                    if related_db_model is not None:
                        single_ret[related_db_model_cls.__tablename__] = related_db_model.dict
                    else:
                        single_ret[related_db_model_cls.__tablename__] = {}
                data.append(single_ret)

        ret["total_num"] = total_num
        ret["data"] = data
        ret["num"] = len(data)
        ret["total_page"] = int(math.ceil(total_num / ret["size"]))
        return ret
