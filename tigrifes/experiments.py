"""Cinco experimentos do enunciado e exportação reproduzível: python -m tigrifes.experiments."""

import argparse
import csv
import io
import json
import os
import platform
import statistics
import threading
import zipfile
from collections import Counter
from functools import lru_cache
from importlib.metadata import version
from itertools import accumulate
from pathlib import Path
from random import Random

from .machine import PAYOUTS, conditional_prizes, simulate, simulate_participants

N = 10_000
SEEDS = (10, 2026, 123456)
CHART_NAMES = ("frequencies", "convergence", "balances")
PLOT_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def run_experiments():
    sequences = {seed: simulate(N, seed) for seed in SEEDS}
    base = sequences[2026]
    counts = Counter(r.prize for r in base)
    distribution = [{"label": symbol * 3, "prize": prize, "profit": prize - 1,
                     "probability": 1 / 125, "count": counts[prize], "frequency": counts[prize] / N}
                    for symbol, prize in PAYOUTS.items()]
    distribution.append({"label": "Sem prêmio", "prize": 0, "profit": -1,
                         "probability": 120 / 125, "count": counts[0], "frequency": counts[0] / N})
    prize_mean = statistics.mean(r.prize for r in base)
    profit_mean = statistics.mean(r.profit for r in base)
    prize_frequency = sum(r.prize > 0 for r in base) / N
    e1 = {"distribution": distribution, "mean_profit": profit_mean, "rtp": prize_mean,
          "prize_frequency": prize_frequency, "sample_stddev": statistics.stdev(r.profit for r in base)}
    trajectories = {seed: [total / i for i, total in enumerate(accumulate(r.profit for r in rounds), 1)]
                    for seed, rounds in sequences.items()}
    e2 = {"checkpoints": [{"seed": seed, "n100": values[99], "n1000": values[999], "n10000": values[9999]}
                          for seed, values in trajectories.items()],
          "reproduced": base[:10] == simulate(10, 2026),
          "first_ten": [r.as_dict() for r in base[:10]], "trajectories": trajectories}
    participants = simulate_participants(Random(42))
    balances = [p["balance"] for p in participants]
    e3 = {"participants": participants, "gain": sum(b > 100 for b in balances),
          "tie": sum(b == 100 for b in balances), "loss": sum(b < 100 for b in balances),
          "exhausted": sum(p["exhausted"] for p in participants),
          "mean": statistics.mean(balances), "median": statistics.median(balances)}
    # Frações exatas de meio crédito: 110% dos pagamentos são múltiplos de 0,5.
    enhanced_total = sum(r.prize * 11 // 5 for r in base) / 2
    e5 = [{"name": "Base", "prize_probability": 0.04, "prize_frequency": prize_frequency,
           "theoretical_prize": 0.84, "observed_prize": prize_mean,
           "theoretical_profit": -0.16, "observed_profit": profit_mean,
           "theoretical_rtp": 0.84, "observed_rtp": prize_mean},
          {"name": "Prêmios +10%", "prize_probability": 0.04, "prize_frequency": prize_frequency,
           "theoretical_prize": 0.924, "observed_prize": enhanced_total / N,
           "theoretical_profit": -0.076, "observed_profit": enhanced_total / N - 1,
           "theoretical_rtp": 0.924, "observed_rtp": enhanced_total / N}]
    metadata = {"model_version": "1.0", "python": platform.python_version(),
                "implementation": platform.python_implementation(), "platform": platform.platform(),
                "generator": "random.Random / Mersenne Twister; randrange(5), 3 chamadas por rodada",
                "dependencies": {name: version(name) for name in ("Jinja2", "matplotlib")},
                "rounds_e1_e2_e4_e5": N, "seeds_e1_e2": list(SEEDS), "seed_e3": 42,
                "participants_e3": 100, "initial_balance_e3": 100, "max_rounds_e3": 500,
                "bet": 1, "payouts": PAYOUTS, "e4_e5_reuse_e1": True,
                "standard_deviation_divisor": "N - 1"}
    return {"metadata": metadata, "e1": e1, "e2": e2, "e3": e3,
            "e4": conditional_prizes(base), "e5": e5, "sequences": sequences}


@lru_cache(maxsize=6)
def chart_bytes(name, extension="png"):
    if name not in CHART_NAMES or extension not in ("png", "svg"):
        raise ValueError("Gráfico desconhecido.")
    # Matplotlib não é thread-safe; serializa construções simultâneas de gráficos.
    with PLOT_LOCK:
        cache_dir = Path(os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / "tmp" / "matplotlib")))
        cache_dir.mkdir(parents=True, exist_ok=True)
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        data = run_experiments()
        figure = Figure(figsize=(9, 4.5), layout="constrained", facecolor="#ffffff")
        FigureCanvasAgg(figure)
        ax = figure.subplots()
        colors = ("#17634d", "#bd5c35", "#5269a1")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.16)
        ax.set_axisbelow(True)
        if name == "frequencies":
            rows = data["e1"]["distribution"]
            x = list(range(len(rows)))
            ax.bar([i - .19 for i in x], [r["probability"] * 100 for r in rows], .38, label="Teoria", color=colors[0])
            bars = ax.bar([i + .19 for i in x], [r["frequency"] * 100 for r in rows], .38, label="Observação", color=colors[1], hatch="//")
            ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=8)
            ax.set_xticks(x, [r["label"] for r in rows])
            ax.set_ylabel("Frequência (%)")
            ax.set_xlabel("Resultado central")
            ax.set_ylim(0, 108)
        elif name == "convergence":
            for color, style, (seed, values) in zip(colors, ("-", "--", "-."), data["e2"]["trajectories"].items()):
                ax.plot(range(1, N + 1), values, color=color, linestyle=style, linewidth=1, label=f"Semente {seed}")
            ax.axhline(-.16, color="#303c39", linestyle="--", label="Esperança: −0,16")
            ax.set_xlabel("Rodadas acumuladas")
            ax.set_ylabel("Lucro médio (créditos / rodada)")
        else:
            for style, participant in zip(("-", "--", "-.", ":", (0, (5, 1, 1, 1, 1, 1))), data["e3"]["participants"][:5]):
                ax.plot(range(501), participant["trajectory"], linestyle=style, linewidth=1.4, label=f"Participante {participant['participant']}")
            ax.axhline(100, color="#303c39", linestyle="--", alpha=.5, label="Saldo inicial")
            ax.set_xlabel("Rodada (saldo mantido após a parada)")
            ax.set_ylabel("Saldo (créditos fictícios)")
        ax.legend(frameon=False, fontsize=8)
        output = io.BytesIO()
        figure.savefig(output, format=extension, dpi=160)
        return output.getvalue()


