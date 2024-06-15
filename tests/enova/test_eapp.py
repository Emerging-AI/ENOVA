import pytest
from httpx import AsyncClient
from enova.app.server import get_app_api_server
from enova.common.config import CONFIG


@pytest.fixture
def eapp():
    api_server = get_app_api_server()
    return api_server.app


@pytest.mark.asyncio
class TestEApp:
    async def test_healthz(self, eapp):
        async with AsyncClient(app=eapp, base_url="http://test") as ac:
            response = await ac.get(f"/{CONFIG.enova_app['url_prefix']}/healthz")
            assert response.status_code == 200


@pytest.mark.asyncio
class TestEServe:
    async def test_list_enode(self, eapp):
        async with AsyncClient(app=eapp, base_url="http://test") as ac:
            response = await ac.get(f"/{CONFIG.enova_app['url_prefix']}/v1/enode")
            assert response.status_code == 200
            # TODO: some test of biz flow

    # async def test_create_enode_with_escalar(self, eapp):
    #     post_params = {}
    #     async with AsyncClient(app=eapp, base_url="http://test") as ac:
    #         response = await ac.post(
    #             f"/{CONFIG.enova_app['url_prefix']}/v1/enode",
    #             json=post_params,
    #         )
    #         assert response.status_code == 200
    #         # TODO: some test of biz flow

    # async def test_create_enode_missing_escalar(self, eapp):
    #     post_params = {}
    #     async with AsyncClient(app=eapp, base_url="http://test") as ac:
    #         response = await ac.post(
    #             f"/{CONFIG.enova_app['url_prefix']}/v1/enode",
    #             json=post_params,
    #         )
    #         assert response.status_code == 200
    #         # TODO: some test of biz flow

    # async def test_get_enode(self, eapp):
    #     eserve_id = ""
    #     async with AsyncClient(app=eapp, base_url="http://test") as ac:
    #         response = await ac.get(f"/{CONFIG.enova_app['url_prefix']}/v1/enode/{eserve_id}")
    #         assert response.status_code == 200
    #         # TODO: some test of biz flow

    # async def test_delete_enode(self, eapp):
    #     eserve_id = ""
    #     async with AsyncClient(app=eapp, base_url="http://test") as ac:
    #         response = await ac.delete(f"/{CONFIG.enova_app['url_prefix']}/v1/enode/{eserve_id}")
    #         assert response.status_code == 200
    #         # TODO: some test of biz flow


@pytest.mark.asyncio
class TestTInject:
    async def test_list_injector(self, eapp):
        async with AsyncClient(app=eapp, base_url="http://test") as ac:
            response = await ac.get(f"/{CONFIG.enova_app['url_prefix']}/v1/instance/test")
            assert response.status_code == 200
            # TODO: some test of biz flow
