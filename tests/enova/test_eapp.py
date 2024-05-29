import pytest
from httpx import AsyncClient
from enova.app.server import get_app_api_server
from enova.common.config import CONFIG


@pytest.fixture
def eapp():
    api_server = get_app_api_server()
    return api_server.app


@pytest.mark.asyncio
class TestEnovaApp:
    async def test_healthz(self, eapp):
        async with AsyncClient(app=eapp, base_url="http://test") as ac:
            response = await ac.get(f"/{CONFIG.enova_app['url_prefix']}/healthz")
            assert response.status_code == 200

    async def test_list_enode(self, eapp):
        async with AsyncClient(app=eapp, base_url="http://test") as ac:
            response = await ac.get(f"/{CONFIG.enova_app['url_prefix']}/v1/enode")
            assert response.status_code == 200
