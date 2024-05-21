from http.client import HTTPException
from pathlib import Path

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import sqlalchemy as sa

from enova.common.config import CONFIG
from enova.common.logger import LOGGER
from enova.common.constant import ApiServerType
from enova.common.utils import get_web_static_path
from enova.database.relation.orm.base import BaseSqlite
from enova.database.relation.transaction.session import get_session
from enova.server.server import ApiServer


WEB_STATIC_PATH = get_web_static_path()


async def redirect_all_requests_to_frontend(request: Request, exc: HTTPException):
    # TODO: need to modify
    if WEB_STATIC_PATH:
        return HTMLResponse(open(Path(WEB_STATIC_PATH) / "index.html").read())
    return "Welcome to enova"


def init_db():
    with get_session() as session:
        # TODO: allow migrate new tables
        insp = sa.inspect(session.db_engine.engine)
        if not insp.get_table_names():
            BaseSqlite.metadata.create_all(bind=session.db_engine.engine)
            session.commit()

        insp = sa.inspect(session.db_engine.engine)
        LOGGER.info(insp.get_table_names())


def get_app_api_server(api_server_type=ApiServerType.ENOVA_APP.value):
    api_config = getattr(CONFIG, api_server_type)

    CONFIG.api.update(api_config)

    api_server = ApiServer(api_config)

    # mount vuejs dist
    api_server.app.mount(
        f"{CONFIG.api['url_prefix']}/",
        StaticFiles(directory=WEB_STATIC_PATH, html=True),
        name="static",
    )
    api_server.app.add_exception_handler(404, redirect_all_requests_to_frontend)

    # datebase init
    init_db()

    return api_server
