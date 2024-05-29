import datetime

from sqlalchemy import (
    Column,
    Float,
    Integer,
    String,
)
from sqlalchemy.orm import declared_attr

from enova.common.constant import DeployStatus, TestStatus
from enova.common.utils import gen_ulid
from enova.database.relation.orm.base import DBModelBase, table_args, JSON, DateTime


class DeploymentInstanceInfoTable(DBModelBase):
    __tablename__ = "deployment_instance_info"

    @declared_attr
    def __table_args__(cls):
        return table_args(cls, {"comment": "table of enode's deployment instance"})

    instance_id = Column(String(256), primary_key=True, nullable=False, comment="instance id", default=gen_ulid)
    instance_name = Column(String(64), nullable=False, comment="instance name")
    instance_spec = Column(JSON, comment="instance specification")
    startup_args = Column(JSON, comment="the arguments of starting up of model serve by enode")
    mdl_cfg = Column(JSON, comment="the config of llm model")
    enode_id = Column(
        String(256), nullable=False, comment="enode's unique id, allow use it get the status by polit api"
    )
    deploy_status = Column(
        String(32), nullable=False, default=DeployStatus.UNKNOWN.value, comment="status of deployment"
    )
    extra = Column(JSON)
    create_time = Column(DateTime, default=datetime.datetime.now)
    update_time = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    is_deleted = Column(Integer, default=0)
    creator = Column(String(64))
    updater = Column(String(64))


class TestInfoTable(DBModelBase):
    __tablename__ = "test_info"

    @declared_attr
    def __table_args__(cls):
        return table_args(cls, {"comment": "Inject Test record"})

    test_id = Column(String(256), primary_key=True, nullable=False, comment="test ID", default=gen_ulid)
    instance_id = Column(String(256), nullable=False, comment="instance_id in enode's deployment")
    data_set = Column(String(64), nullable=False, comment="name of dataset")
    param_spec = Column(JSON, comment="enode's startup parameters")
    test_spec = Column(JSON, comment="test specification")
    test_status = Column(String(32), nullable=False, default=TestStatus.UNKNOWN.value)
    prompt_tps = Column(Float, default=0, comment="throughput of prompt tokens")
    generation_tps = Column(Float, default=0, comment="throughput of generation tokens")
    result = Column(JSON, comment="result of inject test")
    create_time = Column(DateTime, default=datetime.datetime.now)
    update_time = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    is_deleted = Column(Integer, default=0)
    creator = Column(String(64))
    updater = Column(String(64))
