import { useState } from "react";
import { useRadarWebSocket } from "./hooks/useRadarWebSocket";
import { RadarScope } from "./components/RadarScope";
import { ModeSelector } from "./components/ModeSelector";
import { ParamControls } from "./components/ParamControls";
import { DetectionTable } from "./components/DetectionTable";
import { ControlBar } from "./components/ControlBar";

const WS_URL = `ws://${window.location.hostname}:8000/ws`;

function App() {
  const { frame, connected, sendMessage } = useRadarWebSocket(WS_URL);
  const [showGT, setShowGT] = useState(true);

  const modeInfo = frame?.mode_info;
  const hasTracks = frame?.tracks && frame.tracks.length > 0;

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#c9d1d9] p-4">
      <div className="max-w-7xl mx-auto space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <ModeSelector frame={frame} sendMessage={sendMessage} />
          <ControlBar
            connected={connected}
            time={frame?.time ?? 0}
            sendMessage={sendMessage}
          />
        </div>

        {modeInfo && (
          <div className="text-xs text-[#484f58] font-mono">{modeInfo.description}</div>
        )}

        {/* Main content */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
          {/* Left: Scope */}
          <div>
            <RadarScope frame={frame} showGroundTruth={showGT} />
            <label className="flex items-center gap-1.5 text-xs font-mono text-[#8b949e] cursor-pointer mt-2">
              <input
                type="checkbox"
                checked={showGT}
                onChange={(e) => setShowGT(e.target.checked)}
                className="accent-[#238636]"
              />
              Show Ground Truth
            </label>
          </div>

          {/* Right: Controls + Info */}
          <div className="space-y-4">
            <div className="bg-[#161b22] rounded p-3">
              <h3 className="text-xs text-[#8b949e] font-mono mb-2 uppercase">Radar Parameters</h3>
              <ParamControls frame={frame} sendMessage={sendMessage} />
            </div>

            <div className="bg-[#161b22] rounded p-3">
              <h3 className="text-xs text-[#8b949e] font-mono mb-2 uppercase">Mode Statistics</h3>
              {modeInfo && (
                <div className="text-sm font-mono space-y-0.5">
                  <div>Targets: <span className="text-[#00ff41]">{modeInfo.num_targets}</span></div>
                  <div>Clutter: <span className="text-[#484f58]">{modeInfo.num_clutter}</span></div>
                  {hasTracks && (
                    <div>Tracks: <span className="text-[#00ff41]">
                      {frame!.tracks!.filter(t => t.status === "confirmed").length}
                    </span> confirmed</div>
                  )}
                </div>
              )}
            </div>

            {frame?.radar_params && (
              <div className="bg-[#161b22] rounded p-3">
                <h3 className="text-xs text-[#8b949e] font-mono mb-2 uppercase">System</h3>
                <div className="text-xs font-mono text-[#484f58] space-y-0.5">
                  <div>Freq: {frame.radar_params.frequency_ghz.toFixed(1)} GHz</div>
                  <div>Range res: {frame.radar_params.range_resolution_m.toFixed(0)} m</div>
                  <div>Blind: {frame.radar_params.blind_speeds_mps.slice(0, 3).map(v => v.toFixed(0)).join(", ")} m/s</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Detection table */}
        {frame && (
          <div className="bg-[#161b22] rounded p-3">
            <h3 className="text-xs text-[#8b949e] font-mono mb-2 uppercase">Detections</h3>
            <DetectionTable detections={frame.detections} />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
