# SentinelAI — User Manual

A guide for security operators using the dashboard.

## 1. Signing in

Open the dashboard (default http://localhost:5173). On first run, log in with
**admin / admin123**.

> **Change the default password immediately.** Register a new admin via
> `POST /api/v1/auth/register` (or the API docs at `/docs`), then disable the
> seeded account.

## 2. Dashboard

The landing page shows:
- **Stat cards** — total threats, threats today, active cameras, live events.
- **24h activity** — hourly threat volume.
- **Live Threat Feed** — real-time events as they fire (WebSocket).
- **Category** and **Severity** breakdown charts.

The **Live/Disconnected** pill in the top bar shows the event-stream status.

## 3. Adding a camera

1. Go to **Cameras → Add Camera**.
2. Fill in:
   - **camera_id** — unique slug, e.g. `gate-01`.
   - **name** — human label.
   - **source** — `0` (default webcam), an RTSP URL
     (`rtsp://user:pass@192.168.1.10:554/stream`), or a file path.
   - **location** — optional.
3. Save, then press **▶ Start** to begin processing.

## 4. Live view

**Live View** shows every camera as a tile with the annotated stream (bounding
boxes, track IDs, trajectories, zone overlays, and a threat banner). FPS is shown
top-right. Start/stop each camera from its tile.

## 5. Defining detection zones

Zones make rules location-aware. Create them via the API (`POST /zones`) or a
future in-canvas editor. Types:

| Type | Effect |
|---|---|
| `restricted` | Any person inside → intrusion; ≥2 → multiple intruders |
| `tripwire` | Crossing the line → intrusion event |
| `directional` | Movement opposing `allowed_direction` → wrong-direction |
| `vehicle_exclude` | Vehicle inside → vehicle-in-zone |
| `counting` | Crossings increment entry/exit counters |

Points are normalized `[0..1]`, so a zone drawn once works at any resolution.

## 6. Reviewing threats

**Threats** lists all events with filters (category, severity). For each event:
- **ℹ Explain** — opens the Explainable-AI panel: *why* it fired, confidence, and
  the numeric factors (dwell time, speed, zone, anomaly z-score, …).
- **✓ Acknowledge** — marks it reviewed (hidden from "unacknowledged" filters).

## 7. Analytics & reports

**Analytics** shows threats per camera and category frequency. Export a 7-day
report as **PDF** or **Excel** with one click. Reports include timestamp, camera,
category, severity, score, and message per event.

## 8. Alerts

When configured (`.env`), **high** and **critical** events also dispatch:
- **Email** (SMTP) with the snapshot attached.
- **Telegram** message/photo to your bot chat.

All events always appear in the dashboard feed and are stored with a snapshot.

## 9. Tuning sensitivity

Adjust thresholds in `.env` (restart backend to apply):

| Setting | Meaning |
|---|---|
| `LOITERING_SECONDS` | dwell time before loitering fires |
| `ABANDONED_OBJECT_SECONDS` | static time before an object is "abandoned" |
| `CROWD_THRESHOLD` | people count that constitutes a crowd |
| `RUNNING_SPEED_PX_PER_S` | speed classed as running |
| `DETECTION_CONF_THRESHOLD` | minimum detection confidence |

## 10. Good practice

- Prefer `yolov8n/s` on CPU, `yolov8m/l` on GPU.
- Use `FRAME_STRIDE` > 1 to trade latency for load on many cameras.
- Only deploy where you are legally permitted to record; keep snapshots secure.