def csv_bytes(rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def export_files():
    data = run_experiments()
    files = {"metadata.json": json.dumps(data["metadata"], ensure_ascii=False, indent=2).encode("utf-8")}
    summary = {"e1": data["e1"], "e2": {k: v for k, v in data["e2"].items() if k != "trajectories"},
               "e3": {k: v for k, v in data["e3"].items() if k != "participants"}, "e4": data["e4"], "e5": data["e5"]}
    files["resumos.json"] = json.dumps(summary, ensure_ascii=False, indent=2).encode("utf-8")
    tables = {"e1_frequencias": data["e1"]["distribution"], "e2_medias": data["e2"]["checkpoints"],
              "e3_participantes": [{k: v for k, v in p.items() if k != "trajectory"} for p in data["e3"]["participants"]],
              "e4_condicionais": data["e4"], "e5_pagamentos": data["e5"]}
    for seed, rounds in data["sequences"].items():
        tables[f"rodadas_semente_{seed}"] = [
            {"round": i, "k1": r.stops[0], "k2": r.stops[1], "k3": r.stops[2],
             "center": "".join(r.center), "prize": r.prize, "profit": r.profit,
             "cumulative_mean": data["e2"]["trajectories"][seed][i - 1]}
            for i, r in enumerate(rounds, 1)]
    tables["e3_trajetorias"] = [{"round": i, **{f"participant_{p['participant']}": p["trajectory"][i]
                                                for p in data["e3"]["participants"][:5]}} for i in range(501)]
    for name, rows in tables.items():
        files[f"{name}.csv"] = csv_bytes(rows)
    for name in CHART_NAMES:
        for extension in ("png", "svg"):
            files[f"graficos/{name}.{extension}"] = chart_bytes(name, extension)
    files["LEIA-ME.txt"] = (
        "TigrIFES — experimentos do Trabalho I\n"
        "Somente créditos fictícios. CSV: UTF-8 com BOM; separador vírgula; decimal ponto.\n"
        "Probabilidades, frequências e RTP nos CSV/JSON são proporções (0.84 = 84%).\n"
        "Sementes, parâmetros, gerador e versões: metadata.json. Resumos: resumos.json.\n"
        "E1: semente 2026, 10.000 rodadas; E2 reutiliza 2026 e acrescenta 10 e 123456.\n"
        "E3: semente 42 contínua, 100 participantes, saldo 100, até 500 rodadas.\n"
        "E4 e E5 reutilizam os mesmos resultados do E1; não sorteiam novamente.\n"
        "Os gráficos PNG e SVG usam os dados integrais; os cinco primeiros participantes não foram selecionados pelo resultado.\n"
        "Reproduzir com: python -m tigrifes.experiments --output results\n"
        "As interpretações e os limites estão na página de experimentos e no README do projeto.\n"
    ).encode("utf-8")
    return files


@lru_cache(maxsize=1)
def export_zip():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, contents in export_files().items():
            archive.writestr(name, contents)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Executa e exporta os cinco experimentos acadêmicos.")
    parser.add_argument("--output", type=Path, default=Path("results"))
    args = parser.parse_args()
    for name, contents in export_files().items():
        destination = args.output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(contents)
    print(f"Cinco experimentos exportados para {args.output.resolve()}")


if __name__ == "__main__":
    main()
