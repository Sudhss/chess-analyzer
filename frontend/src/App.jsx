import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  Check,
  ChevronsLeft,
  ChevronsRight,
  CircleHelp,
  CircleX,
  Flag,
  Gauge,
  Play,
  Search,
  Sparkles,
  Star,
  StepBack,
  StepForward,
  ThumbsUp,
  Zap,
} from "lucide-react";

const API = "http://127.0.0.1:8000";

const PIECES = {
  P: "♙",
  N: "♘",
  B: "♗",
  R: "♖",
  Q: "♕",
  K: "♔",
  p: "♟",
  n: "♞",
  b: "♝",
  r: "♜",
  q: "♛",
  k: "♚",
};

const QUALITY_ICONS = {
  Brilliant: Sparkles,
  Great: Zap,
  Book: BookOpen,
  Best: Star,
  Excellent: ThumbsUp,
  Good: Check,
  Inaccuracy: CircleHelp,
  Mistake: AlertCircle,
  Miss: CircleX,
  Blunder: AlertCircle,
};

function squareName(file, rank) {
  return `${"abcdefgh"[file]}${rank}`;
}

function parseFen(fen) {
  const board = {};
  const placement = fen.split(" ")[0];
  const rows = placement.split("/");
  rows.forEach((row, rowIndex) => {
    let file = 0;
    const rank = 8 - rowIndex;
    for (const char of row) {
      if (/\d/.test(char)) {
        file += Number(char);
      } else {
        board[squareName(file, rank)] = char;
        file += 1;
      }
    }
  });
  return board;
}

function clampEval(value) {
  return Math.max(-900, Math.min(900, value ?? 0));
}

function formatEval(value) {
  const clamped = clampEval(value);
  const pawns = (clamped / 100).toFixed(2);
  return clamped > 0 ? `+${pawns}` : pawns;
}

function ratingLevel(rating) {
  if (rating >= 2200) return "Master";
  if (rating >= 1800) return "Advanced";
  if (rating >= 1300) return "Club";
  if (rating >= 900) return "Developing";
  return "Learning";
}

function QualityBadge({ quality, compact = false }) {
  const Icon = QUALITY_ICONS[quality] || Check;
  return (
    <span className={`quality-badge ${quality?.toLowerCase()} ${compact ? "compact" : ""}`} title={quality}>
      <Icon size={compact ? 14 : 16} strokeWidth={2.6} />
      {!compact && <span>{quality}</span>}
    </span>
  );
}

function EvalGraph({ graph, moves, current }) {
  const width = 580;
  const height = 112;
  const pad = 8;
  const points = graph.map((point, index) => {
    const x = pad + (index / Math.max(1, graph.length - 1)) * (width - pad * 2);
    const y = height / 2 - (clampEval(point.eval) / 900) * (height / 2 - 14);
    return { x, y, point };
  });
  const area = [
    `M ${pad} ${height / 2}`,
    ...points.map((p) => `L ${p.x} ${p.y}`),
    `L ${width - pad} ${height / 2}`,
    "Z",
  ].join(" ");
  const line = points.map((p) => `${p.x},${p.y}`).join(" ");
  const cursor = points[current] || points[0];

  return (
    <svg className="eval-graph" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Evaluation graph">
      <path d={area} className="graph-area" />
      <line x1={pad} x2={width - pad} y1={height / 2} y2={height / 2} className="zero-line" />
      <polyline points={line} className="graph-line" />
      {moves.map((move, index) => {
        const p = points[index + 1];
        if (!p) return null;
        return <circle key={move.ply} cx={p.x} cy={p.y} r="4" className={`dot ${move.quality?.toLowerCase()}`} />;
      })}
      {cursor && (
        <>
          <line x1={cursor.x} x2={cursor.x} y1={6} y2={height - 6} className="cursor-line" />
          <rect x={Math.min(width - 68, Math.max(8, cursor.x - 31))} y={Math.max(6, cursor.y - 32)} width="62" height="26" rx="4" className="eval-chip" />
          <text x={Math.min(width - 37, Math.max(39, cursor.x))} y={Math.max(23, cursor.y - 14)} textAnchor="middle" className="eval-chip-text">
            {formatEval(cursor.point.eval)}
          </text>
        </>
      )}
    </svg>
  );
}

