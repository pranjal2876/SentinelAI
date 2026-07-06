# SentinelAI — Developer Guide

## 1. Layout

```
backend/app/
  core/       config (pydantic-settings), logging (loguru), security (JWT/bcrypt)
  vision/     detection, tracking, threat, anomaly, activity, explain, pipeline
  db/         async SQLAlchemy base + models
  schemas/    pydantic request/response models
  services/   camera manager, event bus, threat handler, alerts, analytics, reports
  api/v1/     REST endpoints + deps
  websocket/  connection manager + routes
  main.py     app factory + lifespan
frontend/src/ React app (components, pages, hooks, store, services, types)
ml/           training / evaluation / export
```

## 2. Environment

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt ruff pytest
uvicorn app.main:app --reload
```

Config is centralized in `app/core/config.py`. Never read `os.environ` directly
elsewhere — add a typed field to `Settings`.

## 3. Coding standards

- **PEP 8**, 100-col lines, `ruff check app` clean.
- **Type hints** everywhere; `from __future__ import annotations` at the top.
- **Docstrings** on modules and public functions/classes.
- **Logging** via `from app.core.logging import logger` (never bare `print`).
- **Errors**: raise `HTTPException` in endpoints; swallow-and-log in best-effort
  background paths (alerts, snapshots) so one failure can't break processing.
- Keep the per-frame hot path allocation-light; use dataclasses, not Pydantic,
  inside `vision/`.

## 4. Adding a new threat rule

1. Add a `ThreatCategory` value in `vision/types.py`.
2. Implement `_rule_x(...)` in `vision/threat/engine.py` returning
   `list[ThreatEvent]`; respect `self._ready(key, now)` for cooldowns.
3. Call it from `ThreatEngine.evaluate(...)`.
4. Add a rationale string in `vision/explain/gradcam.py::_RULE_RATIONALE`.
5. Write a unit test in `tests/test_threat_engine.py`.

Rules receive already-tracked objects with speed + trajectory, so most logic is
a few lines of geometry/kinematics.

## 5. Adding a detector/model

`ObjectDetector` wraps Ultralytics behind a stable interface returning
`Detection`. To swap models, point `YOLO_MODEL` at a new `.pt/.onnx/.engine`. To
add a *new modality* (e.g. fire/smoke), create a module under `vision/` exposing
`update(frame|tracks) -> Optional[ThreatEvent]` and wire it into
`SurveillancePipeline.process`.

## 6. Database changes

Edit models under `db/models/`, then:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## 7. Frontend

```bash
cd frontend && npm install && npm run dev
```

- State: Zustand (`store/`). API: typed Axios wrappers (`services/api.ts`).
- Live data: `hooks/useThreatSocket.ts`. Types mirror backend schemas in
  `types/index.ts` — keep them in sync when the API changes.
- Styling: Tailwind utility classes + a few `@layer components` helpers.

## 8. Testing

```bash
cd backend && pytest -q          # zones, tracker, threat engine
cd frontend && npm run build     # type-check + production build
```

CI (`.github/workflows/ci.yml`) runs ruff + pytest, the frontend build, and a
backend Docker build on every push/PR.

## 9. Performance tips

- Share a single `ObjectDetector` across cameras (the manager already does).
- Export to TensorRT (`ml/export/export_model.py --format engine --half`) for
  low latency on NVIDIA hardware.
- Increase `FRAME_STRIDE` and cap `MAX_INFERENCE_FPS` under many streams.
- Batch inference across cameras is the next optimization seam (group frames,
  one `model.predict` call).

## 10. Commit conventions

Conventional-commit prefixes (`feat`, `fix`, `docs`, `chore`, `refactor`,
`test`). Keep PRs focused; include tests for new rules/endpoints.
