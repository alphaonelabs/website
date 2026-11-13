# EarthMind 🌍

AI-powered platform for monitoring environmental data from multiple sources.
Uses machine learning to analyze trends, detect anomalies, and identify
potential ecological risks. Includes real-time alerts, visual dashboards, and
geospatial insights to help researchers, communities, and organizations respond
to environmental changes.

**Hosted on [Cloudflare Python Workers](https://developers.cloudflare.com/workers/languages/python/) · Powered by [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/)**

---

## Features

| Feature | Description |
|---|---|
| 📡 **Multi-source ingestion** | REST API accepts readings from IoT sensors, satellites, weather stations, and community reports |
| 🤖 **AI analysis** | Cloudflare Workers AI (Llama 3.1 8B) generates trend narratives, risk assessments, and anomaly explanations |
| 📈 **Trend analysis** | Linear regression, short/long moving averages, EMA, and rate-of-change metrics |
| 🔍 **Anomaly detection** | Z-score, IQR (Tukey fences), and rolling-average methods running entirely in Python |
| 🚨 **Real-time alerts** | Automatic threshold-based alerts + manual alert management via REST API |
| 🗺️ **Geospatial insights** | GeoJSON endpoint consumed by a Leaflet.js map on the dashboard |
| 📊 **Visual dashboard** | Single-page web app with Chart.js trend charts, anomaly tables, and AI insight panels |

---

## Project Structure

```
earthmind/
├── wrangler.toml              # Cloudflare Workers configuration
├── schema.sql                 # D1 database schema + seed data
├── requirements.txt           # Local dev / test dependencies
├── src/
│   ├── index.py               # Worker entry point & HTTP routing
│   ├── services/
│   │   ├── anomaly.py         # Statistical anomaly detection
│   │   ├── trends.py          # Trend analysis
│   │   └── ai_service.py      # Cloudflare AI integration
│   └── static/
│       └── index.py           # Dashboard HTML (served inline)
└── tests/
    ├── test_anomaly.py        # 34 unit tests for anomaly detection
    └── test_trends.py         # 33 unit tests for trend analysis
```

---

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) ≥ 18 (for Wrangler CLI)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/): `npm install -g wrangler`
- A Cloudflare account with Workers AI enabled
- Python 3.12+ (for local testing only)

### 1. Clone & configure

```bash
git clone https://github.com/alphaonelabs/website.git
cd website/earthmind
```

Edit `wrangler.toml` and replace the placeholder IDs:

```bash
# Create a KV namespace
wrangler kv namespace create ENV_CACHE

# Create a D1 database
wrangler d1 create earthmind
```

Copy the returned IDs into `wrangler.toml`.

### 2. Initialise the database

```bash
wrangler d1 execute earthmind --local --file schema.sql  # local dev
wrangler d1 execute earthmind --file schema.sql          # production
```

### 3. Run locally

```bash
wrangler dev
# Dashboard available at http://localhost:8787
```

### 4. Deploy

```bash
wrangler deploy
```

---

## API Reference

All endpoints return JSON (or GeoJSON for `/api/geo`).
CORS headers are set for all responses.

