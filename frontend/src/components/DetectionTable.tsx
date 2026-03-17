import type { Detection } from "../types/radar";

interface Props {
  detections: Detection[];
}

export function DetectionTable({ detections }: Props) {
  // Show non-clutter detections first, sorted by range, then clutter
  const sorted = [...detections]
    .filter((d) => !d.is_clutter)
    .sort((a, b) => a.range_m - b.range_m)
    .slice(0, 20);

  const clutterCount = detections.filter((d) => d.is_clutter).length;

  return (
    <div className="text-xs font-mono">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-[#8b949e] border-b border-[#21262d]">
              <th className="text-left py-1 px-2">ID</th>
              <th className="text-right py-1 px-2">Range</th>
              <th className="text-right py-1 px-2">Vel</th>
              <th className="text-right py-1 px-2">SNR</th>
              <th className="text-center py-1 px-2">Flags</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((d, i) => (
              <tr key={i} className="border-b border-[#161b22] hover:bg-[#161b22]">
                <td className="py-1 px-2 text-[#c9d1d9]">
                  {d.track_id ?? d.target_id ?? "—"}
                </td>
                <td className="py-1 px-2 text-right text-[#00ff41]">
                  {(d.range_m / 1000).toFixed(1)} km
                </td>
                <td className="py-1 px-2 text-right text-[#8b949e]">
                  {d.velocity_mps != null ? `${d.velocity_mps.toFixed(0)} m/s` : "—"}
                </td>
                <td className="py-1 px-2 text-right text-[#8b949e]">
                  {d.snr_db.toFixed(0)}
                </td>
                <td className="py-1 px-2 text-center">
                  {d.is_ambiguous && <span className="text-[#ff4444]">AMB</span>}
                  {d.track_quality != null && (
                    <span className="text-[#00ff41] ml-1">
                      Q{(d.track_quality * 100).toFixed(0)}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {clutterCount > 0 && (
        <div className="text-[#484f58] mt-1 px-2">
          + {clutterCount} clutter returns (hidden)
        </div>
      )}
    </div>
  );
}
