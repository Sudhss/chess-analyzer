from __future__ import annotations

import io
import math
import re
from dataclasses import dataclass
from typing import Any

import chess
import chess.pgn

try:
    from .sample_pgn import SAMPLE_PGN
except ImportError:
    from sample_pgn import SAMPLE_PGN


QUALITY_ORDER = [
    "Brilliant",
    "Great",
    "Book",
    "Best",
    "Excellent",
    "Good",
    "Inaccuracy",
    "Mistake",
    "Miss",
    "Blunder",
]

QUALITY_META = {
    "Brilliant": {"icon": "!!", "tone": "brilliant", "cp": 0},
    "Great": {"icon": "!", "tone": "great", "cp": 18},
    "Book": {"icon": "book", "tone": "book", "cp": 0},
    "Best": {"icon": "star", "tone": "best", "cp": 12},
    "Excellent": {"icon": "thumb", "tone": "excellent", "cp": 32},
    "Good": {"icon": "check", "tone": "good", "cp": 65},
    "Inaccuracy": {"icon": "?!", "tone": "inaccuracy", "cp": 130},
    "Mistake": {"icon": "?", "tone": "mistake", "cp": 260},
    "Miss": {"icon": "x", "tone": "miss", "cp": 360},
    "Blunder": {"icon": "??", "tone": "blunder", "cp": 550},
}

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 335,
    chess.ROOK: 500,
    chess.QUEEN: 920,
    chess.KING: 0,
}

PIECE_SQUARES = {
    chess.PAWN: [0, 5, 8, -4, -8, 10, 32, 0],
    chess.KNIGHT: [-45, -20, 8, 16, 16, 8, -20, -45],
    chess.BISHOP: [-20, 0, 8, 12, 12, 8, 0, -20],
    chess.ROOK: [0, 4, 8, 10, 10, 8, 4, 0],
    chess.QUEEN: [-8, 0, 6, 10, 10, 6, 0, -8],
    chess.KING: [18, 12, 2, -8, -8, 2, 12, 18],
}


@dataclass
class Candidate:
    move: chess.Move
    san: str
    eval_after: int
    quality: str
    loss: int


def clean_pgn(pgn: str) -> str:
    text = (pgn or SAMPLE_PGN).strip()
    if text.count("{") > text.count("}"):
        text = text[: text.rfind("{")]
    text = re.sub(r"\{[^{}]*\}", " ", text)
    text = re.sub(r";[^\n\r]*", " ", text)
    text = re.sub(r"\[%[^\]]*", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(\])\s+", r"\1\n", text)
    return text.strip()


def parse_game(pgn: str) -> chess.pgn.Game:
    cleaned = clean_pgn(pgn)
    game = chess.pgn.read_game(io.StringIO(cleaned))
    if game is None:
        game = chess.pgn.read_game(io.StringIO(clean_pgn(SAMPLE_PGN)))
    return game


def piece_square_bonus(piece_type: chess.PieceType, square: chess.Square, color: chess.Color) -> int:
    rank = chess.square_rank(square)
    file = chess.square_file(square)
    rank_for_color = rank if color == chess.WHITE else 7 - rank
    file_center = 3.5 - abs(3.5 - file)
    table = PIECE_SQUARES[piece_type]
    return table[rank_for_color] + int(file_center * 4)


def evaluate_white(board: chess.Board) -> int:
    if board.is_checkmate():
        return -100000 if board.turn == chess.WHITE else 100000
    if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
        return 0

    score = 0
    for square, piece in board.piece_map().items():
        sign = 1 if piece.color == chess.WHITE else -1
        score += sign * PIECE_VALUES[piece.piece_type]
        score += sign * piece_square_bonus(piece.piece_type, square, piece.color)

    turn = board.turn
    board.turn = chess.WHITE
    white_mobility = board.legal_moves.count()
    board.turn = chess.BLACK
    black_mobility = board.legal_moves.count()
    board.turn = turn

    score += int((white_mobility - black_mobility) * 2.5)
    if board.has_kingside_castling_rights(chess.WHITE) or board.has_queenside_castling_rights(chess.WHITE):
        score += 8
    if board.has_kingside_castling_rights(chess.BLACK) or board.has_queenside_castling_rights(chess.BLACK):
        score -= 8
    if board.is_check():
        score += -22 if board.turn == chess.WHITE else 22
    return score


def move_order_key(board: chess.Board, move: chess.Move) -> int:
    score = 0
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        if victim and attacker:
            score += 10 * PIECE_VALUES[victim.piece_type] - PIECE_VALUES[attacker.piece_type]
        else:
            score += 250
    if move.promotion:
        score += PIECE_VALUES.get(move.promotion, 0)
    board.push(move)
    if board.is_check():
        score += 80
    board.pop()
    return score


