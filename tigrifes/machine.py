"""Modelo da seção 5 do trabalho, independente da interface e sem estado global."""

from dataclasses import dataclass
from random import Random

SYMBOLS = ("A", "B", "C", "D", "E")
PAYOUTS = {"A": 5, "B": 10, "C": 15, "D": 25, "E": 50}
BET = 1
INITIAL_BALANCE = 100
MAX_ROUNDS = 500


@dataclass(frozen=True)
class Round:
    stops: tuple[int, int, int]
    board: tuple[tuple[str, ...], ...]  # Linhas: topo, centro, base.
    prize: int

    @property
    def center(self):
        return self.board[1]

    @property
    def profit(self):
        return self.prize - BET

    def as_dict(self):
        return {"stops": self.stops, "board": self.board, "center": self.center,
                "prize": self.prize, "profit": self.profit}


def from_stops(stops: tuple[int, int, int]) -> Round:
    if len(stops) != 3 or any(type(k) is not int or not 0 <= k < 5 for k in stops):
        raise ValueError("São necessárias três paradas inteiras entre 0 e 4.")
    board = tuple(tuple(SYMBOLS[(k + row) % 5] for k in stops) for row in range(3))
    center = board[1]
    prize = PAYOUTS[center[0]] if center[0] == center[1] == center[2] else 0
    return Round(tuple(stops), board, prize)


def spin(rng: Random) -> Round:
    """O chamador inicializa o gerador uma vez e conserva seu estado."""
    return from_stops(tuple(rng.randrange(5) for _ in range(3)))


def simulate(count: int, seed: int) -> list[Round]:
    rng = Random(seed)
    return [spin(rng) for _ in range(count)]


def conditional_prizes(rounds: list[Round]) -> list[dict]:
    rows = []
    for previous_prize, label in ((False, "Após rodada sem prêmio"), (True, "Após prêmio")):
        pairs = [(a, b) for a, b in zip(rounds, rounds[1:]) if (a.prize > 0) == previous_prize]
        winners = sum(b.prize > 0 for _, b in pairs)
        rows.append({"previous": label, "pairs": len(pairs), "prizes": winners,
                     "proportion": winners / len(pairs) if pairs else None})
    return rows


def simulate_participants(rng: Random, count=100, balance=100, limit=500):
    """Um único gerador continua entre participantes; sem reposição de saldo."""
    sessions = []
    for participant in range(1, count + 1):
        current = balance
        trajectory = [current]
        while len(trajectory) - 1 < limit and current >= BET:
            current += spin(rng).profit
            trajectory.append(current)
        played = len(trajectory) - 1
        sessions.append({"participant": participant, "balance": current, "rounds": played,
                         "exhausted": current < BET,
                         "trajectory": trajectory + [current] * (limit - played)})
    return sessions
