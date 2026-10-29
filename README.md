# Observability Platform: Prometheus + Grafana

A portfolio-ready monitoring stack demonstrating application instrumentation, time-series collection, operational dashboards, alert rules, container health checks, and automated tests.

## Architecture

```text
Client / API traffic
        |
        v
FastAPI service :8000 ---- /metrics
        |                       ^
        |                       |
        +-----------------------+
                                |
                         Prometheus :9090
                                |
                            PromQL queries
                                |
                          Grafana :3000
```

## Features

- FastAPI service with health and readiness endpoints.
- Prometheus counters and histograms for HTTP request volume, status codes, and latency.
- Process/system CPU and memory measurements.
- Grafana dashboard provisioned from version-controlled JSON.
- Prometheus alert rules for target availability, p95 latency, HTTP 5xx rate, and memory pressure.
- Docker Compose deployment with persistent Prometheus and Grafana volumes.
- Automated API and metrics tests.

## Quick start: Docker Compose (recommended)

Prerequisites: Docker Desktop with Docker Compose v2.

1. Copy `.env.example` to `.env` and change the Grafana password.
2. From this directory, run:

   ```powershell
   Copy-Item .env.example .env
   notepad .env
   docker compose up --build -d
   docker compose ps
   ```

3. Open:
   - API docs: http://localhost:8000/docs
   - Metrics: http://localhost:8000/metrics
   - Prometheus targets: http://localhost:9090/targets
   - Prometheus alerts: http://localhost:9090/alerts
   - Grafana: http://localhost:3000

   Grafana credentials are `admin` and the password in `.env`.

The dashboard and Prometheus data source are provisioned automatically. This is a local demonstration stack; do not expose its ports publicly without hardening authentication, TLS, network access, and secrets.

## Run on Windows without Docker

This path uses the Python API plus your native Prometheus and Grafana installations.

### 1. Create a virtual environment and install dependencies

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If Python 3.12 is not installed, use a supported Python version installed on your machine, for example `py -3.14 -m venv .venv`. If a dependency fails to install on your Python version, use Python 3.12 for this project.

### 2. Start the API

In a project terminal:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify `http://localhost:8000/health` and `http://localhost:8000/metrics`.

### 3. Configure native Prometheus

Use `config/prometheus.windows.yml` as the Prometheus configuration. Since the rules file is referenced relative to the configuration directory, run Prometheus with the project `config` directory as the working directory:

```powershell
Set-Location .\config
& "D:\monitoring-tools\prometheus-3.15.1.windows-amd64\prometheus.exe" --config.file="prometheus.windows.yml" --storage.tsdb.path="..\prometheus-data"
```

If Prometheus is installed in a different folder, update the executable path. Keep this terminal open while Prometheus runs.

Open http://localhost:9090/targets and verify both `prometheus` and `observability-api` are **UP**.

### 4. Connect native Grafana to Prometheus

Open Grafana at http://localhost:3000 and sign in using the credentials configured during installation.

1. Add a Prometheus data source.
2. Set the URL to `http://localhost:9090`.
3. Save and test the data source.
4. Import `grafana/dashboards/observability-overview.json` from the Grafana Dashboards page.

For native Grafana, the Docker provisioning file uses the Docker service hostname `prometheus`; use `localhost:9090` in the Grafana UI instead.

## Generate traffic

With the API running, open another PowerShell terminal:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/orders
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/checkout -ContentType "application/json" -Body '{"customer_id":"demo-1"}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/checkout -ContentType "application/json" -Body '{"simulate_failure":true}'
```

The last request intentionally returns HTTP 503. It is useful for validating error-rate instrumentation; it is not a real payment or checkout system.

## Run tests

```powershell
python -m pytest
```

## Useful PromQL queries

Requests per second:

```promql
sum(rate(http_requests_total{job="observability-api"}[5m]))
```

HTTP 5xx rate:

```promql
sum(rate(http_requests_total{job="observability-api",status=~"5.."}[5m]))
```

95th percentile latency:

```promql
histogram_quantile(
  0.95,
  sum by (le) (rate(http_request_duration_seconds_bucket{job="observability-api"}[5m]))
)
```

System memory usage:

```promql
system_memory_percent
```

Target availability:

```promql
up{job="observability-api"}
```

## Repository layout

```text
app/                         FastAPI application and instrumentation
tests/                       Automated API/metrics tests
config/prometheus.yml         Prometheus configuration for Docker Compose
config/prometheus.windows.yml Prometheus configuration for native Windows
config/rules/alerts.yml       Alerting rules
grafana/provisioning/         Data source and dashboard provisioning
grafana/dashboards/           Version-controlled Grafana dashboard
Dockerfile                   Container image definition
docker-compose.yml            Local multi-service deployment
requirements.txt              Python dependencies
```

## Engineering notes

- Metrics use route templates rather than raw URL paths to avoid high-cardinality labels.
- The demo uses a histogram for latency so percentile estimates can be calculated in PromQL.
- Prometheus alert rules define conditions only. For external notifications, configure Alertmanager or Grafana Alerting.
- CPU and memory measurements are a lightweight local demo; for production host-level metrics, deploy an appropriate host exporter and apply access controls.
- The default Compose image tags are convenient for a portfolio demo. Pin image versions or digests for reproducible production deployments.
- No real customer or payment data is used.

## Roadmap

- [ ] Add CI with linting, unit tests, and container build validation.
- [ ] Add Alertmanager and a test notification receiver.
- [ ] Add host metrics exporter and dashboard panels.
- [ ] Add load testing with Locust or k6.
- [ ] Add tracing with OpenTelemetry and a trace backend.
- [ ] Add environment-specific configuration and deployment manifests.

## License

MIT. See [LICENSE](LICENSE).
