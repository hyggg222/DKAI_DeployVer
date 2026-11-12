import unittest
try:
    import httpx
except ImportError:
    httpx = None

from ai_server import fastapi_app

class TestServerEndpoints(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        if httpx is None:
            self.skipTest("httpx is not installed in the current environment")
        transport = httpx.ASGITransport(app=fastapi_app)
        self.client = httpx.AsyncClient(transport=transport, base_url="http://testserver")

    async def asyncTearDown(self):
        if httpx is not None:
            await self.client.aclose()

    async def test_root_endpoint_returns_html(self):
        response = await self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("DKAI Vehicle Access Control Console", response.text)

    async def test_api_history_returns_json(self):
        response = await self.client.get("/api/history")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

if __name__ == "__main__":
    unittest.main()