### Environmental Data

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/data` | Query readings (`?parameter=pm2_5&limit=100&since=ISO8601&source=&location=`) |
| `POST` | `/api/data` | Ingest a new reading (see body below) |

**POST /api/data body:**
```json
{
  "source": "sensor-001",
  "source_type": "iot_sensor",
  "parameter": "pm2_5",
  "value": 18.4,
  "unit": "µg/m³",
  "timestamp": "2024-09-01T12:00:00Z",
  "location": "Downtown Station",
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

### Anomaly Detection

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/anomalies` | Run anomaly detection (`?parameter=pm2_5&zscore_threshold=2.5`) |

### Trend Analysis

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/trends` | Compute trends (`?parameter=pm2_5&limit=200`) |

### Alerts

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/alerts` | List alerts (`?active=true&severity=high`) |
| `POST` | `/api/alerts` | Create a manual alert |
| `PUT` | `/api/alerts/:id/resolve` | Resolve an alert |

### AI Analytics

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/analytics/trends` | AI narrative for a parameter (`?parameter=pm2_5`) |
| `GET` | `/api/analytics/risk` | Ecological risk assessment |
| `GET` | `/api/analytics/anomaly-explain` | AI explanation of the top anomaly |
| `GET` | `/api/analytics/summary` | Executive dashboard summary |

### Geospatial

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/geo` | GeoJSON FeatureCollection of sensor readings (`?parameter=pm2_5`) |

### Device Management

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/devices/register` | Register a new device and receive its API key |
| `DELETE` | `/api/devices/:device_id` | Deactivate a device (admin) |

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Returns `{"status":"ok"}` |

---

## Device Authentication

EarthMind supports per-device API keys for authenticated sensor ingestion. Authenticated submissions are rate-limited to prevent abuse. Unauthenticated submissions continue to work for backward compatibility.

### Register a device

```http
POST /api/devices/register
Content-Type: application/json

{
  "device_id": "sensor-042",
  "owner_name": "Alice Johnson",
  "location": "Riverside Park",
  "latitude": 40.7282,
  "longitude": -73.9942
}
```

**Response (201 Created):**
```json
{
  "device_id": "sensor-042",
  "api_key": "your-raw-api-key-shown-only-once",
  "message": "Save this key — it will not be shown again."
}
```

Store the returned `api_key` securely — it is shown only once and cannot be retrieved later.

### Send an authenticated reading

Include the `X-Device-ID` and `X-API-Key` headers with every POST to `/api/data`:

```http
POST /api/data
Content-Type: application/json
X-Device-ID: sensor-042
X-API-Key: your-raw-api-key

{
  "source": "sensor-042",
  "source_type": "iot_sensor",
  "parameter": "pm2_5",
  "value": 18.4,
  "unit": "µg/m³",
  "timestamp": "2024-09-01T12:00:00Z",
  "location": "Riverside Park"
}
```

If the credentials are invalid, the server responds with `401 Unauthorized`.

### Rate limits

Each device is limited to **30 requests per 60-second window**. When the limit is exceeded the server responds with `429 Too Many Requests`:

```json
{
  "error": "Rate limit exceeded",
  "limit": 30,
  "window": "60s"
}
```

The window resets automatically at the start of the next 60-second period.

**Known limitation — fixed-window boundary burst:** The rate-limit window is anchored to wall-clock minute boundaries (`HH:MM:00`). A device can send up to 30 requests just before `HH:MM:00` and another 30 immediately after, resulting in up to 60 requests passing through in under two seconds across a window boundary. For typical low-frequency IoT sensors this is acceptable; high-frequency deployments should be aware of this behaviour.

**Known limitation — non-atomic check and increment:** The rate-limit check and the subsequent reading insert are two separate database round-trips. Under concurrent requests from the same device, both may pass the limit check before either increments the counter. For normal sensor ingest rates this race is negligible.

### Backward compatibility

Requests to `POST /api/data` that omit the `X-Device-ID` and `X-API-Key` headers are still accepted without authentication. Existing integrations continue to work without modification.

**Note:** Because authentication is opt-in (enforced only when both headers are present), a device that has registered can still submit readings via the unauthenticated path by simply omitting the headers. The unauthenticated path carries no rate limiting. If your deployment requires that all registered devices authenticate, enforce this at the network or gateway level rather than relying on the headers alone.

---

## Supported Environmental Parameters

| Parameter key | Description | Alert threshold |
|---|---|---|
| `pm2_5` | Fine particulate matter | 35 µg/m³ |
| `pm10` | Coarse particulate matter | 50 µg/m³ |
| `co2` | Carbon dioxide | 1000 ppm |
| `no2` | Nitrogen dioxide | 40 µg/m³ |
| `o3` | Ozone | 100 µg/m³ |
| `temperature` | Air/water temperature | 40 °C |
| `ph` | Water / soil pH | 9.0 |
| `noise_db` | Noise level | 85 dB |
| `humidity` | Relative humidity | — |
| `dissolved_o2` | Dissolved oxygen | — |

---

## Running Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

All 67 tests run against the pure-Python services (no Cloudflare runtime required).

---

## Architecture

```
Browser / API Client
       │
       ▼
Cloudflare Python Worker (src/index.py)
       │
       ├── services/anomaly.py      (Z-score, IQR, rolling-avg)
       ├── services/trends.py       (linear regression, SMA, EMA)
       ├── services/ai_service.py   ──► Cloudflare Workers AI
       │                                (@cf/meta/llama-3.3-70b-instruct-fp8-fast)
       ├── env.DB  (Cloudflare D1 / SQLite)
       └── env.ENV_CACHE (Cloudflare KV)
```

---

## License

[GNU Affero General Public License v3](LICENSE)
