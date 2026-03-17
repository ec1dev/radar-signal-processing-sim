import type { ClientMessage } from "../types/radar";

interface Props {
  connected: boolean;
  time: number;
  sendMessage: (msg: ClientMessage) => void;
}

export function ControlBar({ connected, time, sendMessage }: Props) {
  return (
    <div className="flex items-center gap-3 text-sm font-mono">
      <button
        onClick={() => sendMessage({ type: "control", action: "play" })}
        className="px-3 py-1 bg-[#238636] rounded hover:bg-[#2ea043] text-white"
      >
        Play
      </button>
      <button
        onClick={() => sendMessage({ type: "control", action: "pause" })}
        className="px-3 py-1 bg-[#21262d] rounded hover:bg-[#30363d] text-[#c9d1d9]"
      >
        Pause
      </button>
      <button
        onClick={() => sendMessage({ type: "control", action: "reset" })}
        className="px-3 py-1 bg-[#21262d] rounded hover:bg-[#30363d] text-[#c9d1d9]"
      >
        Reset
      </button>
      <span className="text-[#484f58] ml-2">
        T = {time.toFixed(1)}s
      </span>
      <span className={`ml-auto text-xs ${connected ? "text-[#238636]" : "text-[#ff4444]"}`}>
        {connected ? "CONNECTED" : "DISCONNECTED"}
      </span>
    </div>
  );
}
