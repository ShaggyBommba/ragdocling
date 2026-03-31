"""Integration tests for workspace CRUD endpoints against live infrastructure."""

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
    response = client.post("/api/v1/workspaces", json={"name": name})
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert payload["name"] == name
    assert isinstance(payload["id"], str)
    return payload


class TestWorkspaceEndpoints:
    """Endpoint coverage for workspace CRUD operations."""

    def test_create_workspace_endpoint(self, client: TestClient) -> None:
        """POST /workspaces/ should create a workspace and return 200."""
        name = f"workspace-{uuid4().hex[:12]}"
        response = client.post("/api/v1/workspaces", json={"name": name})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == name
        assert isinstance(data["id"], str)
        assert data["created_at"]
        assert data["updated_at"]

    def test_list_workspaces_endpoint(self, client: TestClient) -> None:
        """GET /workspaces/ should return all workspaces and return 200."""
        name = f"workspace-{uuid4().hex[:12]}"
        created = _create_workspace(client, name)

        response = client.get("/api/v1/workspaces")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(item["id"] == created["id"] for item in data)

    def test_get_workspace_endpoint(self, client: TestClient) -> None:
        """GET /workspaces/{workspace_id} should return one workspace and return 200."""
        name = f"workspace-{uuid4().hex[:12]}"
        created = _create_workspace(client, name)
        workspace_id = created["id"]

        response = client.get(f"/api/v1/workspaces/{workspace_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == workspace_id
        assert data["name"] == name

    def test_update_workspace_endpoint(self, client: TestClient) -> None:
        """PUT /workspaces/{workspace_id} should update a workspace and return 200."""
        original_name = f"workspace-{uuid4().hex[:12]}"
        created = _create_workspace(client, original_name)
        workspace_id = created["id"]
        new_name = f"workspace-renamed-{uuid4().hex[:8]}"

        response = client.put(
            f"/api/v1/workspaces/{workspace_id}",
            json={"name": new_name},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == workspace_id
        assert data["name"] == new_name

    def test_delete_workspace_endpoint(self, client: TestClient) -> None:
        """DELETE /workspaces/{workspace_id} should delete a workspace and return 204."""
        name = f"workspace-{uuid4().hex[:12]}"
        created = _create_workspace(client, name)
        workspace_id = created["id"]

        response = client.delete(f"/api/v1/workspaces/{workspace_id}")

        assert response.status_code == 204
        assert response.text == ""