function ChessBoard({ fen, lastMove, moveQuality, onMove }) {
  const board = useMemo(() => parseFen(fen), [fen]);
  const [selected, setSelected] = useState(null);
  const ranks = [8, 7, 6, 5, 4, 3, 2, 1];
  const files = [0, 1, 2, 3, 4, 5, 6, 7];

  async function handleSquare(square) {
    const piece = board[square];
    if (!selected) {
      if (piece) setSelected(square);
      return;
    }
    if (selected === square) {
      setSelected(null);
      return;
    }
    if (piece && (board[selected] === board[selected]?.toUpperCase()) === (piece === piece.toUpperCase())) {
      setSelected(square);
      return;
    }
    await onMove(`${selected}${square}`);
    setSelected(null);
  }

  return (
    <div className="board-shell">
      <div className="board-grid">
        {ranks.map((rank) =>
          files.map((file) => {
            const square = squareName(file, rank);
            const piece = board[square];
            const light = (file + rank) % 2 === 1;
            const isLastFrom = lastMove?.from === square;
            const isLastTo = lastMove?.to === square;
            const isSelected = selected === square;
            const showBadge = isLastTo && moveQuality;
            return (
              <button
                key={square}
                className={`square ${light ? "light" : "dark"} ${isLastFrom || isLastTo ? "last" : ""} ${isSelected ? "selected" : ""}`}
                onClick={() => handleSquare(square)}
                aria-label={square}
              >
                {file === 0 && <span className="rank-label">{rank}</span>}
                {rank === 1 && <span className="file-label">{"abcdefgh"[file]}</span>}
                {piece && <span className={`piece ${piece === piece.toUpperCase() ? "white-piece" : "black-piece"}`}>{PIECES[piece]}</span>}
                {showBadge && <QualityBadge quality={moveQuality} compact />}
              </button>
            );
          }),
        )}
      </div>
    </div>
  );
}

function PlayerRail({ player, color, top = false }) {
  return (
    <div className={`player-rail ${top ? "top" : ""}`}>
      <div className={`avatar ${color}`}>{color === "white" ? "♙" : "♟"}</div>
      <div>
        <strong>{player?.name || color}</strong>
        <span>({player?.elo || "?"})</span>
      </div>
      <span className="flag">🇮🇳</span>
    </div>
  );
}

function MoveTable({ moves, current, setCurrent }) {
  const rows = [];
  for (let i = 0; i < moves.length; i += 2) {
    rows.push({ number: moves[i].moveNumber, white: moves[i], black: moves[i + 1] });
  }
  return (
    <div className="move-table" role="list">
      {rows.map((row) => (
        <div className="move-row" key={row.number}>
          <span className="move-number">{row.number}.</span>
          {[row.white, row.black].map((move) =>
            move ? (
              <button
                key={move.ply}
                className={`move-pill ${current === move.ply ? "active" : ""}`}
                onClick={() => setCurrent(move.ply)}
              >
                <QualityBadge quality={move.quality} compact />
                <span>{move.san}</span>
              </button>
            ) : (
              <span key="empty" />
            ),
          )}
        </div>
      ))}
    </div>
  );
}

function ReviewPanel({ data, current, setCurrent }) {
  const move = data.moves[current - 1];
  const ordered = data.qualityOrder || [];
  const currentQuality = move?.quality || "Book";
  const currentEval = data.states[current]?.eval ?? data.states[0]?.eval;

  return (
    <aside className="review-panel">
      <header className="panel-title">
        <Star size={19} fill="currentColor" />
        <span>Game Review</span>
        <Search size={18} className="muted-icon" />
      </header>

      <section className="coach">
        <div className="coach-face">
          <div className="hair" />
          <div className="eyes" />
          <div className="smile" />
        </div>
        <div className="speech">
          {move ? (
            <>
              <QualityBadge quality={currentQuality} compact />
              <span>{move.san} is a {currentQuality.toLowerCase()} move</span>
              <b>{formatEval(currentEval)}</b>
            </>
          ) : (
            <span>{data.coach}</span>
          )}
        </div>
      </section>

      <EvalGraph graph={data.graph} moves={data.moves} current={current} />

      <section className="players-card">
        <div className="players-grid">
          <span />
          <strong>{data.players.black.name}</strong>
          <strong>{data.players.white.name}</strong>
          <span>Players</span>
          <div className="portrait black">♟</div>
          <div className="portrait white">♙</div>
          <span>Accuracy</span>
          <b className="score">{data.players.black.accuracy}</b>
          <b className="score">{data.players.white.accuracy}</b>
        </div>
      </section>

      <section className="breakdown">
        {ordered.map((quality) => {
          const Icon = QUALITY_ICONS[quality] || Check;
          return (
            <div className="quality-row" key={quality}>
              <span>{quality}</span>
              <b className={quality.toLowerCase()}>{data.counts.black[quality]}</b>
              <span className={`quality-center ${quality.toLowerCase()}`}>
                <Icon size={16} />
              </span>
              <b className={quality.toLowerCase()}>{data.counts.white[quality]}</b>
            </div>
          );
        })}
      </section>

      <section className="rating-panel">
        <div className="rating-row">
          <span>Game Rating</span>
          <b>{data.players.black.rating}</b>
          <b>{data.players.white.rating}</b>
        </div>
        <div className="rating-row level">
          <span>Level</span>
          <em>{ratingLevel(data.players.black.rating)}</em>
          <em>{ratingLevel(data.players.white.rating)}</em>
        </div>
        {["opening", "middlegame", "endgame"].map((phase) => (
          <div className="rating-row" key={phase}>
            <span>{phase[0].toUpperCase() + phase.slice(1)}</span>
            <QualityMini value={data.phases.black[phase]} />
            <QualityMini value={data.phases.white[phase]} />
          </div>
        ))}
      </section>

      <MoveTable moves={data.moves} current={current} setCurrent={setCurrent} />
    </aside>
  );
}

