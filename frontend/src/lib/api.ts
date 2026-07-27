// Thin, typed API client. A single `request()` helper attaches the Clerk JWT
// (when available) and centralizes error handling; the exported functions are
// the only surface the UI touches.

import type {
  AccuracyPoint,
  AiGameState,
  AiLevel,
  Classification,
  Dashboard,
  PublicProfile,
  SharedGame,
  GameFeedback,
  ExplainMoveResponse,
  GameReview,
  Opening,
  PositionResponse,
  Puzzle,
  PuzzleMoveResult,
  RepertoireItem,
  TrainingPlan,
  UserProfile,
} from "@/types";

const BASE = import.meta.env.VITE_API_URL ?? "/api";

// The Clerk `getToken` function is injected at runtime by AuthProvider so this
// module has no hard dependency on Clerk (keeps dev-bypass simple).
let tokenGetter: (() => Promise<string | null>) | null = null;

export function setTokenGetter(fn: () => Promise<string | null>) {
  tokenGetter = fn;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  if (tokenGetter) {
    const token = await tokenGetter();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const detail = await res
      .json()
      .then((b) => b.detail ?? res.statusText)
      .catch(() => res.statusText);
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  me: () => request<UserProfile>("/users/me"),

  dashboard: () => request<Dashboard>("/users/me/dashboard"),

  analysePosition: (fen: string, opts?: { multipv?: number; depth?: number }) =>
    request<PositionResponse>("/analysis/position", {
      method: "POST",
      body: JSON.stringify({
        fen,
        multipv: opts?.multipv ?? 5,
        depth: opts?.depth,
      }),
    }),

  explainMove: (fenBefore: string, moveUci: string, rating: number) =>
    request<ExplainMoveResponse>("/analysis/explain-move", {
      method: "POST",
      body: JSON.stringify({ fen_before: fenBefore, move_uci: moveUci, rating }),
    }),

  explainPosition: (fen: string, rating: number) =>
    request<{ explanation: string }>("/analysis/explain-position", {
      method: "POST",
      body: JSON.stringify({ fen, rating }),
    }),

  importGame: (pgn: string, depth = 14) =>
    request<GameReview>("/games/import", {
      method: "POST",
      body: JSON.stringify({ pgn, review: true, depth }),
    }),

  generatePuzzlesFromGame: (gameId: number) =>
    request<{ created: number }>("/puzzles/generate-from-game", {
      method: "POST",
      body: JSON.stringify({ game_id: gameId }),
    }),

  nextPuzzle: (theme?: string) =>
    request<Puzzle>(`/puzzles/next${theme ? `?theme=${theme}` : ""}`),

  submitPuzzleMove: (
    puzzleId: number,
    playerMoveIndex: number,
    uci: string,
    timeMs?: number
  ) =>
    request<PuzzleMoveResult>(`/puzzles/${puzzleId}/move`, {
      method: "POST",
      body: JSON.stringify({ player_move_index: playerMoveIndex, uci, time_ms: timeMs }),
    }),

  accuracyTrend: () => request<AccuracyPoint[]>("/users/me/accuracy-trend"),

  shareGame: (gameId: number) =>
    request<{ share_token: string; url_path: string }>(
      `/social/games/${gameId}/share`,
      { method: "POST" }
    ),

  viewShared: (token: string) => request<SharedGame>(`/social/shared/${token}`),

  players: () => request<PublicProfile[]>("/social/players"),

  follow: async (userId: number, on: boolean) => {
    const headers = new Headers();
    if (tokenGetter) {
      const token = await tokenGetter();
      if (token) headers.set("Authorization", `Bearer ${token}`);
    }
    const res = await fetch(`${BASE}/social/follow/${userId}`, {
      method: on ? "POST" : "DELETE",
      headers,
    });
    if (!res.ok) throw new ApiError(res.status, res.statusText);
  },

  searchOpenings: (q: string) =>
    request<Opening[]>(`/openings?q=${encodeURIComponent(q)}&limit=40`),

  identifyOpening: (movesSan: string[]) =>
    request<{ opening: Opening | null; continuations: { move: string; eco: string; name: string }[] }>(
      "/openings/identify",
      { method: "POST", body: JSON.stringify({ moves_san: movesSan }) }
    ),

  repertoire: () => request<RepertoireItem[]>("/openings/me/repertoire"),

  saveOpening: (eco: string, color: "white" | "black") =>
    request<RepertoireItem>("/openings/me/repertoire", {
      method: "POST",
      body: JSON.stringify({ eco, color }),
    }),

  removeOpening: async (id: number) => {
    const headers = new Headers();
    if (tokenGetter) {
      const token = await tokenGetter();
      if (token) headers.set("Authorization", `Bearer ${token}`);
    }
    const res = await fetch(`${BASE}/openings/me/repertoire/${id}`, {
      method: "DELETE",
      headers,
    });
    if (!res.ok) throw new ApiError(res.status, res.statusText);
  },

  aiLevels: () => request<AiLevel[]>("/ai/levels"),

  newAiGame: (level: string, playAs: "white" | "black") =>
    request<AiGameState>("/ai/games", {
      method: "POST",
      body: JSON.stringify({ level, play_as: playAs }),
    }),

  playAiMove: (gameId: number, uci: string) =>
    request<AiGameState>(`/ai/games/${gameId}/move`, {
      method: "POST",
      body: JSON.stringify({ uci }),
    }),

  aiGameFeedback: (gameId: number) =>
    request<GameFeedback>(`/ai/games/${gameId}/feedback`, { method: "POST" }),

  trainingPlan: () => request<TrainingPlan>("/training/plan"),

  regeneratePlan: () =>
    request<TrainingPlan>("/training/plan/regenerate", { method: "POST" }),

  completeWeek: (weekId: number) =>
    request<TrainingPlan>(`/training/weeks/${weekId}/complete`, { method: "POST" }),
};

// ---- Streaming coach (SSE) ----
//
// Consumes the /stream endpoints: `onMeta` fires with the classification, `onText`
// fires for each streamed chunk, `onError` for a coach failure. Returns a promise
// that resolves when the stream is done.

export interface StreamHandlers {
  onMeta?: (c: Classification) => void;
  onText?: (chunk: string) => void;
  onError?: (message: string) => void;
}

async function streamSSE(path: string, body: unknown, handlers: StreamHandlers): Promise<void> {
  const headers = new Headers({ "Content-Type": "application/json" });
  if (tokenGetter) {
    const token = await tokenGetter();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${BASE}${path}`, { method: "POST", headers, body: JSON.stringify(body) });
  if (!res.ok || !res.body) {
    const detail = await res.json().then((b) => b.detail).catch(() => res.statusText);
    throw new ApiError(res.status, detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // Parse the SSE stream frame-by-frame (frames separated by a blank line).
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      let event: string | null = null;
      let data = "";
      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (!data) continue;
      if (event === "meta") handlers.onMeta?.(JSON.parse(data));
      else if (event === "error") handlers.onError?.(JSON.parse(data));
      else if (event === "done") return;
      else handlers.onText?.(JSON.parse(data));
    }
  }
}

export const coachStream = {
  move: (fenBefore: string, moveUci: string, rating: number, h: StreamHandlers) =>
    streamSSE("/analysis/explain-move/stream", { fen_before: fenBefore, move_uci: moveUci, rating }, h),
  position: (fen: string, rating: number, h: StreamHandlers) =>
    streamSSE("/analysis/explain-position/stream", { fen, rating }, h),
};
