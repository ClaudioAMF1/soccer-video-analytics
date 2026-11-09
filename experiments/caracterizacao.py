"""Caracterização das sequências do SN-GSR usadas no artigo.

Quantos quadros, quantos atletas visíveis por quadro, em que fração dos
quadros a bola aparece e qual o resíduo da homografia de referência.

Uso:
    python -m experiments.caracterizacao --dados data/SoccerNetGS/test --saida resultados/
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np

from experiments.soccernet import carregar, homografia_referencia, listar
from pitch import projetar


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", type=Path, required=True)
    ap.add_argument("--saida", type=Path, default=Path("resultados"))
    args = ap.parse_args()

    quadros, atletas, bola, residuos, eventos = 0, [], [], [], Counter()
    for p in listar(args.dados):
        seq = carregar(p)
        eventos[seq.acao] += 1
        for q in seq.quadros:
            quadros += 1
            atletas.append(len([a for a in q.atletas if a.papel in ("player", "goalkeeper")]))
            bola.append(q.bola_xy is not None)
            if q.indice % 25 == 1:
                H = homografia_referencia(q)
                if H is not None:
                    uv = np.array([a.uv for a in q.atletas])
                    xy = np.array([a.xy for a in q.atletas])
                    residuos.append(float(np.linalg.norm(projetar(H, uv) - xy, axis=1).mean()))

    args.saida.mkdir(parents=True, exist_ok=True)
    texto = (f"quadros={quadros} atletas_por_quadro={np.mean(atletas):.2f} "
             f"pct_bola={100 * np.mean(bola):.1f} residuo_ref_m={np.median(residuos):.3f} "
             f"sequencias={sum(eventos.values())} tipos_evento={len(eventos)}\n")
    (args.saida / "caracterizacao.txt").write_text(texto, encoding="utf-8")
    print(texto.strip())
    print(dict(eventos))


if __name__ == "__main__":
    main()
