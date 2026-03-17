import type { Detection, GroundTruthTarget, TWSTrack } from "../types/radar";

const COLORS = {
  bg: "#0a0f0a",
  ring: "#0d3d0d",
  ringLabel: "#1a5c1a",
  detection: "#00ff41",
  clutter: "#1a5c1a",
  ambiguous: "#ff4444",
  groundTruth: "rgba(0,191,255,0.5)",
  groundTruthLine: "rgba(0,191,255,0.25)",
  beamSweep: "rgba(0,255,65,0.12)",
  trackConfirmed: "#00ff41",
  trackTentative: "#ffcc00",
  trackCoasting: "#ff8c00",
  trackTrail: "rgba(0,255,65,0.3)",
};

function toCanvas(
  azDeg: number,
  rangeM: number,
  cx: number,
  cy: number,
  radius: number,
  maxRange: number,
) {
  const azRad = (azDeg * Math.PI) / 180;
  const r = (rangeM / maxRange) * radius;
  return {
    x: cx + r * Math.sin(azRad),
    y: cy - r * Math.cos(azRad),
  };
}

function xyToCanvas(
  xEast: number,
  yNorth: number,
  cx: number,
  cy: number,
  radius: number,
  maxRange: number,
) {
  const range = Math.sqrt(xEast * xEast + yNorth * yNorth);
  const azDeg = (Math.atan2(xEast, yNorth) * 180) / Math.PI;
  return toCanvas(azDeg, range, cx, cy, radius, maxRange);
}

export function renderScope(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  detections: Detection[],
  targets: GroundTruthTarget[],
  maxRangeKm: number,
  showGroundTruth: boolean,
  tracks?: TWSTrack[],
  scanBeamAz?: number,
) {
  const size = Math.min(width, height);
  const cx = width / 2;
  const cy = height / 2;
  const radius = size / 2 - 30;
  const maxRange = maxRangeKm * 1000;

  // Background
  ctx.fillStyle = COLORS.bg;
  ctx.fillRect(0, 0, width, height);

  // Scope circle clip
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, radius + 1, 0, 2 * Math.PI);
  ctx.clip();

  // Range rings
  const ringCount = 5;
  const ringSpacing = maxRangeKm / ringCount;
  ctx.strokeStyle = COLORS.ring;
  ctx.lineWidth = 0.5;
  ctx.font = "10px monospace";
  ctx.fillStyle = COLORS.ringLabel;
  for (let i = 1; i <= ringCount; i++) {
    const r = (i / ringCount) * radius;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.fillText(`${(i * ringSpacing).toFixed(0)} km`, cx + 4, cy - r + 12);
  }

  // Cardinal lines
  ctx.strokeStyle = COLORS.ring;
  ctx.lineWidth = 0.3;
  for (let deg = 0; deg < 360; deg += 30) {
    const rad = (deg * Math.PI) / 180;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + radius * Math.sin(rad), cy - radius * Math.cos(rad));
    ctx.stroke();
  }
  // Cardinal labels
  ctx.fillStyle = COLORS.ringLabel;
  ctx.font = "11px monospace";
  ctx.textAlign = "center";
  ctx.fillText("N", cx, cy - radius - 6);
  ctx.fillText("S", cx, cy + radius + 14);
  ctx.fillText("E", cx + radius + 12, cy + 4);
  ctx.fillText("W", cx - radius - 12, cy + 4);

  // TWS beam sweep
  if (scanBeamAz !== undefined) {
    const azRad = (scanBeamAz * Math.PI) / 180;
    ctx.strokeStyle = COLORS.beamSweep;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + radius * Math.sin(azRad), cy - radius * Math.cos(azRad));
    ctx.stroke();
  }

  // Ground truth overlay
  if (showGroundTruth) {
    for (const t of targets) {
      if (t.range_m > maxRange) continue;
      const p = xyToCanvas(t.x, t.y, cx, cy, radius, maxRange);
      // Crosshair
      ctx.strokeStyle = COLORS.groundTruth;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(p.x - 6, p.y);
      ctx.lineTo(p.x + 6, p.y);
      ctx.moveTo(p.x, p.y - 6);
      ctx.lineTo(p.x, p.y + 6);
      ctx.stroke();
      // Label
      ctx.fillStyle = COLORS.groundTruth;
      ctx.font = "9px monospace";
      ctx.textAlign = "left";
      ctx.fillText(t.id, p.x + 8, p.y - 4);
    }
  }

  // TWS track trails and positions
  if (tracks) {
    for (const trk of tracks) {
      const color =
        trk.status === "confirmed"
          ? COLORS.trackConfirmed
          : trk.status === "tentative"
            ? COLORS.trackTentative
            : COLORS.trackCoasting;

      // Trail
      if (trk.history.length > 1) {
        ctx.strokeStyle = COLORS.trackTrail;
        ctx.lineWidth = 1;
        ctx.beginPath();
        const p0 = xyToCanvas(trk.history[0][0], trk.history[0][1], cx, cy, radius, maxRange);
        ctx.moveTo(p0.x, p0.y);
        for (let i = 1; i < trk.history.length; i++) {
          const pi = xyToCanvas(trk.history[i][0], trk.history[i][1], cx, cy, radius, maxRange);
          ctx.lineTo(pi.x, pi.y);
        }
        ctx.stroke();
      }

      // Track position
      const tp = xyToCanvas(trk.x, trk.y, cx, cy, radius, maxRange);

      // Uncertainty circle
      const uncR = (trk.uncertainty / maxRange) * radius;
      ctx.strokeStyle = color;
      ctx.lineWidth = 0.5;
      ctx.globalAlpha = 0.3;
      ctx.beginPath();
      ctx.arc(tp.x, tp.y, Math.max(uncR, 3), 0, 2 * Math.PI);
      ctx.stroke();
      ctx.globalAlpha = 1;

      // Track marker
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(tp.x, tp.y, 4, 0, 2 * Math.PI);
      ctx.fill();

      // Track label
      ctx.fillStyle = color;
      ctx.font = "9px monospace";
      ctx.textAlign = "left";
      ctx.fillText(trk.track_id, tp.x + 7, tp.y - 5);
    }
  }

  // Detections (draw after tracks so they appear on top)
  for (const d of detections) {
    const p = toCanvas(d.azimuth_deg, d.range_m, cx, cy, radius, maxRange);
    if (p.x < 0 || p.x > width || p.y < 0 || p.y > height) continue;

    let color = COLORS.detection;
    let size = 2.5;
    if (d.is_clutter) {
      color = COLORS.clutter;
      size = 1.5;
    } else if (d.is_ambiguous) {
      color = COLORS.ambiguous;
    }
    // Scale by SNR
    const snrScale = Math.min(Math.max(d.snr_db / 40, 0.5), 2.5);
    size *= snrScale;

    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(p.x, p.y, size, 0, 2 * Math.PI);
    ctx.fill();

    if (d.is_ambiguous) {
      ctx.strokeStyle = COLORS.ambiguous;
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.arc(p.x, p.y, size + 3, 0, 2 * Math.PI);
      ctx.stroke();
    }
  }

  // Center dot (radar)
  ctx.fillStyle = COLORS.detection;
  ctx.beginPath();
  ctx.arc(cx, cy, 2, 0, 2 * Math.PI);
  ctx.fill();

  ctx.restore();

  // Scope border
  ctx.strokeStyle = COLORS.ring;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
  ctx.stroke();
}
