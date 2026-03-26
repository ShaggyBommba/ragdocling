"""Integration tests for collection CRUD endpoints against live infrastructure."""

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from dacke.app import build


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    app = build()
    with TestClient(app) as test_client:
        yield test_client


def _create_workspace(client: TestClient, name: str) -> dict[Any, Any]:
    response = client.post("/api/v1/workspace", json={"name": name})
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload["name"] == name
    assert isinstance(payload["id"], str)
    return payload


def _create_collection(client: TestClient, workspace_id: str, name: str) -> dict[Any, Any]:
    response = client.post(
        "/api/v1/collection",
        json={"workspace_id": workspace_id, "name": name},
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload["workspace_id"] == workspace_id
    assert payload["name"] == name
    assert isinstance(payload["id"], str)
    return payload


class TestCollectionEndpoints:
    """Endpoint coverage for collection CRUD operations."""

    def test_create_collection_endpoint(self, client: TestClient) -> None:
        workspace_name = f"workspace-{uuid4().hex[:12]}"
        workspace = _create_workspace(client, workspace_name)

        collection_name = f"collection-{uuid4().hex[:12]}"
        response = client.post(
            "/api/v1/collection",
            json={"workspace_id": workspace["id"], "name": collection_name},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workspace_id"] == workspace["id"]
        assert data["name"] == collection_name
        assert data["created_at"]
        assert data["updated_at"]

    def test_list_collections_endpoint(self, client: TestClient) -> None:
        workspace_name = f"workspace-{uuid4().hex[:12]}"
        workspace = _create_workspace(client, workspace_name)

        collection_name = f"collection-{uuid4().hex[:12]}"
        created = _create_collection(client, workspace["id"], collection_name)

        response = client.get("/api/v1/collection")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(item["id"] == created["id"] for item in data)

    def test_get_collection_endpoint(self, client: TestClient) -> None:
        workspace_name = f"workspace-{uuid4().hex[:12]}"
        workspace = _create_workspace(client, workspace_name)

        collection_name = f"collection-{uuid4().hex[:12]}"
        created = _create_collection(client, workspace["id"], collection_name)

        response = client.get(f"/api/v1/collection/{created['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert data["workspace_id"] == workspace["id"]
        assert data["name"] == collection_name

    def test_update_collection_endpoint(self, client: TestClient) -> None:
        workspace_name = f"workspace-{uuid4().hex[:12]}"
        workspace = _create_workspace(client, workspace_name)

        collection_name = f"collection-{uuid4().hex[:12]}"
        created = _create_collection(client, workspace["id"], collection_name)

        new_name = f"collection-renamed-{uuid4().hex[:8]}"
        response = client.put(
            f"/api/v1/collection/{created['id']}",
            json={"name": new_name},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert data["name"] == new_name

    def test_delete_collection_endpoint(self, client: TestClient) -> None:
        workspace_name = f"workspace-{uuid4().hex[:12]}"
        workspace = _create_workspace(client, workspace_name)

        collection_name = f"collection-{uuid4().hex[:12]}"
        created = _create_collection(client, workspace["id"], collection_name)

        response = client.delete(f"/api/v1/collection/{created['id']}")

        assert response.status_code == 204
        assert response.text == ""
