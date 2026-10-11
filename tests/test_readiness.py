import json
import unittest
from unittest.mock import AsyncMock

from sqlalchemy.exc import OperationalError
from starlette.requests import Request

from app.main import app, readiness


def request() -> Request:
    return Request({"type": "http", "headers": []})


class ReadinessTests(unittest.IsolatedAsyncioTestCase):
    def test_readiness_route_is_documented(self):
        self.assertIn("/ready", app.openapi()["paths"])

    async def test_readiness_succeeds_when_database_responds(self):
        db = AsyncMock()
        response = await readiness(request(), db)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(bytes(response.body))["data"], {"status": "ready"})
        db.execute.assert_awaited_once()

    async def test_readiness_returns_503_when_database_fails(self):
        db = AsyncMock()
        db.execute.side_effect = OperationalError("SELECT 1", {}, Exception("down"))
        response = await readiness(request(), db)
        body = json.loads(bytes(response.body))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(body["code"], "AUTH-503-001")
        self.assertEqual(body["error"]["requiredAction"], "RETRY_LATER")


if __name__ == "__main__":
    unittest.main()
