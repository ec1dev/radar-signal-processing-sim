/**
 * B-scope renderer — rectangular azimuth (x) vs range (y) display.
 *
 * Layout (War Thunder style):
 *   X-axis: azimuth in degrees, left = negative, right = positive
 *   Y-axis: range, TOP = close (0 km), BOTTOM = max range
 *
 * The scan volume is ±60 degrees.  Grid lines are drawn for range
 * and azimuth intervals.  Detections are rendered as bright blips,
 * with distinct styles for clutter, ambiguous, and tracked targets.
 */

import type { Detection, GroundTruthTarget, TWSTrack } from "../types/radar";

const HALF_SCAN = 60; // degrees

const C = {
  bg: "#0a0f0a",
  grid: "#0d3d0d",
  gridLabel: "#1a5c1a",
  hud: "#2a8a2a",
  det: "#00ff41",           // bright green — real targets
  detLabel: "#00ff41",
  clutter: "#1a4a1a",       // dim green — visible noise/static (not invisible)
  unknown: "#2a6a2a",       // medium dim — unclassified returns
  ambiguous: "#ffaa00",     // amber — range-ambiguous PD detections
  gt: "rgba(0,191,255,0.5)",
  beam: "rgba(0,255,65,0.18)",
  trkConfirmed: "#00ff41",
  trkTentative: "#ffcc00",
  trkCoasting: "#ff8c00",
  trail: "rgba(0,255,65,0.25)",
};

// Margins (px) for axis labels
const ML = 36, MR = 10, MT = 20, MB = 18;

/** Map (azimuth_deg, range_m) → canvas pixel coordinates. */
function toXY(
  az: number, rangeM: number,
  dw: number, dh: number, maxRange: number,
) {
  const x = ML + ((az + HALF_SCAN) / (2 * HALF_SCAN)) * dw;
  const y = MT + (rangeM / maxRange) * dh;
  return { x, y };
}

/** Map (x_east, y_north) in metres → (azimuth_deg, range_m). */
function xyToAzRange(xE: number, yN: number): { az: number; range: number } {
  return {
    az: (Math.atan2(xE, yN) * 180) / Math.PI,
    range: Math.sqrt(xE * xE + yN * yN),
  };
}

