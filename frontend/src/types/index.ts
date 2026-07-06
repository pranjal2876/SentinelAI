// Shared TypeScript types mirroring the backend API schemas.

export type Severity = 'low' | 'medium' | 'high' | 'critical';

export type CameraStatus = 'online' | 'offline' | 'error' | 'connecting';

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: 'admin' | 'operator' | 'viewer';
  is_active: boolean;
}

export interface Camera {
  id: number;
  camera_id: string;
  name: string;
  location: string;
  source: string;
  enabled: boolean;
  status: CameraStatus;
  fps: number;
  conf_threshold: number;
}

export interface Threat {
  id: number;
  camera_id: string;
  category: string;
  severity: Severity;
  score: number;
  message: string;
  timestamp: number;
  track_ids: number[];
  bbox: number[] | null;
  snapshot_path: string | null;
  clip_path: string | null;
  event_metadata: Record<string, unknown>;
  acknowledged: boolean;
}

export interface LiveThreat {
  type: 'threat';
  camera_id: string;
  category: string;
  severity: Severity;
  score: number;
  message: string;
  timestamp: number;
  metadata: Record<string, unknown>;
}

export interface DashboardStats {
  total_threats: number;
  threats_today: number;
  active_cameras: number;
  total_cameras: number;
  by_category: { category: string; count: number }[];
  by_severity: { severity: string; count: number }[];
  by_camera: Record<string, number>;
  timeline: { bucket: string; count: number }[];
}

export interface Zone {
  id: number;
  zone_id: string;
  camera_id: string;
  name: string;
  type: string;
  points: [number, number][];
  allowed_direction: [number, number] | null;
  enabled: boolean;
}

export interface ThreatExplanation {
  category: string;
  severity: Severity;
  confidence: number;
  why: string;
  message: string;
  contributing_factors: { factor: string; value: unknown }[];
  tracks_involved: number[];
}
