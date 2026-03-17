import type { RadarFrame, ClientMessage } from "../types/radar";

const MODES = [
  { id: "src", label: "SRC" },
  { id: "mti", label: "MTI" },
  { id: "pulse_doppler", label: "Pulse Doppler" },
  { id: "tws", label: "TWS" },
] as const;

interface Props {
  frame: RadarFrame | null;
  sendMessage: (msg: ClientMessage) => void;
}

export function ModeSelector({ frame, sendMessage }: Props) {
  const activeMode = frame?.mode ?? "";

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {MODES.map((m) => {
        const isActive = activeMode.toLowerCase().includes(m.id.replace("_", " ")) ||
          activeMode.toLowerCase().includes(m.id);
        return (
          <button
            key={m.id}
            onClick={() => sendMessage({ type: "set_mode", mode: m.id })}
            className={`px-4 py-1.5 rounded text-sm font-mono transition-colors ${
              isActive
                ? "bg-[#238636] text-white"
                : "bg-[#21262d] text-[#8b949e] hover:bg-[#30363d]"
            }`}
          >
            {m.label}
          </button>
        );
      })}
    </div>
  );
}
