"""Figura do artigo: sensibilidade das métricas ao erro de registro (dados reais).

Lê `e5_real.csv` e, opcionalmente, `e2_registro_real.csv` para sombrear a faixa
de erro de registro que o pipeline efetivamente comete.

Uso:
    python -m experiments.figura_sensibilidade --e5 resultados/e5_real.csv \\
        --e2 resultados/e2_registro_real.csv --saida paper/figuras/sensibilidade_real.png
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402,F401

LIMIAR_PCT = 5.0
# (coluna, rótulo, cor, marcador, traço). Cores: paleta categórica validada
# (ordem fixa); marcador e traço garantem a leitura em impressão monocromática.
SERIES = [
    ("controle_equipe", "Controle de espaço", "#2a78d6", "o", "-"),
    ("largura", "Largura", "#eb6834", "s", "--"),
    ("profundidade", "Profundidade", "#1baf7a", "^", "-."),
    ("identidade_dominante", "Jogador dominante", "#eda100", "D", ":"),
    ("area_ocupacao", "Área de ocupação", "#e87ba4", "v", (0, (5, 1, 1, 1))),
]
TINTA, TINTA_2, GRADE = "#0b0b0b", "#52514e", "#d9d8d4"


def ler(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e5", type=Path, required=True)
    ap.add_argument("--e2", type=Path, default=None)
    ap.add_argument("--condicao", default="chaves_1s_so_anterior",
                    help="Condição do E2 cuja faixa (mediana a p90) é sombreada")
    ap.add_argument("--saida", type=Path, required=True)
    args = ap.parse_args()

    linhas = [l for l in ler(args.e5) if l["erro_medio_m"] not in ("", "None")]
    x = [float(l["erro_medio_m"]) for l in linhas]

    plt.rcParams.update({"font.family": "serif", "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
                         "font.size": 9})
    fig, ax = plt.subplots(figsize=(5.6, 2.9))

    if args.e2 and args.e2.exists():
        e2 = {l["condicao"]: l for l in ler(args.e2)}
        if args.condicao in e2:
            lo, hi = float(e2[args.condicao]["mediana_m"]), float(e2[args.condicao]["p90_m"])
            hi = min(hi, max(x) * 1.02)
            ax.axvspan(lo, hi, color="#ecebe7", zorder=0, lw=0)
            ax.text(hi - 0.03, 22.4, "erro do registro com\numa chave por segundo\n(mediana a p90)",
                    color=TINTA_2, fontsize=8, va="top", ha="right")

    ax.axhline(LIMIAR_PCT, color=TINTA_2, lw=1, ls=(0, (2, 2)), zorder=1)
    ax.text(max(x) * 1.0, LIMIAR_PCT + 0.4, "limiar de exibição (5%)", color=TINTA_2, fontsize=8, ha="right")

    for col, rot, cor, mk, ls in SERIES:
        y = [float(l[col]) for l in linhas]
        ax.plot(x, y, color=cor, lw=2, ls=ls, marker=mk, ms=6, mec="white", mew=1.2, zorder=3, label=rot)
        ax.annotate(rot, (x[-1], y[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8.5, color=TINTA)

    ax.set_xlabel("Erro médio de registro (m)", color=TINTA)
    ax.set_ylabel("Erro relativo da métrica (%)", color=TINTA)
    ax.set_xlim(0, max(x) * 1.02)
    ax.set_ylim(0, 23)
    ax.grid(axis="y", color=GRADE, lw=0.6)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(GRADE)
    ax.tick_params(colors=TINTA_2)
    virgula = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))
    ax.xaxis.set_major_formatter(virgula)
    ax.yaxis.set_major_formatter(virgula)
    ax.legend(loc="upper left", fontsize=8, frameon=False, ncol=1)
    fig.subplots_adjust(right=0.76)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.saida, dpi=300, bbox_inches="tight")
    print(f"figura: {args.saida}")


if __name__ == "__main__":
    main()
