"""Métricas do erro de registro do campo (experimento E2)."""
from __future__ import annotations

import numpy as np


def estatisticas_erro(erros_m: np.ndarray) -> dict:
    """Resumo do erro de reprojeção, em metros.

    Reporta mediana e p95 além da média porque a distribuição do erro de
    registro é fortemente assimétrica: a cauda, concentrada na periferia da
    imagem, é o que de fato inviabiliza métricas de nível de jogador, e a média
    sozinha a esconde.
    """
    e = np.asarray(erros_m, dtype=float)
    e = e[np.isfinite(e)]
    if len(e) == 0:
        return {"n": 0, "media_m": float("nan"), "mediana_m": float("nan"),
                "p95_m": float("nan"), "max_m": float("nan"), "rmse_m": float("nan")}
    return {
        "n": int(len(e)),
        "media_m": float(e.mean()),
        "mediana_m": float(np.median(e)),
        "p95_m": float(np.percentile(e, 95)),
        "max_m": float(e.max()),
        "rmse_m": float(np.sqrt((e ** 2).mean())),
    }


def erro_por_regiao(
    pontos_campo: np.ndarray,
    erros_m: np.ndarray,
    comprimento: float = 105.0,
    n_faixas: int = 3,
) -> dict:
    """Erro estratificado por terço longitudinal do campo.

    A precisão do registro degrada sistematicamente longe do centro da imagem,
    onde há menos linhas visíveis e a perspectiva é mais acentuada. Reportar o
    erro agregado esconde essa estrutura.
    """
    p = np.atleast_2d(np.asarray(pontos_campo, dtype=float))
    e = np.asarray(erros_m, dtype=float)
    if len(p) != len(e):
        raise ValueError("pontos_campo e erros_m devem ter o mesmo comprimento")

    limites = np.linspace(0.0, comprimento, n_faixas + 1)
    nomes = ["defensivo", "central", "ofensivo"] if n_faixas == 3 else \
            [f"faixa_{i + 1}" for i in range(n_faixas)]

    saida = {}
    for i, nome in enumerate(nomes):
        # A última faixa inclui o limite superior, para não descartar a linha de fundo.
        if i == n_faixas - 1:
            mascara = (p[:, 0] >= limites[i]) & (p[:, 0] <= limites[i + 1])
        else:
            mascara = (p[:, 0] >= limites[i]) & (p[:, 0] < limites[i + 1])
        saida[nome] = estatisticas_erro(e[mascara])
    return saida
