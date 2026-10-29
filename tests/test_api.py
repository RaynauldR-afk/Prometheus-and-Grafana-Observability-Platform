from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_returns_service_metadata():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "observability-demo-api"


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_readiness_endpoint():
    response = client.get("/ready")
    assert response.status_code == 200


def test_orders_endpoint_returns_items():
    response = client.get("/api/v1/orders")
    assert response.status_code == 200
    assert response.json()["count"] == 3


def test_checkout_success():
    response = client.post("/api/v1/checkout", json={"customer_id": "demo-1"})
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_checkout_failure_can_be_observed():
    response = client.post("/api/v1/checkout", json={"simulate_failure": True})
    assert response.status_code == 503


def test_metrics_endpoint_exposes_prometheus_format():
    # Generate at least one instrumented request before checking the metrics output.
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text
    assert "system_memory_percent" in response.text
