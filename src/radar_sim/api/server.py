"""
FastAPI WebSocket server for real-time radar simulation.

Streams SimulationFrame data at 20 Hz over a WebSocket connection.
Accepts client commands for mode switching, parameter tuning, and
play/pause/reset control.

    uvicorn radar_sim.api.server:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import math
from collections import defaultdict
from dataclasses import asdict

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from radar_sim.models import RadarMode, Detection
from radar_sim.engine import SimulationEngine, SimulationFrame
from radar_sim.modes.tws.track_manager import TrackStatus

app = FastAPI(title="Radar Signal Processing Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── helpers ───────────────────────────────────────────────────────────

_MODE_MAP = {
    "src": RadarMode.SRC,
    "mti": RadarMode.MTI,
    "pulse_doppler": RadarMode.PULSE_DOPPLER,
    "tws": RadarMode.TWS,
}

TRACK_HISTORY_LEN = 50


def _py(v):
    """Convert numpy scalars to native Python types for JSON serialization."""
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def _serialize_detection(d: Detection) -> dict:
    return {
        "range_m": _py(d.range_m),
        "azimuth_deg": _py(d.azimuth_deg),
        "velocity_mps": _py(d.velocity_mps),
        "snr_db": _py(d.snr_db),
        "target_id": d.target_id,
        "is_clutter": d.is_clutter,
        "is_ambiguous": d.is_ambiguous,
        "track_id": d.track_id,
        "track_quality": _py(d.track_quality),
    }


def _serialize_target(t: dict) -> dict:
    return {k: _py(v) for k, v in t.items()}


def _serialize_params(p: dict) -> dict:
    out = {}
    for k, v in p.items():
        if isinstance(v, list):
            out[k] = [_py(x) for x in v]
        else:
            out[k] = _py(v)
    return out


def serialize_frame(
    frame: SimulationFrame,
    engine: SimulationEngine,
    track_history: dict[str, list[list[float]]],
) -> dict:
    """Build the JSON message for one simulation frame."""
    detections = [_serialize_detection(d) for d in frame.detections]
    targets = [_serialize_target(t) for t in frame.targets]
    params = _serialize_params(frame.radar_params_summary)

    target_dets = [d for d in frame.detections if d.target_id is not None]
    clutter_dets = [d for d in frame.detections if d.is_clutter]

    msg: dict = {
        "type": "frame",
        "time": _py(frame.time),
        "mode": frame.mode,
        "detections": detections,
        "targets": targets,
        "radar_params": params,
        "mode_info": {
            "description": engine.active_mode.description,
            "num_detections": len(frame.detections),
            "num_clutter": len(clutter_dets),
            "num_targets": len(target_dets),
        },
    }

    # TWS-specific: tracks + beam azimuth
    if engine._active_mode == RadarMode.TWS:
        tws = engine._modes[RadarMode.TWS]
        tracks_out = []
        for trk in tws.track_manager.get_active_tracks():
            x, y = trk.ekf.position
            vx, vy = trk.ekf.velocity
            tid = trk.track_id

            # Append to history
            track_history[tid].append([_py(x), _py(y)])
            if len(track_history[tid]) > TRACK_HISTORY_LEN:
                track_history[tid] = track_history[tid][-TRACK_HISTORY_LEN:]

            tracks_out.append({
                "track_id": tid,
                "status": trk.status.value,
                "x": _py(x),
                "y": _py(y),
                "vx": _py(vx),
                "vy": _py(vy),
                "uncertainty": _py(trk.ekf.position_uncertainty),
                "hits": trk.hits,
                "misses": trk.misses,
                "history": track_history[tid],
            })

        msg["tracks"] = tracks_out
        msg["scan_beam_az"] = _py(tws.scan_controller.current_beam_az)

    return msg


# ── WebSocket endpoint ────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()

    engine = SimulationEngine()
    track_history: dict[str, list[list[float]]] = defaultdict(list)
    playing = True
    dt = 0.05  # 20 Hz

    async def send_frame() -> None:
        frame = engine.tick(dt)
        msg = serialize_frame(frame, engine, track_history)
        await websocket.send_text(json.dumps(msg))

    try:
        while True:
            # Check for incoming messages (non-blocking)
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=dt)
                data = json.loads(raw)
                msg_type = data.get("type")

                if msg_type == "set_mode":
                    mode_str = data.get("mode", "")
                    if mode_str in _MODE_MAP:
                        engine.set_mode(_MODE_MAP[mode_str])
                        track_history.clear()

                elif msg_type == "set_param":
                    param = data.get("param", "")
                    value = data.get("value")
                    if param and value is not None:
                        try:
                            engine.update_radar_param(param, float(value))
                            track_history.clear()
                        except ValueError:
                            pass

                elif msg_type == "control":
                    action = data.get("action")
                    if action == "pause":
                        playing = False
                    elif action == "play":
                        playing = True
                    elif action == "reset":
                        engine = SimulationEngine()
                        track_history.clear()
                        playing = True

            except asyncio.TimeoutError:
                pass

            if playing:
                await send_frame()

    except WebSocketDisconnect:
        pass


# ── Health check ──────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