function QualityMini({ value }) {
  if (value === "-") return <span className="dash">-</span>;
  const map = {
    thumb: ThumbsUp,
    "!": Zap,
    "?!": CircleHelp,
    "?": AlertCircle,
  };
  const Icon = map[value] || Check;
  return (
    <span className={`phase-icon v-${value.replace(/[?!]/g, "warn")}`}>
      <Icon size={15} />
    </span>
  );
}

function Controls({ current, max, setCurrent, playing, setPlaying }) {
  return (
    <div className="controls">
      <button onClick={() => setCurrent(0)} aria-label="First move">
        <ChevronsLeft />
      </button>
      <button onClick={() => setCurrent(Math.max(0, current - 1))} aria-label="Previous move">
        <StepBack />
      </button>
      <button className="play" onClick={() => setPlaying(!playing)} aria-label="Play">
        <Play fill="currentColor" />
      </button>
      <button onClick={() => setCurrent(Math.min(max, current + 1))} aria-label="Next move">
        <StepForward />
      </button>
      <button onClick={() => setCurrent(max)} aria-label="Last move">
        <ChevronsRight />
      </button>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [pgn, setPgn] = useState("");
  const [current, setCurrent] = useState(0);
  const [loading, setLoading] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [sandbox, setSandbox] = useState(null);
  const [error, setError] = useState("");
  const moveListRef = useRef(null);

  async function analyze(nextPgn = pgn) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pgn: nextPgn }),
      });
      const result = await response.json();
      setData(result);
      setPgn(nextPgn || result.samplePgn);
      setCurrent(0);
      setSandbox(null);
    } catch (err) {
      setError("The analyzer service is not running.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    analyze("");
  }, []);

  useEffect(() => {
    function onKey(event) {
      if (event.target?.tagName === "TEXTAREA") return;
      if (event.key === "ArrowLeft") {
        setSandbox(null);
        setCurrent((value) => Math.max(0, value - 1));
      }
      if (event.key === "ArrowRight") {
        setSandbox(null);
        setCurrent((value) => Math.min((data?.states.length || 1) - 1, value + 1));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [data]);

  useEffect(() => {
    if (!playing || !data) return undefined;
    const timer = setInterval(() => {
      setCurrent((value) => {
        if (value >= data.states.length - 1) {
          setPlaying(false);
          return value;
        }
        return value + 1;
      });
    }, 650);
    return () => clearInterval(timer);
  }, [playing, data]);

  useEffect(() => {
    setSandbox(null);
    moveListRef.current?.querySelector(".active")?.scrollIntoView({ block: "nearest" });
  }, [current]);

  async function makeBoardMove(uci) {
    if (!data) return;
    const fen = sandbox?.fen || data.states[current]?.fen;
    const response = await fetch(`${API}/api/analyze-move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fen, uci }),
    });
    const result = await response.json();
    if (result.legal) {
      setSandbox(result);
      setPlaying(false);
    }
  }

  if (loading) {
    return (
      <main className="loading-screen">
        <Gauge size={42} />
        <span>Analyzing game</span>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="loading-screen error">
        <AlertCircle size={42} />
        <span>{error || "Unable to load the review."}</span>
      </main>
    );
  }

  const state = data.states[current];
  const displayFen = sandbox?.fen || state.fen;
  const displayLastMove = sandbox?.lastMove || state.lastMove;
  const currentMove = data.moves[current - 1];
  const moveQuality = sandbox?.quality || currentMove?.quality;

  return (
    <main className="app">
      <section className="board-column">
        <PlayerRail player={data.players.black} color="black" top />
        <div className="board-area">
          <ChessBoard fen={displayFen} lastMove={displayLastMove} moveQuality={moveQuality} onMove={makeBoardMove} />
          <div className="clock top-clock">
            <span>◷</span>
            <b>3:00</b>
          </div>
          <div className="eval-strip">
            <span>{formatEval(data.states[current]?.eval)}</span>
          </div>
        </div>
        <PlayerRail player={data.players.white} color="white" />
      </section>

      <section className="review-column">
        <div className="pgn-bar">
          <textarea value={pgn} onChange={(event) => setPgn(event.target.value)} spellCheck="false" aria-label="PGN" />
          <button onClick={() => analyze(pgn)}>
            <Flag size={17} />
            Analyze PGN
          </button>
        </div>
        {sandbox?.message && (
          <div className="sandbox-note">
            <QualityBadge quality={sandbox.quality} compact />
            <span>{sandbox.message}</span>
            <b>{formatEval(sandbox.eval)}</b>
          </div>
        )}
        <div ref={moveListRef}>
          <ReviewPanel data={data} current={current} setCurrent={setCurrent} />
        </div>
        <Controls current={current} max={data.states.length - 1} setCurrent={setCurrent} playing={playing} setPlaying={setPlaying} />
      </section>
    </main>
  );
}
