import json
import re
import secrets
import socket
import time
import unittest
import urllib.error
import urllib.request
from itertools import count


BASE_URL = "https://qa-internship.avito.com"
UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_NAME_COUNTER = count(1)


class ApiResponse:
    def __init__(self, status_code, headers, text):
        self.status_code = status_code
        self.headers = headers
        self.text = text
        try:
            self.json = json.loads(text) if text else None
        except json.JSONDecodeError:
            self.json = None


class AvitoApiTestCase(unittest.TestCase):
    maxDiff = None

    def request(self, method, path, payload=None):
        last_exception = None
        for attempt in range(3):
            data = None
            headers = {"Accept": "application/json"}
            if payload is not None:
                data = json.dumps(payload).encode("utf-8")
                headers["Content-Type"] = "application/json"

            req = urllib.request.Request(
                url=f"{BASE_URL}{path}",
                data=data,
                headers=headers,
                method=method,
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    return ApiResponse(
                        response.status,
                        dict(response.headers.items()),
                        response.read().decode("utf-8"),
                    )
            except urllib.error.HTTPError as exc:
                return ApiResponse(
                    exc.code,
                    dict(exc.headers.items()),
                    exc.read().decode("utf-8"),
                )
            except (TimeoutError, socket.timeout, urllib.error.URLError, OSError) as exc:
                last_exception = exc
                if attempt < 2:
                    time.sleep(1)
                    continue
                raise last_exception

    def unique_seller_id(self):
        return 111111 + secrets.randbelow(888889)

    def unique_name(self, prefix="qa-api"):
        return f"{prefix}-{int(time.time() * 1000)}-{next(_NAME_COUNTER)}"

    def item_payload(self, **overrides):
        payload = {
            "sellerID": self.unique_seller_id(),
            "name": self.unique_name(),
            "price": 12345,
            "statistics": {
                "likes": 1,
                "viewCount": 2,
                "contacts": 3,
            },
        }
        payload.update(overrides)
        return payload

    def extract_uuid(self, response):
        if isinstance(response.json, dict):
            for key in ("id", "status"):
                value = response.json.get(key)
                if isinstance(value, str):
                    match = UUID_RE.search(value)
                    if match:
                        return match.group(0)

        if isinstance(response.text, str):
            match = UUID_RE.search(response.text)
            if match:
                return match.group(0)
        return None

    def create_item(self, payload=None):
        payload = payload or self.item_payload()
        response = self.request("POST", "/api/1/item", payload)
        item_id = self.extract_uuid(response)
        if item_id:
            self.addCleanup(self.delete_item_safely, item_id)
        return payload, response, item_id

    def delete_item_safely(self, item_id):
        try:
            self.request("DELETE", f"/api/2/item/{item_id}")
        except (TimeoutError, socket.timeout, OSError):
            pass

    def assert_item_shape(self, item, expected_payload):
        self.assertIsInstance(item, dict)
        self.assertIn("id", item)
        self.assertEqual(item["sellerId"], expected_payload["sellerID"])
        self.assertEqual(item["name"], expected_payload["name"])
        self.assertEqual(item["price"], expected_payload["price"])
        self.assertEqual(item["statistics"], expected_payload["statistics"])
        self.assertRegex(item["id"], UUID_RE)
        self.assertTrue(item["createdAt"])

    def assert_error_status(self, response, expected_code):
        self.assertEqual(response.status_code, expected_code, response.text)
        self.assertIsInstance(response.json, dict, response.text)
        self.assertEqual(response.json.get("status"), str(expected_code), response.text)

    def test_create_and_get_item_by_id(self):
        payload, create_response, item_id = self.create_item()

        self.assertEqual(create_response.status_code, 200, create_response.text)
        self.assertIsNotNone(item_id, create_response.text)

        get_response = self.request("GET", f"/api/1/item/{item_id}")

        self.assertEqual(get_response.status_code, 200, get_response.text)
        self.assertIsInstance(get_response.json, list, get_response.text)
        self.assertEqual(len(get_response.json), 1, get_response.text)
        self.assert_item_shape(get_response.json[0], payload)

    def test_get_items_by_seller_returns_created_item(self):
        payload, create_response, item_id = self.create_item()

        self.assertEqual(create_response.status_code, 200, create_response.text)
        self.assertIsNotNone(item_id, create_response.text)

        seller_response = self.request("GET", f"/api/1/{payload['sellerID']}/item")

        self.assertEqual(seller_response.status_code, 200, seller_response.text)
        self.assertIsInstance(seller_response.json, list, seller_response.text)
        self.assertGreaterEqual(len(seller_response.json), 1, seller_response.text)
        ids = {item["id"] for item in seller_response.json}
        self.assertIn(item_id, ids, seller_response.text)
        for item in seller_response.json:
            self.assertEqual(item["sellerId"], payload["sellerID"])

    def test_get_statistics_by_item_id(self):
        payload, create_response, item_id = self.create_item()

        self.assertEqual(create_response.status_code, 200, create_response.text)
        self.assertIsNotNone(item_id, create_response.text)

        statistics_response = self.request("GET", f"/api/1/statistic/{item_id}")

        self.assertEqual(statistics_response.status_code, 200, statistics_response.text)
        self.assertEqual(statistics_response.json, [payload["statistics"]], statistics_response.text)

    def test_get_item_with_invalid_uuid_returns_400(self):
        response = self.request("GET", "/api/1/item/not-a-uuid")
        self.assert_error_status(response, 400)
        self.assertIn("UUID", response.text)

    def test_get_nonexistent_item_returns_404(self):
        response = self.request("GET", "/api/1/item/00000000-0000-4000-8000-000000000001")
        self.assert_error_status(response, 404)
        self.assertIn("not found", response.text)

    def test_create_without_name_returns_400(self):
        payload = self.item_payload()
        payload.pop("name")

        response = self.request("POST", "/api/1/item", payload)

        self.assert_error_status(response, 400)
        self.assertIn("name", response.text)

    def test_repeated_get_item_is_stable(self):
        payload, create_response, item_id = self.create_item()

        self.assertEqual(create_response.status_code, 200, create_response.text)
        self.assertIsNotNone(item_id, create_response.text)

        first_response = self.request("GET", f"/api/1/item/{item_id}")
        second_response = self.request("GET", f"/api/1/item/{item_id}")

        self.assertEqual(first_response.status_code, 200, first_response.text)
        self.assertEqual(second_response.status_code, 200, second_response.text)
        self.assertEqual(first_response.json, second_response.json)
        self.assert_item_shape(first_response.json[0], payload)

    def test_delete_removes_item_from_read_api(self):
        _, create_response, item_id = self.create_item()

        self.assertEqual(create_response.status_code, 200, create_response.text)
        self.assertIsNotNone(item_id, create_response.text)

        delete_response = self.request("DELETE", f"/api/2/item/{item_id}")
        read_after_delete = self.request("GET", f"/api/1/item/{item_id}")

        self.assertEqual(delete_response.status_code, 200, delete_response.text)
        self.assert_error_status(read_after_delete, 404)

    def test_create_response_matches_documented_contract(self):
        payload, response, item_id = self.create_item()

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNotNone(item_id, response.text)
        self.assertIsInstance(response.json, dict, response.text)
        self.assertIn("id", response.json, response.text)
        self.assertIn("sellerId", response.json, response.text)
        self.assertIn("statistics", response.json, response.text)
        self.assertEqual(response.json["sellerId"], payload["sellerID"])
        self.assertEqual(response.json["name"], payload["name"])
        self.assertEqual(response.json["price"], payload["price"])
        self.assertEqual(response.json["statistics"], payload["statistics"])
        self.assertRegex(response.json["id"], UUID_RE)
        self.assertTrue(response.json["createdAt"])

    def test_create_rejects_negative_price(self):
        payload = self.item_payload(
            name=self.unique_name("negative-price"),
            price=-1,
        )

        response = self.request("POST", "/api/1/item", payload)
        created_id = self.extract_uuid(response)
        if created_id:
            self.addCleanup(self.delete_item_safely, created_id)

        self.assert_error_status(response, 400)
        self.assertIn("price", response.text.lower())

    def test_create_rejects_negative_statistics(self):
        payload = self.item_payload(
            name=self.unique_name("negative-likes"),
            statistics={
                "likes": -1,
                "viewCount": 2,
                "contacts": 3,
            },
        )

        response = self.request("POST", "/api/1/item", payload)
        created_id = self.extract_uuid(response)
        if created_id:
            self.addCleanup(self.delete_item_safely, created_id)

        self.assert_error_status(response, 400)
        self.assertIn("likes", response.text.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