def search(board: chess.Board, depth: int, alpha: int = -120000, beta: int = 120000) -> int:
    if depth <= 0 or board.is_game_over(claim_draw=True):
        return evaluate_white(board)

    moves = sorted(board.legal_moves, key=lambda move: move_order_key(board, move), reverse=True)
    if board.turn == chess.WHITE:
        value = -120000
        for move in moves:
            board.push(move)
            value = max(value, search(board, depth - 1, alpha, beta))
            board.pop()
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    value = 120000
    for move in moves:
        board.push(move)
        value = min(value, search(board, depth - 1, alpha, beta))
        board.pop()
        beta = min(beta, value)
        if alpha >= beta:
            break
    return value


def is_book_move(board: chess.Board, san: str, ply_index: int) -> bool:
    if ply_index > 12:
        return False
    key = " ".join(board.move_stack_uci()) if hasattr(board, "move_stack_uci") else None
    fen_key = board.board_fen()
    common_by_position = {
        chess.Board().board_fen(): {"e4", "d4", "Nf3", "c4"},
    }
    if fen_key in common_by_position and san in common_by_position[fen_key]:
        return True
    common_opening_sans = {"e4", "d4", "Nf3", "c4", "e5", "c5", "e6", "c6", "Nf6", "d5", "Nc3", "Bb5", "Bc4", "O-O"}
    return san in common_opening_sans and ply_index <= 8 and key is None


def classify_move(
    board: chess.Board,
    move: chess.Move,
    san: str,
    best_eval: int,
    actual_eval: int,
    ply_index: int,
) -> tuple[str, int]:
    mover = board.turn
    loss = max(0, best_eval - actual_eval) if mover == chess.WHITE else max(0, actual_eval - best_eval)

    board.push(move)
    gives_check = board.is_check()
    board.pop()
    is_capture = board.is_capture(move)
    moved_piece = board.piece_at(move.from_square)
    is_sacrifice = False
    if moved_piece and moved_piece.piece_type in (chess.BISHOP, chess.KNIGHT, chess.ROOK, chess.QUEEN):
        defenders_before = len(board.attackers(mover, move.to_square))
        attackers_before = len(board.attackers(not mover, move.to_square))
        is_sacrifice = attackers_before > defenders_before and not is_capture

    if is_book_move(board, san, ply_index):
        return "Book", loss
    if loss <= 20 and (is_sacrifice or (gives_check and is_capture and abs(actual_eval - evaluate_white(board)) > 120)):
        return "Brilliant", loss
    if loss <= 25 and (gives_check or is_capture):
        return "Great", loss
    if loss <= 15:
        return "Best", loss
    if loss <= 45:
        return "Excellent", loss
    if loss <= 90:
        return "Good", loss
    if loss <= 180:
        return "Inaccuracy", loss
    if loss <= 330:
        return "Mistake", loss
    if abs(best_eval) > 750 and loss > 280:
        return "Miss", loss
    return "Blunder", loss


def top_candidates(board: chess.Board, depth: int = 1, limit: int = 4) -> tuple[list[Candidate], int]:
    candidates: list[Candidate] = []
    legal = list(board.legal_moves)
    if not legal:
        return candidates, evaluate_white(board)
    evals: list[tuple[chess.Move, str, int]] = []
    for move in legal:
        san = board.san(move)
        board.push(move)
        ev = search(board, depth - 1)
        board.pop()
        evals.append((move, san, ev))
    best_eval = max(ev for _, _, ev in evals) if board.turn == chess.WHITE else min(ev for _, _, ev in evals)
    for move, san, ev in evals:
        quality, loss = classify_move(board, move, san, best_eval, ev, board.ply() + 1)
        candidates.append(Candidate(move, san, ev, quality, loss))
    reverse = board.turn == chess.WHITE
    candidates.sort(key=lambda item: item.eval_after, reverse=reverse)
    return candidates[:limit], best_eval


def accuracy_from_losses(losses: list[int]) -> float:
    if not losses:
        return 100.0
    values = []
    for loss in losses:
        values.append(100 * math.exp(-loss / 230))
    return round(sum(values) / len(values), 1)


