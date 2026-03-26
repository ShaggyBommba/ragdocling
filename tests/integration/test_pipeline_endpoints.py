"""Integration tests for pipeline endpoints against live infrastructure."""

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


def _create_collection_with_pipeline(client: TestClient) -> tuple[str, str]:
    workspace = _create_workspace(client, f"workspace-{uuid4().hex[:12]}")
    collection = _create_collection(
        client,
        workspace_id=workspace["id"],
        name=f"collection-{uuid4().hex[:12]}",
    )
    collection_id = collection["id"]

    response = client.get(f"/api/v1/collection/{collection_id}/pipelines")
    assert response.status_code == 200
    pipelines = response.json()
    assert isinstance(pipelines, list)
    assert len(pipelines) >= 1

    pipeline_id = pipelines[0]["id"]
    return collection_id, pipeline_id


class TestPipelineEndpoints:
    """Endpoint coverage for pipeline routes under a collection."""

    def test_list_collection_pipelines_endpoint(self, client: TestClient) -> None:
        collection_id, _ = _create_collection_with_pipeline(client)

        response = client.get(f"/api/v1/collection/{collection_id}/pipelines")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_collection_pipeline_endpoint(self, client: TestClient) -> None:
        collection_id, pipeline_id = _create_collection_with_pipeline(client)

        response = client.get(f"/api/v1/collection/{collection_id}/pipelines/{pipeline_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pipeline_id

    def test_promote_pipeline_endpoint(self, client: TestClient) -> None:
        collection_id, pipeline_id = _create_collection_with_pipeline(client)

        response = client.post(
            f"/api/v1/collection/{collection_id}/pipelines/{pipeline_id}/promote"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pipeline_id

    def test_demote_pipeline_endpoint(self, client: TestClient) -> None:
        collection_id, pipeline_id = _create_collection_with_pipeline(client)

        response = client.post(f"/api/v1/collection/{collection_id}/pipelines/{pipeline_id}/demote")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pipeline_id

    def test_get_production_pipeline_endpoint(self, client: TestClient) -> None:
        collection_id, _ = _create_collection_with_pipeline(client)

        response = client.get(f"/api/v1/collection/{collection_id}/pipelines/production")

        assert response.status_code == 400
        assert "valid UUID hex string" in response.json()["detail"]

    def test_get_staging_pipeline_endpoint(self, client: TestClient) -> None:
        collection_id, _ = _create_collection_with_pipeline(client)

        response = client.get(f"/api/v1/collection/{collection_id}/pipelines/staging")

        assert response.status_code == 400
        assert "valid UUID hex string" in response.json()["detail"]

    def test_get_archived_pipeline_endpoint_not_found(self, client: TestClient) -> None:
        collection_id, _ = _create_collection_with_pipeline(client)

        response = client.get(f"/api/v1/collection/{collection_id}/pipelines/archived")

        assert response.status_code == 400
        assert "valid UUID hex string" in response.json()["detail"]
