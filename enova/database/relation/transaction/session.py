import dataclasses
from typing import Dict, Type
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session as SqlAlchemySession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession as SqlAlchemyAsyncSession
from enova.common.config import CONFIG
from enova.common.local import get_local_param, set_local_param


DB_ENGINES = {}


class DBEngine:
    def __init__(self, db_config):
        self.db_config = db_config
        self._protocol = None
        self._aio_protocol = None
        self._engine = None
        self._async_engine = None

    def __getattr__(self, item):
        return self.db_config[item]

    @property
    def engine(self):
        if self._engine is None:
            echo_flag = self.db_config.get("echo", False)
            if self.db_config.get("is_file_based"):
                self._engine = create_engine(
                    self.protocol,
                    echo=echo_flag,
                )
            else:
                self._engine = create_engine(
                    self.protocol,
                    pool_recycle=self.db_config.get("pool_recycle", 3600),
                    pool_size=self.db_config.get("pool_size", 30),
                    echo=echo_flag,
                )

        return self._engine

    @property
    def async_engine(self):
        """
        https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
        one thread can only have one async_engine
        """
        cache_key = f"async_engine-{self.aio_protocol}"
        self._async_engine = get_local_param(cache_key)
        if self._async_engine is None:
            echo_flag = self.db_config.get("echo", False)
            if self.db_config.get("is_file_based"):
                self._async_engine = create_async_engine(
                    self.aio_protocol,
                    echo=echo_flag,
                )
            else:
                self._async_engine = create_async_engine(
                    self.aio_protocol,
                    pool_recycle=self.db_config.get("pool_recycle", 3600),
                    pool_size=self.db_config.get("pool_size", 30),
                    echo=echo_flag,
                )
            set_local_param(cache_key, self._async_engine)

        return self._async_engine


class MysqlEngine(DBEngine):
    @property
    def protocol(self):
        if self._protocol is None:
            self._protocol = "mysql+pymysql://{user}:{passwd}@{host}:{port}".format(
                user=self.username,
                passwd=self.password,
                host=self.host,
                port=self.port,
            )
            if self.db_config.get("database"):
                self._protocol = f"{self._protocol}/{self.database}?charset=utf8mb4"
            else:
                self._protocol = f"{self._protocol}/?charset=utf8mb4"
        return self._protocol

    @property
    def aio_protocol(self):
        if self._aio_protocol is None:
            self._aio_protocol = "mysql+aiomysql://{user}:{passwd}@{host}:{port}".format(
                user=self.username,
                passwd=self.password,
                host=self.host,
                port=self.port,
            )
            if self.db_config.get("database"):
                self._aio_protocol = f"{self._aio_protocol}/{self.database}?charset=utf8mb4"
            else:
                self._aio_protocol = f"{self._aio_protocol}/?charset=utf8mb4"
        return self._aio_protocol


class PostgresqlEngine(DBEngine):
    @property
    def protocol(self):
        if self._protocol is None:
            self._protocol = "postgresql+psycopg2://{user}:{passwd}@{host}:{port}".format(
                user=self.username,
                passwd=self.password,
                host=self.host,
                port=self.port,
            )
            if self.db_config.get("database"):
                self._protocol = f"{self._protocol}/{self.database}"
            else:
                self._protocol = f"{self._protocol}/"
        return self._protocol

    @property
    def aio_protocol(self):
        if self._aio_protocol is None:
            self._aio_protocol = "postgresql+asyncpg://{user}:{passwd}@{host}:{port}".format(
                user=self.username,
                passwd=self.password,
                host=self.host,
                port=self.port,
            )
            if self.db_config.get("database"):
                self._aio_protocol = f"{self._aio_protocol}/{self.database}"
            else:
                self._aio_protocol = f"{self._aio_protocol}/"
        return self._aio_protocol


class SqliteEngine(DBEngine):
    @property
    def protocol(self):
        if self._protocol is None:
            self._protocol = "sqlite://"
            data_dir = self.db_config.get("data_dir", "/tmp")
            # TODO: make sure data_dir as absolute path

            if self.db_config.get("database"):
                self._protocol = f"{self._protocol}/{data_dir}/{self.database}.db"
            else:
                self.db_config.update({"database": "mydatabase"})
                self._protocol = f"{self._protocol}/mydatabase.db"
        return self._protocol

    @property
    def aio_protocol(self):
        if self._aio_protocol is None:
            self._aio_protocol = "sqlite+aiosqlite://"
            data_dir = self.db_config.get("data_dir", "/tmp")
            if self.db_config.get("database"):
                self._aio_protocol = f"{self._aio_protocol}/{data_dir}/{self.database}.db"
            else:
                self._aio_protocol = f"{self._aio_protocol}/mydatabase.db"
        return self._aio_protocol


class DBRouter:
    """
    route to the db corresponding of db_name in
    """

    def db_engine(self, instance_name="default") -> Type[DBEngine]:
        """ """
        databases = CONFIG.api["databases"]
        if instance_name not in DB_ENGINES:
            db_type = databases[instance_name].get("db_type")
            if db_type and str.lower(db_type) == "postgresql":
                DB_ENGINES.update({instance_name: PostgresqlEngine(databases[instance_name])})
            elif db_type and str.lower(db_type) == "mysql":
                DB_ENGINES.update({instance_name: MysqlEngine(databases[instance_name])})
            else:
                db_config = databases[instance_name]
                db_config.update({"is_file_based": True})
                DB_ENGINES.update({instance_name: SqliteEngine(db_config)})

        return DB_ENGINES[instance_name]

    def has_engine(self, instance_name):
        return instance_name in DB_ENGINES

    def set_custom_db_engine(self, instance_name, db_engine):
        DB_ENGINES.update({instance_name: db_engine})

    def set_custom_db_engine_by_config(self, instance_name, db_config: Dict):
        mysql_db_engine = MysqlEngine(db_config)
        DB_ENGINES.update({instance_name: mysql_db_engine})

    def has_db_engine(self, instance_name):
        return instance_name in DB_ENGINES


db_router = DBRouter()


@dataclasses.dataclass
class BaseSession:
    db_name: str

    def __post_init__(self):
        self.session = self.get_session()

    def get_session(self):
        """"""
        print(self.db_name)

    @property
    def db_engine(self):
        return db_router.db_engine(self.db_name)

    def __getattr__(self, name):
        return getattr(self.session, name)


@dataclasses.dataclass
class DBSession(BaseSession):
    def get_session(self):
        """"""
        return sessionmaker(bind=self.db_engine.engine, class_=SqlAlchemySession)()

    def __enter__(self):
        """"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        try:
            if exc_type is None:
                self.session.commit()
                self.session.flush()
        except Exception as e:
            self.session.rollback()
            raise e
        finally:
            self.session.close()


@dataclasses.dataclass
class ASyncSession(BaseSession):
    def get_session(self):
        """"""
        return async_sessionmaker(bind=self.db_engine.async_engine, class_=SqlAlchemyAsyncSession)()

    async def __aenter__(self):
        self.session.begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        try:
            if exc_type is None:
                await self.session.commit()
                await self.session.flush()
        except Exception as e:
            await self.session.rollback()
            raise e
        finally:
            await self.session.close()


def get_session(db_name="default"):
    return DBSession(db_name)


def get_async_session(db_name="default"):
    return ASyncSession(db_name)
