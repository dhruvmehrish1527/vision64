// TypeScript types mirroring the backend Pydantic schemas. Keeping these in one
// place means the API contract is legible and changes are caught at compile time.

export type MoveClassification =
  | "Brilliant"
  | "Great"
  | "Excellent"
  | "Good"
  | "Book"
  | "Interesting"
  | "Inaccuracy"
  | "Mistake"
  | "Blunder";

export interface Candidate {
  move_uci: string;
  move_san: string;
  eval_cp: number | null;
  mate_in: number | null;
  pv: string[];
}

export interface EngineResult {
  fen: string;
  depth: number;
  eval_cp: number | null;
  mate_in: number | null;
  best_move: string | null;
  best_move_san: string | null;
  pv: string[];
  candidates: Candidate[];
}

export interface Classification {
  classification: MoveClassification;
  centipawn_loss: number;
  tags: string[];
}

export interface PositionResponse {
  engine: EngineResult;
  explanation: string | null;
}

export interface ExplainMoveResponse {
  engine: EngineResult;
  classification: Classification;
  explanation: string;
}

export interface UserProfile {
  id: number;
  display_name: string | null;
  email: string | null;
  rating: number;
  puzzle_rating: number;
  streak_days: number;
}

export interface Dashboard {
  rating: number;
  puzzle_rating: number;
  streak_days: number;
  training_minutes: number;
  games_analyzed: number;
  puzzle_accuracy: number | null;
  average_accuracy: number | null;
  top_weaknesses: { pattern: string; count: number }[];
}

// ---- Puzzles ----

export interface Puzzle {
  id: number;
  fen: string;
  theme: string;
  rating: number;
  side_to_move: "white" | "black";
  player_move_count: number;
}

export interface PuzzleMoveResult {
  correct: boolean;
  solved: boolean;
  opponent_reply_uci: string | null;
  solution_uci: string[] | null;
  new_puzzle_rating: number | null;
}

// ---- Openings ----

export interface Opening {
  eco: string;
  name: string;
  moves: string[];
  white_win: number;
  draw: number;
  black_win: number;
  plans: string[];
  mistakes: string[];
  famous: string[];
}

export interface RepertoireItem {
  id: number;
  eco: string;
  name: string;
  color: "white" | "black";
  note: string | null;
}

// ---- AI opponent ----

export interface AiLevel {
  key: string;
  label: string;
  elo: number;
  blurb: string;
}

export interface AiGameState {
  game_id: number;
  fen: string;
  status: "in_progress" | "checkmate" | "stalemate" | "draw";
  result: string | null;
  player_color: "white" | "black";
  level: string;
  moves_san: string[];
  last_move_uci: string | null;
  your_turn: boolean;
}

export interface GameFeedback {
  accuracy: number;
  summary: string;
  biggest_mistake_ply: number | null;
  weakness_tags: Record<string, number>;
}

// ---- Training plan ----

export interface TrainingWeek {
  id: number;
  week_number: number;
  goal: string | null;
  focus_topics: string[];
  completed: boolean;
  puzzle_theme: string | null;
}

export interface TrainingPlan {
  id: number;
  title: string;
  weeks: TrainingWeek[];
  progress_percent: number;
}

// ---- Game review ----

export interface ReviewedMove {
  ply: number;
  color: string;
  san: string;
  uci: string;
  fen_before: string | null;
  eval_cp: number | null;
  mate_in: number | null;
  best_move: string | null;
  best_pv: string[];
  classification: MoveClassification;
  centipawn_loss: number;
  tags: string[];
}

export interface GameReview {
  game: {
    id: number;
    white: string | null;
    black: string | null;
    result: string | null;
    source: string;
    accuracy_white: number | null;
    accuracy_black: number | null;
  };
  accuracy_white: number;
  accuracy_black: number;
  biggest_mistake_ply: number | null;
  turning_points: number[];
  phases: Record<string, { move_count: number; avg_cp_loss: number; labels: Record<string, number> }>;
  weakness_tags: Record<string, number>;
  moves: ReviewedMove[];
}
