// Navigation + import controls beneath the board: step/first/last, flip, and
// PGN/FEN import. Keyboard shortcuts (arrows, f) are wired in the parent page.

interface Props {
  canPrev: boolean;
  canNext: boolean;
  onFirst: () => void;
  onPrev: () => void;
  onNext: () => void;
  onLast: () => void;
  onFlip: () => void;
  onImport: () => void;
}

function IconButton({
  onClick,
  disabled,
  label,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className="btn-ghost h-9 w-9 !px-0 text-base"
    >
      {children}
    </button>
  );
}

export function BoardControls({
  canPrev,
  canNext,
  onFirst,
  onPrev,
  onNext,
  onLast,
  onFlip,
  onImport,
}: Props) {
  return (
    <div className="flex items-center justify-between gap-2">
      <div className="flex items-center gap-1.5">
        <IconButton onClick={onFirst} disabled={!canPrev} label="First move (Home)">
          ⏮
        </IconButton>
        <IconButton onClick={onPrev} disabled={!canPrev} label="Previous move (←)">
          ◀
        </IconButton>
        <IconButton onClick={onNext} disabled={!canNext} label="Next move (→)">
          ▶
        </IconButton>
        <IconButton onClick={onLast} disabled={!canNext} label="Last move (End)">
          ⏭
        </IconButton>
      </div>
      <div className="flex items-center gap-2">
        <button onClick={onFlip} className="btn-ghost" title="Flip board (F)">
          ⇅ Flip
        </button>
        <button onClick={onImport} className="btn-primary" title="Import PGN or FEN">
          Import
        </button>
      </div>
    </div>
  );
}
