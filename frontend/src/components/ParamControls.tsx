import type { RadarFrame, ClientMessage } from "../types/radar";

interface Props {
  frame: RadarFrame | null;
  sendMessage: (msg: ClientMessage) => void;
}

export function ParamControls({ frame, sendMessage }: Props) {
  const p = frame?.radar_params;
  if (!p) return null;

  const send = (param: string, value: number) =>
    sendMessage({ type: "set_param", param, value });

  return (
    <div className="space-y-3 text-sm font-mono">
      <div>
        <label className="text-[#8b949e] block mb-1">
          PRF: {p.prf_hz.toFixed(0)} Hz
        </label>
        <input
          type="range"
          min={500}
          max={10000}
          step={100}
          value={p.prf_hz}
          onChange={(e) => send("prf", Number(e.target.value))}
          className="w-full accent-[#238636]"
        />
        <div className="text-[#484f58] text-xs mt-0.5">
          R_max = {p.max_unamb_range_km.toFixed(1)} km | V_max = {p.max_unamb_velocity_mps.toFixed(1)} m/s
        </div>
      </div>

      <div>
        <label className="text-[#8b949e] block mb-1">
          Threshold: {frame?.radar_params ? "13.0" : "—"} dB
        </label>
        <input
          type="range"
          min={5}
          max={25}
          step={0.5}
          defaultValue={13}
          onChange={(e) => send("detection_threshold_db", Number(e.target.value))}
          className="w-full accent-[#238636]"
        />
      </div>

      <div>
        <label className="text-[#8b949e] block mb-1">
          Power: {(p.power_w / 1000).toFixed(0)} kW
        </label>
        <input
          type="range"
          min={1000}
          max={100000}
          step={1000}
          value={p.power_w}
          onChange={(e) => send("power", Number(e.target.value))}
          className="w-full accent-[#238636]"
        />
      </div>
    </div>
  );
}
