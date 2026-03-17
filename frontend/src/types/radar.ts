export interface Detection {
  range_m: number;
  azimuth_deg: number;
  velocity_mps: number | null;
  snr_db: number;
  target_id: string | null;
  is_clutter: boolean;
  is_ambiguous: boolean;
  track_id: string | null;
  track_quality: number | null;
}

export interface GroundTruthTarget {
  id: string;
  label: string;
  x: number;
  y: number;
  altitude: number;
  range_m: number;
  radial_velocity: number;
  speed: number;
  rcs: number;
}

export interface RadarParams {
  frequency_ghz: number;
  prf_hz: number;
  power_w: number;
  pulse_width_us: number;
  max_unamb_range_km: number;
  max_unamb_velocity_mps: number;
  range_resolution_m: number;
  blind_speeds_mps: number[];
}

export interface ModeInfo {
  description: string;
  num_detections: number;
  num_clutter: number;
  num_targets: number;
}

export interface TWSTrack {
  track_id: string;
  status: "tentative" | "confirmed" | "coasting" | "dropped";
  x: number;
  y: number;
  vx: number;
  vy: number;
  uncertainty: number;
  hits: number;
  misses: number;
  history: [number, number][];
}

export interface RadarFrame {
  type: "frame";
  time: number;
  mode: string;
  detections: Detection[];
  targets: GroundTruthTarget[];
  radar_params: RadarParams;
  mode_info: ModeInfo;
  tracks?: TWSTrack[];
  scan_beam_az?: number;
}

export interface SetModeMessage {
  type: "set_mode";
  mode: string;
}

export interface SetParamMessage {
  type: "set_param";
  param: string;
  value: number;
}

export interface ControlMessage {
  type: "control";
  action: "play" | "pause" | "reset";
}

export type ClientMessage = SetModeMessage | SetParamMessage | ControlMessage;
