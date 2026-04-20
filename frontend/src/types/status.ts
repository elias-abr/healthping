/**
 * Types mirroring the healthping backend API.
 *
 * Keep this file in sync with backend/src/healthping/models.py
 * and backend/src/healthping/api.py.
 */

export type CheckStatus = "up" | "down";

export interface CheckResult {
  endpoint_name: string;
  url: string;
  status: CheckStatus;
  response_time_ms: number | null;
  http_status: number | null;
  error: string | null;
  timestamp: string;
}

export interface StatusResponse {
  started_at: string;
  now: string;
  endpoints: CheckResult[];
}