export function renderScope(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  detections: Detection[],
  targets: GroundTruthTarget[],
  maxRangeKm: number,
  showGroundTruth: boolean,
  modeName: string,
  prfHz: number,
  numDetections: number,
  numTracks: number,
  tracks?: TWSTrack[],
  scanBeamAz?: number,
) {
  const maxRange = maxRangeKm * 1000;
  const dw = width - ML - MR;   // drawable width
  const dh = height - MT - MB;   // drawable height

  // ── background ─────────────────────────────────────────────────
  ctx.fillStyle = C.bg;
  ctx.fillRect(0, 0, width, height);

  // ── grid lines ─────────────────────────────────────────────────
  ctx.strokeStyle = C.grid;
  ctx.lineWidth = 0.5;
  ctx.font = "9px monospace";
  ctx.fillStyle = C.gridLabel;

  // Horizontal: range marks
  const rangeStep = maxRangeKm <= 30 ? 5 : maxRangeKm <= 100 ? 15 : 25;
  for (let rKm = 0; rKm <= maxRangeKm; rKm += rangeStep) {
    const y = MT + (rKm / maxRangeKm) * dh;
    ctx.beginPath();
    ctx.moveTo(ML, y);
    ctx.lineTo(ML + dw, y);
    ctx.stroke();
    ctx.textAlign = "right";
    ctx.fillText(`${rKm}`, ML - 4, y + 3);
  }

  // Vertical: azimuth marks
  const azStep = HALF_SCAN <= 30 ? 10 : 15;
  for (let az = -HALF_SCAN; az <= HALF_SCAN; az += azStep) {
    const x = ML + ((az + HALF_SCAN) / (2 * HALF_SCAN)) * dw;
    ctx.beginPath();
    ctx.moveTo(x, MT);
    ctx.lineTo(x, MT + dh);
    ctx.stroke();
    ctx.textAlign = "center";
    ctx.fillText(`${az > 0 ? "+" : ""}${az}\u00b0`, x, MT - 5);
  }

  // ── TWS scan bar ───────────────────────────────────────────────
  if (scanBeamAz !== undefined) {
    const bx = ML + ((scanBeamAz + HALF_SCAN) / (2 * HALF_SCAN)) * dw;
    ctx.strokeStyle = C.beam;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(bx, MT);
    ctx.lineTo(bx, MT + dh);
    ctx.stroke();
  }

  // ── ground truth ───────────────────────────────────────────────
  if (showGroundTruth) {
    for (const t of targets) {
      const { az, range } = xyToAzRange(t.x, t.y);
      if (Math.abs(az) > HALF_SCAN || range > maxRange) continue;
      const p = toXY(az, range, dw, dh, maxRange);
      // Crosshair
      ctx.strokeStyle = C.gt;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(p.x - 5, p.y); ctx.lineTo(p.x + 5, p.y);
      ctx.moveTo(p.x, p.y - 5); ctx.lineTo(p.x, p.y + 5);
      ctx.stroke();
      ctx.fillStyle = C.gt;
      ctx.font = "8px monospace";
      ctx.textAlign = "left";
      ctx.fillText(t.id, p.x + 7, p.y - 3);
    }
  }

  // ── TWS tracks ─────────────────────────────────────────────────
  if (tracks) {
    for (const trk of tracks) {
      const { az, range } = xyToAzRange(trk.x, trk.y);
      if (Math.abs(az) > HALF_SCAN) continue;
      const p = toXY(az, Math.min(range, maxRange), dw, dh, maxRange);

      const color =
        trk.status === "confirmed" ? C.trkConfirmed
        : trk.status === "tentative" ? C.trkTentative
        : C.trkCoasting;

      // Trail
      if (trk.history.length > 1) {
        ctx.strokeStyle = C.trail;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let i = 0; i < trk.history.length; i++) {
          const h = xyToAzRange(trk.history[i][0], trk.history[i][1]);
          const hp = toXY(h.az, Math.min(h.range, maxRange), dw, dh, maxRange);
          if (i === 0) ctx.moveTo(hp.x, hp.y);
          else ctx.lineTo(hp.x, hp.y);
        }
        ctx.stroke();
      }

      // Track box [ ]
      const bsz = 8;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(p.x - bsz, p.y - bsz, bsz * 2, bsz * 2);

      // Center dot
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 2, 0, 2 * Math.PI);
      ctx.fill();

      // Velocity vector
      const vScale = 0.08;
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(p.x + trk.vx * vScale, p.y - trk.vy * vScale);
      ctx.stroke();

      // Label
      ctx.fillStyle = color;
      ctx.font = "9px monospace";
      ctx.textAlign = "left";
      ctx.fillText(trk.track_id, p.x + bsz + 3, p.y - 3);
    }
  }

  // ── detections ─────────────────────────────────────────────────
  // Three-tier rendering:
  //   1. Clutter  (is_clutter=true)           → nearly invisible noise/static
  //   2. Unknown  (no target_id, not clutter) → dim blip, no label
  //   3. Target   (has target_id)             → bright blip + labels
  const isTWS = modeName.toLowerCase().includes("tws");
  const isPD = modeName.toLowerCase().includes("pd") || modeName.toLowerCase().includes("pulse");

  for (const d of detections) {
    const az = d.azimuth_deg;
    if (Math.abs(az) > HALF_SCAN) continue;
    const p = toXY(az, Math.min(d.range_m, maxRange), dw, dh, maxRange);

    // Skip TWS track-based detections (already rendered as tracks above)
    if (isTWS && d.track_id) continue;

    // Classify: clutter → unknown → ambiguous → real target
    const isTarget = d.target_id != null && !d.is_clutter;
    const isClutter = d.is_clutter;

    let color: string;
    let w: number;   // blip half-width (px)
    let h: number;   // blip half-height (px)

    if (isClutter) {
      // Tier 1: dim but VISIBLE noise — creates the "sea of static" in SRC
      color = C.clutter;
      w = 2;
      h = 1;
    } else if (!isTarget) {
      // Tier 2: unclassified — brighter than clutter, no labels
      color = C.unknown;
      w = 3;
      h = 1.5;
    } else if (d.is_ambiguous) {
      // Tier 3a: real target, range-ambiguous (PD)
      color = C.ambiguous;
      w = 5;
      h = 2;
    } else {
      // Tier 3b: real target, clean detection
      color = C.det;
      w = 5;
      h = 2;
    }

    // SNR-based scaling (targets and unknowns only — clutter stays tiny)
    if (!isClutter) {
      const snr = d.snr_db ?? 0;
      if (snr > 40)      { w *= 1.8; h *= 1.6; }
      else if (snr > 30) { w *= 1.4; h *= 1.3; }
      else if (snr > 20) { w *= 1.0; h *= 1.0; }
      else               { w *= 0.7; h *= 0.7; }
    }

    // Draw blip
    ctx.fillStyle = color;
    ctx.fillRect(p.x - w, p.y - h, w * 2, h * 2);

    // Ambiguous ring
    if (d.is_ambiguous) {
      ctx.strokeStyle = C.ambiguous;
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.arc(p.x, p.y, w + 4, 0, 2 * Math.PI);
      ctx.stroke();
    }

    // Labels for real targets only
    if (isTarget) {
      ctx.fillStyle = C.detLabel;
      ctx.font = "8px monospace";
      ctx.textAlign = "left";
      let lbl = d.target_id!;
      if (isPD && d.velocity_mps != null) {
        lbl += ` ${d.velocity_mps.toFixed(0)}m/s`;
      }
      if (d.is_ambiguous) {
        lbl += " [AMB]";
      }
      ctx.fillText(lbl, p.x + w + 3, p.y + 3);
    }
  }

  // ── HUD overlay ────────────────────────────────────────────────
  ctx.font = "11px monospace";

  // Top-left: mode
  ctx.fillStyle = C.hud;
  ctx.textAlign = "left";
  const shortMode = modeName.split("(")[0].trim();
  ctx.fillText(shortMode, ML + 4, MT + 14);

  // Top-right: PRF
  ctx.textAlign = "right";
  ctx.fillText(`PRF ${prfHz.toFixed(0)}`, ML + dw - 4, MT + 14);

  // Bottom-left: detection count
  ctx.textAlign = "left";
  const label = numTracks > 0
    ? `TRK ${numTracks}`
    : `DET ${numDetections}`;
  ctx.fillText(label, ML + 4, MT + dh - 4);

  // Bottom-right: range scale
  ctx.textAlign = "right";
  ctx.fillText(`${maxRangeKm.toFixed(0)} km`, ML + dw - 4, MT + dh - 4);

  // ── border ─────────────────────────────────────────────────────
  ctx.strokeStyle = C.grid;
  ctx.lineWidth = 1;
  ctx.strokeRect(ML, MT, dw, dh);
}
