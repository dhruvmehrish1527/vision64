// Board state manager built on chess.js.
//
// Maintains the full move history and a cursor into it, so the UI gets step
// forward/back, undo/redo, jump-to-ply, flip, PGN/FEN load, and drag-to-move —
// all the "interactive analysis board" behaviors — from one hook.

import { Chess, type Square } from "chess.js";
import { useCallback, useMemo, useReducer } from "react";

export interface HistoryEntry {
  san: string;
  uci: string;
  fenBefore: string;
  fenAfter: string;
  color: "w" | "b";
  ply: number;
}

interface State {
  history: HistoryEntry[];
  cursor: number; // index into history; -1 = start position
  startFen: string;
  orientation: "white" | "black";
}

type Action =
  | { type: "MOVE"; entry: HistoryEntry }
  | { type: "GO_TO"; cursor: number }
  | { type: "FLIP" }
  | { type: "LOAD"; history: HistoryEntry[]; startFen: string }
  | { type: "RESET"; startFen: string };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "MOVE": {
      // Making a move from a mid-history position truncates the future (redo
      // branch is discarded), matching how analysis boards behave.
      const kept = state.history.slice(0, state.cursor + 1);
      return { ...state, history: [...kept, action.entry], cursor: kept.length };
    }
    case "GO_TO":
      return { ...state, cursor: Math.max(-1, Math.min(action.cursor, state.history.length - 1)) };
    case "FLIP":
      return { ...state, orientation: state.orientation === "white" ? "black" : "white" };
    case "LOAD":
      return { ...state, history: action.history, cursor: action.history.length - 1, startFen: action.startFen };
    case "RESET":
      return { history: [], cursor: -1, startFen: action.startFen, orientation: state.orientation };
    default:
      return state;
  }
}

const START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

export function useChessGame(initialFen: string = START_FEN) {
  const [state, dispatch] = useReducer(reducer, {
    history: [],
    cursor: -1,
    startFen: initialFen,
    orientation: "white",
  });

  // The FEN currently shown is the position after the move at `cursor`.
  const currentFen = useMemo(() => {
    if (state.cursor < 0) return state.startFen;
    return state.history[state.cursor].fenAfter;
  }, [state.cursor, state.history, state.startFen]);

  // A fresh Chess instance positioned at the current FEN (for legality checks).
  const board = useMemo(() => new Chess(currentFen), [currentFen]);

  const makeMove = useCallback(
    (from: Square, to: Square, promotion = "q"): boolean => {
      const game = new Chess(currentFen);
      try {
        const move = game.move({ from, to, promotion });
        if (!move) return false;
        dispatch({
          type: "MOVE",
          entry: {
            san: move.san,
            uci: `${move.from}${move.to}${move.promotion ?? ""}`,
            fenBefore: currentFen,
            fenAfter: game.fen(),
            color: move.color,
            ply: state.cursor + 2,
          },
        });
        return true;
      } catch {
        return false; // illegal move — react-chessboard snaps the piece back
      }
    },
    [currentFen, state.cursor]
  );

  const goTo = useCallback((cursor: number) => dispatch({ type: "GO_TO", cursor }), []);
  const first = useCallback(() => dispatch({ type: "GO_TO", cursor: -1 }), []);
  const prev = useCallback(() => dispatch({ type: "GO_TO", cursor: state.cursor - 1 }), [state.cursor]);
  const next = useCallback(() => dispatch({ type: "GO_TO", cursor: state.cursor + 1 }), [state.cursor]);
  const last = useCallback(
    () => dispatch({ type: "GO_TO", cursor: state.history.length - 1 }),
    [state.history.length]
  );
  const flip = useCallback(() => dispatch({ type: "FLIP" }), []);

  const loadFen = useCallback((fen: string) => {
    const test = new Chess();
    try {
      test.load(fen);
      dispatch({ type: "RESET", startFen: fen });
      return true;
    } catch {
      return false;
    }
  }, []);

  const loadPgn = useCallback((pgn: string) => {
    const game = new Chess();
    try {
      game.loadPgn(pgn);
    } catch {
      return false;
    }
    const verbose = game.history({ verbose: true });
    const replay = new Chess();
    const history: HistoryEntry[] = verbose.map((m, i) => {
      const fenBefore = replay.fen();
      replay.move(m.san);
      return {
        san: m.san,
        uci: `${m.from}${m.to}${m.promotion ?? ""}`,
        fenBefore,
        fenAfter: replay.fen(),
        color: m.color,
        ply: i + 1,
      };
    });
    dispatch({ type: "LOAD", history, startFen: START_FEN });
    return true;
  }, []);

  return {
    ...state,
    currentFen,
    board,
    makeMove,
    goTo,
    first,
    prev,
    next,
    last,
    flip,
    loadFen,
    loadPgn,
    canPrev: state.cursor >= 0,
    canNext: state.cursor < state.history.length - 1,
  };
}
