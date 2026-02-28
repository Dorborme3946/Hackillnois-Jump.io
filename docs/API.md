# JumpAI API Reference

Base URL: `http://localhost:8000/api` (dev) · `https://your-backend.railway.app/api` (prod)

---

## Endpoints

### `POST /upload`

Upload a video file to start jump analysis.

**Form Data:**
| Field | Type | Required | Description |
|---|---|---|---|
| `file` | File | Yes | Video file (MP4, MOV, AVI, WebM) |
| `user_id` | string | No | User identifier (default: `"anonymous"`) |

**Response `200`:**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "step": "queued",
  "created_at": "2026-02-27T12:00:00Z",
  "updated_at": "2026-02-27T12:00:00Z",
  "user_id": "user123",
  "filename": "jump.mp4",
  "error": null
}
```

---

### `GET /jobs/{job_id}`

Poll job status.

**Statuses:** `pending` → `processing` → `done` | `failed`

**Steps (processing sub-state):**
- `validating`
- `extracting_pose`
- `calculating_height`
- `analyzing_biomechanics`
- `scoring`
- `fetching_history`
- `generating_report`
- `storing_memory`
- `complete`

**Response `200`:** Same shape as `/upload` response.

---

### `GET /results/{job_id}`

Get full analysis result. Only available when `status === "done"`.

Returns `202` with error detail if still processing.

**Response `200`:**
```json
{
  "job_id": "uuid",
  "user_id": "user123",
  "filename": "jump.mp4",
  "jump_height_inches": 28.4,
  "jump_height_cm": 72.1,
  "flight_time_ms": 483.0,
  "confidence": 0.94,
  "scorecard": {
    "jump_height_score": 64,
    "arm_swing_score": 72,
    "knee_bend_score": 81,
    "penultimate_step_score": 55,
    "heel_plant_score": 85,
    "hip_drive_score": 68,
    "body_alignment_score": 77,
    "landing_score": 60,
    "elite_similarity_score": 42,
    "overall_score": 67
  },
  "biomechanics": { ... },
  "claude_report": "## Performance Summary\n...",
  "pose_frames_sample": [
    {
      "frame_idx": 0,
      "timestamp_ms": 0.0,
      "keypoints": { "nose": [320, 120, 0.99], "left_hip": [300, 350, 0.95], ... }
    }
  ],
  "jump_event": {
    "takeoff_frame": 45,
    "takeoff_ms": 1500.0,
    "landing_frame": 60,
    "landing_ms": 2000.0,
    "flight_time_ms": 500.0,
    "height_inches": 30.7,
    "height_cm": 78.0,
    "confidence": 0.92
  },
  "video_metadata": { "width": 1920, "height": 1080, "fps": 30.0, ... },
  "created_at": "2026-02-27T12:01:00Z"
}
```

---

### `GET /users/{user_id}/history`

Paginated jump history from Supermemory.

**Query Params:**
| Param | Default | Max |
|---|---|---|
| `limit` | 10 | 50 |

---

### `GET /users/{user_id}/stats`

Aggregate progress stats.

**Response `200`:**
```json
{
  "user_id": "user123",
  "stats": {
    "total_jumps": 12,
    "best_height_inches": 32.1,
    "avg_height_inches": 27.4,
    "best_overall_score": 74,
    "avg_overall_score": 62.3,
    "recent_heights": [26.0, 27.5, 28.4, ...],
    "recent_scores": [58, 61, 67, ...]
  }
}
```

---

### `DELETE /videos/{job_id}`

Delete video file from local storage (not the analysis result).

---

### `GET /health`

Health check.

```json
{ "status": "ok", "version": "1.0.0" }
```

---

## Error Format

All errors return:
```json
{ "detail": "Human-readable error message" }
```
