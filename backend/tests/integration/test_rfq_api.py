import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_rfq_api_success(async_client: AsyncClient):
    payload = {
        "title": "Precision Sensors RFQ",
        "description": "Pressure and temperature sensors for skid 4",
        "category": "Instrumentation",
        "reference_currency": "USD",
        "line_items": [
            {
                "position": 1,
                "description": "Pressure Transmitter 0-100 bar",
                "quantity": 10,
                "unit": "units",
            },
            {
                "position": 2,
                "description": "RTD PT100 Temperature Probe",
                "quantity": 15,
                "unit": "units",
            },
        ],
        "criteria": [
            {"name": "Price", "weight": 0.50, "direction": "lower_is_better", "data_type": "price"},
            {
                "name": "Delivery Time",
                "weight": 0.30,
                "direction": "lower_is_better",
                "data_type": "days",
            },
            {
                "name": "Warranty",
                "weight": 0.20,
                "direction": "higher_is_better",
                "data_type": "days",
            },
        ],
    }

    response = await async_client.post(
        "/api/v1/rfqs",
        json=payload,
        headers={"X-API-Key": "test-key"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Precision Sensors RFQ"
    assert data["status"] == "draft"
    assert data["is_archived"] is False
    assert len(data["line_items"]) == 2
    assert len(data["criteria"]) == 3


@pytest.mark.asyncio
async def test_create_rfq_api_invalid_weights_rejected(async_client: AsyncClient):
    # Sum is 0.70 + 0.10 = 0.80 != 1.00
    payload = {
        "title": "Invalid Weights RFQ",
        "criteria": [
            {"name": "Price", "weight": 0.70},
            {"name": "Delivery", "weight": 0.10},
        ],
    }

    response = await async_client.post(
        "/api/v1/rfqs",
        json=payload,
        headers={"X-API-Key": "test-key"},
    )
    # Schema validation or service validation rejects with 422
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rfq_crud_lifecycle_api(async_client: AsyncClient):
    # 1. Create
    create_res = await async_client.post(
        "/api/v1/rfqs",
        json={
            "title": "Lifecycle Test RFQ",
            "category": "Testing",
            "reference_currency": "EUR",
            "line_items": [{"description": "Item 1", "quantity": 5, "unit": "pcs"}],
            "criteria": [{"name": "Price", "weight": 1.0}],
        },
        headers={"X-API-Key": "test-key"},
    )
    assert create_res.status_code == 201
    rfq_id = create_res.json()["id"]

    # 2. Get by ID
    get_res = await async_client.get(f"/api/v1/rfqs/{rfq_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Lifecycle Test RFQ"

    # 3. List
    list_res = await async_client.get("/api/v1/rfqs")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == rfq_id for item in list_data["items"])

    # 4. Update
    patch_res = await async_client.patch(
        f"/api/v1/rfqs/{rfq_id}",
        json={"title": "Updated Lifecycle RFQ", "status": "active"},
        headers={"X-API-Key": "test-key"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated Lifecycle RFQ"
    assert patch_res.json()["status"] == "active"

    # 5. Archive (soft-delete)
    archive_res = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/archive",
        headers={"X-API-Key": "test-key"},
    )
    assert archive_res.status_code == 200
    assert archive_res.json()["is_archived"] is True
    assert archive_res.json()["status"] == "archived"

    # Default list excludes it
    active_list_res = await async_client.get("/api/v1/rfqs")
    assert not any(item["id"] == rfq_id for item in active_list_res.json()["items"])

    # Include archived returns it
    all_list_res = await async_client.get("/api/v1/rfqs?include_archived=true")
    assert any(item["id"] == rfq_id for item in all_list_res.json()["items"])

    # 6. Unarchive
    unarchive_res = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/unarchive",
        headers={"X-API-Key": "test-key"},
    )
    assert unarchive_res.status_code == 200
    assert unarchive_res.json()["is_archived"] is False

    # 7. Clone
    clone_res = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/clone?new_title=Cloned Lifecycle RFQ",
        headers={"X-API-Key": "test-key"},
    )
    assert clone_res.status_code == 201
    cloned_data = clone_res.json()
    assert cloned_data["id"] != rfq_id
    assert cloned_data["title"] == "Cloned Lifecycle RFQ"
    assert len(cloned_data["line_items"]) == 1


@pytest.mark.asyncio
async def test_update_criteria_api(async_client: AsyncClient):
    create_res = await async_client.post(
        "/api/v1/rfqs",
        json={"title": "Criteria Test", "criteria": [{"name": "Old", "weight": 1.0}]},
        headers={"X-API-Key": "test-key"},
    )
    rfq_id = create_res.json()["id"]

    # Update with valid 100% criteria
    update_res = await async_client.put(
        f"/api/v1/rfqs/{rfq_id}/criteria",
        json=[
            {"name": "Commercial Cost", "weight": 0.60},
            {"name": "Technical Compliance", "weight": 0.40},
        ],
        headers={"X-API-Key": "test-key"},
    )
    assert update_res.status_code == 200
    criteria = update_res.json()["criteria"]
    assert len(criteria) == 2
    assert criteria[0]["name"] == "Commercial Cost"