def rating_from_accuracy(accuracy: float, total_moves: int, decisive_score: int) -> int:
    phase_bonus = min(180, total_moves * 3)
    confidence = min(140, abs(decisive_score) // 8)
    return int(round((350 + accuracy * 14.2 + phase_bonus + confidence) / 50) * 50)


def segment_verdict(acc: float | None) -> str:
    if acc is None:
        return "-"
    if acc >= 90:
        return "thumb"
    if acc >= 75:
        return "!"
    if acc >= 55:
        return "?!"
    return "?"


def analyze_pgn(pgn: str | None = None) -> dict[str, Any]:
    game = parse_game(pgn or SAMPLE_PGN)
    board = game.board()
    headers = dict(game.headers)
    states = [{"ply": 0, "fen": board.fen(), "eval": search(board, 1), "lastMove": None}]
    moves: list[dict[str, Any]] = []
    counts = {
        "white": {key: 0 for key in QUALITY_ORDER},
        "black": {key: 0 for key in QUALITY_ORDER},
    }
    losses = {"white": [], "black": []}
    phase_losses = {
        "white": {"opening": [], "middlegame": [], "endgame": []},
        "black": {"opening": [], "middlegame": [], "endgame": []},
    }

    for ply_index, move in enumerate(game.mainline_moves(), start=1):
        if move not in board.legal_moves:
            break
        mover_key = "white" if board.turn == chess.WHITE else "black"
        move_number = board.fullmove_number
        san = board.san(move)
        candidates, best_eval = top_candidates(board, 1, 4)
        candidate = next((item for item in candidates if item.move == move), None)
        if candidate is None:
            board.push(move)
            actual_eval = search(board, 0)
            board.pop()
            quality, loss = classify_move(board, move, san, best_eval, actual_eval, ply_index)
            candidate = Candidate(move, san, actual_eval, quality, loss)

        quality = candidate.quality
        counts[mover_key][quality] += 1
        losses[mover_key].append(candidate.loss)
        phase = "opening" if ply_index <= 20 else "middlegame" if ply_index <= 60 else "endgame"
        phase_losses[mover_key][phase].append(candidate.loss)

        before_fen = board.fen()
        board.push(move)
        after_eval = search(board, 1)
        last_move = {
            "from": chess.square_name(move.from_square),
            "to": chess.square_name(move.to_square),
            "promotion": chess.piece_symbol(move.promotion).upper() if move.promotion else None,
        }
        states.append({"ply": ply_index, "fen": board.fen(), "eval": after_eval, "lastMove": last_move})
        moves.append(
            {
                "ply": ply_index,
                "moveNumber": move_number,
                "side": mover_key,
                "san": san,
                "uci": move.uci(),
                "beforeFen": before_fen,
                "afterFen": board.fen(),
                "quality": quality,
                "loss": candidate.loss,
                "evalBefore": best_eval,
                "evalAfter": after_eval,
                "best": [{"san": c.san, "uci": c.move.uci(), "eval": c.eval_after, "quality": c.quality} for c in candidates],
                "lastMove": last_move,
            }
        )

    white_acc = accuracy_from_losses(losses["white"])
    black_acc = accuracy_from_losses(losses["black"])
    final_eval = states[-1]["eval"] if states else 0

    phase_summary: dict[str, dict[str, str]] = {"white": {}, "black": {}}
    for side in ("white", "black"):
        for phase in ("opening", "middlegame", "endgame"):
            phase_summary[side][phase] = segment_verdict(
                accuracy_from_losses(phase_losses[side][phase]) if phase_losses[side][phase] else None
            )

    best_moments = sorted(moves, key=lambda item: (item["quality"] in ("Brilliant", "Great", "Best"), -item["loss"]), reverse=True)
    if best_moments:
        moment = best_moments[0]
        coach = f"{moment['san']} was a {moment['quality'].lower()} move. Let's review the turning points."
    else:
        coach = "Paste a PGN and start the review."

    return {
        "headers": headers,
        "players": {
            "white": {
                "name": headers.get("White", "White"),
                "elo": headers.get("WhiteElo", "?"),
                "accuracy": white_acc,
                "rating": rating_from_accuracy(white_acc, len(losses["white"]), final_eval),
            },
            "black": {
                "name": headers.get("Black", "Black"),
                "elo": headers.get("BlackElo", "?"),
                "accuracy": black_acc,
                "rating": rating_from_accuracy(black_acc, len(losses["black"]), -final_eval),
            },
        },
        "result": headers.get("Result", "*"),
        "moves": moves,
        "states": states,
        "counts": counts,
        "qualityMeta": QUALITY_META,
        "qualityOrder": QUALITY_ORDER,
        "phases": phase_summary,
        "graph": [{"ply": state["ply"], "eval": max(-900, min(900, state["eval"]))} for state in states],
        "coach": coach,
        "samplePgn": SAMPLE_PGN,
    }


def analyze_single_move(fen: str, uci: str) -> dict[str, Any]:
    board = chess.Board(fen)
    move = chess.Move.from_uci(uci)
    if move not in board.legal_moves:
        if len(uci) == 4:
            promotion = chess.QUEEN
            promoted = chess.Move.from_uci(uci + "q")
            if promoted in board.legal_moves:
                move = promoted
            else:
                return {"legal": False, "message": "That move is not legal in this position."}
        else:
            return {"legal": False, "message": "That move is not legal in this position."}
    san = board.san(move)
    candidates, best_eval = top_candidates(board, 1, 4)
    candidate = next((item for item in candidates if item.move == move), None)
    if candidate is None:
        board.push(move)
        actual_eval = search(board, 0)
        board.pop()
        quality, loss = classify_move(board, move, san, best_eval, actual_eval, board.ply() + 1)
    else:
        quality, loss, actual_eval = candidate.quality, candidate.loss, candidate.eval_after
    board.push(move)
    return {
        "legal": True,
        "fen": board.fen(),
        "san": san,
        "uci": move.uci(),
        "quality": quality,
        "loss": loss,
        "eval": actual_eval,
        "lastMove": {"from": chess.square_name(move.from_square), "to": chess.square_name(move.to_square)},
        "message": f"{san} is a {quality.lower()} move",
    }
