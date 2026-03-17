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

    renderScope(
      ctx,
      rect.width,
      rect.height,
      frame.detections,
      frame.targets,
      frame.radar_params.max_unamb_range_km,
      showGroundTruth,
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
      className="w-full aspect-square max-h-[600px] rounded"
      style={{ imageRendering: "auto" }}
    />
  );
}
