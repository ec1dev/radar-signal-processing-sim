import { useCallback, useEffect, useRef } from "react";
import { renderScope } from "../utils/scopeRenderer";
import type { RadarFrame } from "../types/radar";

interface Props {
  frame: RadarFrame | null;
  showGroundTruth: boolean;
}

export function RadarScope({ frame, showGroundTruth }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !frame) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const numTracks = frame.tracks
      ? frame.tracks.filter(t => t.status === "confirmed" || t.status === "coasting").length
      : 0;

    renderScope(
      ctx,
      rect.width,
      rect.height,
      frame.detections,
      frame.targets,
      frame.radar_params.max_unamb_range_km,
      showGroundTruth,
      frame.mode,
      frame.radar_params.prf_hz,
      frame.mode_info.num_detections,
      numTracks,
      frame.tracks,
      frame.scan_beam_az,
    );
  }, [frame, showGroundTruth]);

  useEffect(() => {
    const id = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(id);
  }, [draw]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full rounded"
      style={{ aspectRatio: "4 / 3", maxHeight: 520, imageRendering: "auto" }}
    />
  );
}
