import pytest


@pytest.mark.asyncio
async def test_global_audit_lists_real_events_without_actor_credentials(async_client):
    response = await async_client.post(
        "/api/v1/rfqs",
        json={
            "title": "Audit regression",
            "reference_currency": "USD",
            "line_items": [],
            "criteria": [],
        },
    )
    assert response.status_code == 201
    rfq_id = response.json()["id"]
    response = await async_client.get("/api/v1/audit", params={"rfq_id": rfq_id, "page_size": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) == 1
    assert data["items"][0]["rfq_id"] == rfq_id
    assert "actor_id" not in data["items"][0]
    assert (await async_client.get("/api/v1/audit?page=0")).status_code == 422
    assert (await async_client.get("/api/v1/audit?rfq_id=missing")).json()["items"] == []
