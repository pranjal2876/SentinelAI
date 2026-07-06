# SentinelAI — API Reference

Base URL: `http://<host>:8000`  ·  API prefix: `/api/v1`
Interactive docs: `/docs` (Swagger) and `/redoc`.

Authentication: **Bearer JWT**. Obtain a token via `/auth/login`, then send
`Authorization: Bearer <access_token>` on every request. Access tokens expire
(default 60 min); use `/auth/refresh` with the refresh token to renew.

Roles: `admin` > `operator` > `viewer`. Write endpoints require `operator`+.

---

## Auth

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/auth/register` | `{username,email,password,full_name}` | Create account |
| POST | `/auth/login` | form: `username`,`password` | Returns `{access_token,refresh_token}` |
| POST | `/auth/refresh` | `{refresh_token}` | New token pair |
| GET | `/auth/me` | — | Current user |

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin&password=admin123"
```

---

## Cameras

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/cameras` | viewer | List cameras (live status/fps merged in) |
| POST | `/cameras` | operator | Create `{camera_id,name,source,location}` |
| PATCH | `/cameras/{id}` | operator | Update fields |
| DELETE | `/cameras/{id}` | operator | Delete + stop worker |
| POST | `/cameras/{id}/start` | operator | Start capture + inference |
| POST | `/cameras/{id}/stop` | operator | Stop worker |

`source` may be a webcam index (`"0"`), an RTSP URL, or a file path.

---

## Threats

| Method | Path | Description |
|---|---|---|
| GET | `/threats` | Filter by `camera_id,category,severity,start,end,acknowledged,limit,offset` |
| GET | `/threats/{id}` | Single event |
| POST | `/threats/{id}/acknowledge` | Mark reviewed |
| GET | `/threats/{id}/explain` | Explainable-AI rationale |

---

## Zones

| Method | Path | Description |
|---|---|---|
| GET | `/zones?camera_id=` | List zones |
| POST | `/zones` | Create `{zone_id,camera_id,name,type,points,allowed_direction}` |
| PATCH | `/zones/{zone_id}` | Update (auto-syncs to live worker) |
| DELETE | `/zones/{zone_id}` | Delete |

`type`: `restricted` \| `tripwire` \| `directional` \| `vehicle_exclude` \| `counting`.
`points` are normalized `[x,y]` in `[0,1]`; tripwire/counting need exactly 2 points.

---

## Analytics & Reports

| Method | Path | Description |
|---|---|---|
| GET | `/analytics/dashboard` | Aggregate stats (totals, by category/severity/camera, 24h timeline) |
| GET | `/analytics/report?start=&end=&fmt=pdf\|xlsx&camera_id=` | Download report |

---

## System

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/system/health` | none | Liveness probe |
| GET | `/system/info` | viewer | Runtime env, device, model info |

---

## WebSockets

| Endpoint | Payload | Purpose |
|---|---|---|
| `/ws/events` | JSON `LiveThreatMessage` | Live threat push |
| `/ws/stream/{camera_id}` | binary JPEG | Annotated live frames |
| `/stream/{camera_id}.mjpg` | multipart MJPEG | `<img>`-compatible fallback |

Example live-events payload:

```json
{
  "type": "threat",
  "camera_id": "gate-01",
  "category": "intrusion",
  "severity": "high",
  "score": 0.82,
  "message": "Person 7 entered restricted zone 'Perimeter'.",
  "timestamp": 1751800000.123,
  "metadata": { "zone": "Perimeter", "track_ids": [7], "snapshot": "..." }
}
```

---

## Error format

Standard FastAPI error shape:

```json
{ "detail": "Camera not found" }
```

Common codes: `401` (missing/invalid token), `403` (role), `404` (not found),
`400` (validation / duplicate), `500` (unhandled — logged server-side).
