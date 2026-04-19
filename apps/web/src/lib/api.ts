import type {
  P2PRequest,
  P2PResponse,
  CoverageRequest,
  CoverageResponse,
  CoverageRadiusResponse,
} from "./types";

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Server error ${res.status}: ${text.substring(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

export function postP2P(req: P2PRequest, signal?: AbortSignal): Promise<P2PResponse> {
  return post<P2PResponse>("/api/p2p", req, signal);
}

export function postCoverage(req: CoverageRequest, signal?: AbortSignal): Promise<CoverageResponse> {
  return post<CoverageResponse>("/api/coverage", req, signal);
}

export function postCoverageRadius(
  req: CoverageRequest,
  signal?: AbortSignal
): Promise<CoverageRadiusResponse> {
  return post<CoverageRadiusResponse>("/api/coverage-radius", req, signal);
}
