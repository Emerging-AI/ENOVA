import datetime
import json
from typing import Any
from sqlalchemy import Column, String, Integer
from sqlalchemy import DateTime
from sqlalchemy import TypeDecorator, types
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.orm.decl_api import declarative_base
from enova.common.encoder import NumpyEncoder


EMERGINAI_DB_MODEL_LIST = []


def table_args(cls: type, __table_args__: dict[str, Any] | tuple[Any, ...]) -> dict[str, Any] | tuple[Any, ...]:
    """
    Helper class function to merge the __table_args__ attr of a
    SQLAlchemy model that has some inheritance. Use it like this:

    from sqlalchemy.ext.declarative import declared_attr

    class MyModel(MixinOne, MixinTwo, MixinThree, Base):
        __tablename__ = "my_table"

        @declared_attr
        def __table_args__(cls):
            return table_args(cls, {"schema": "my_database"})
    """
    args: dict[Any, None] = {}  # Store args in keys of dictionary for fast lookup and no duplicates
    kwargs: dict[str, Any] = {}
    table_args_attrs = []

    # Collect immediate parent "__table_args__" in reverse order
    for class_ in reversed(cls.__bases__):
        table_args_attr = getattr(class_, "__table_args__", None)
        if table_args_attr:
            table_args_attrs.append(table_args_attr)

    # Also merge the current table args
    table_args_attrs.append(__table_args__)

    for table_args_attr in table_args_attrs:
        # Handle simple dictionary use case first
        if isinstance(table_args_attr, dict):
            kwargs.update(table_args_attr)
            continue

        if isinstance(table_args_attr, tuple):
            if not table_args_attr:
                raise ValueError("Empty table arguments found")

            # Add all but last positional argument, if it is not already added
            for positional_arg in table_args_attr[:-1]:
                if positional_arg not in args:
                    args[positional_arg] = None

            last_positional_arg = table_args_attr[-1]
            if isinstance(last_positional_arg, dict):
                kwargs.update(last_positional_arg)
            elif last_positional_arg not in args:
                args[last_positional_arg] = None

    # Either return a tuple or a dictionary depending on what was found
    if args:
        if kwargs:
            return (*args, kwargs)
        else:
            return tuple(args)
    else:
        return kwargs


class NewDeclarativeMeta(DeclarativeMeta):
    def __init__(cls, classname, bases, dict_):
        super().__init__(classname, bases, dict_)

        if hasattr(cls, "__table__"):
            cls.column_dict = {column.name: column for column in cls.__table__.columns}
        else:
            cls.column_dict = {
                name: value for name, value in vars(cls).items() if isinstance(value, InstrumentedAttribute)
            }
        cls.column_names = set(cls.column_dict.keys())
        cls.json_names = {name for name, value in cls.column_dict.items() if isinstance(value.type, JSON)}
        cls.datetime_names = {name for name, value in cls.column_dict.items() if isinstance(value.type, DateTime)}
        cls.primary_column_names = {
            name for name, value in vars(cls).items() if isinstance(value, InstrumentedAttribute) and value.primary_key
        }
        EMERGINAI_DB_MODEL_LIST.append(cls)


EMERGINAI_DB_MODEL_LIST = []


class JSON(TypeDecorator):
    """
    generally, sqlite3 not support json column type,
    this clz helps tabel model that can serilize json obj like mysql
    """

    @property
    def python_type(self):
        return object

    impl = types.String

    def process_bind_param(self, value, dialect):
        return json.dumps(value, cls=NumpyEncoder)

    def process_literal_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return None


class DateTime(TypeDecorator):
    """
    sqlite3 does not support string format datetime
    """

    @property
    def python_type(self):
        return datetime.datetime

    impl = types.String

    def process_bind_param(self, value, dialect):
        if isinstance(value, str):
            return datetime.datetime.fromisoformat(value)
        return value

    def process_literal_param(self, value, dialect):
        return value

    def process_result_value(self, value, dialect):
        return value


BaseSqlite = declarative_base(metaclass=NewDeclarativeMeta)


class DBModelBase(BaseSqlite):
    """
    table's model class for sqlite3
    """

    __tablename__ = NotImplemented
    __abstract__ = True

    @property
    def dict(self):
        ret = {column.name: getattr(self, column.name) for column in self.__table__.columns}
        for name in self.datetime_names:
            value = ret[name]
            if value and isinstance(value, (datetime.date, datetime.datetime)):
                ret[name] = value.strftime("%Y-%m-%d %H:%M:%S")
        return ret


class EmergingAIDBModelBase(DBModelBase):
    __tablename__ = NotImplemented
    __abstract__ = True
    __admin_view__ = True
    __table_args__ = {
        "mysql_engine": "InnoDB",
        "mysql_default_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_unicode_ci",
    }

    create_time = Column(DateTime, default=datetime.datetime.now)
    update_time = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    is_deleted = Column(Integer, default=0)
    creator = Column(String(64))
    updater = Column(String(64))

    def __init__(self, **kwargs) -> None:
        kwargs = {k: v for k, v in kwargs.items() if k in self.column_dict}
        super().__init__(**kwargs)


def enum_values(enum):
    return [e.value for e in enum]


def validate_json_schema(cls, v):
    if isinstance(v, str):
        return json.loads(v)
    return v


class EmergingAIDBModelBaseWithExtra(EmergingAIDBModelBase):
    __tablename__ = NotImplemented
    __abstract__ = True

    extra = Column(JSON)

    class AddOnSchemaModel:
        __validators__ = {
            "extra": {"validate_json_schema": validate_json_schema},
        }
