"""Regra de exibição: só vai ao público o que resiste ao erro de registro.

O experimento E5 mede, para cada métrica, o erro relativo induzido por um dado
erro médio de registro do campo. O experimento E2 mede quanto erro de registro
o pipeline realmente comete. Cruzando os dois, decide-se quais visualizações
podem ser exibidas ao espectador sem risco relevante de afirmar algo falso.

Uma visualização só é exibida se **todas** as métricas que a sustentam ficarem
abaixo do limiar no erro de registro observado. Fora da faixa medida em E5, a
decisão é conservadora: não exibir.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

NIVEL = {
    "largura_a_m": "equipe",
    "profundidade_a_m": "equipe",
    "area_ocupacao_a_m2": "equipe",
    "dispersao_a_m": "equipe",
    "dist_centroides_m": "equipe",
    "controle_a": "equipe",
    "concordancia_dominante": "jogador",
    "area_maior_dominio_m2": "jogador",
}

# Métricas das quais cada visualização depende.
VISUALIZACOES = {
    "zonas_de_controle": ["controle_a"],
    "forma_da_equipe": ["largura_a_m", "profundidade_a_m", "area_ocupacao_a_m2"],
    "distancia_entre_linhas": ["dist_centroides_m"],
    "dominio_individual": ["concordancia_dominante", "area_maior_dominio_m2"],
}

LIMIAR_PADRAO_PCT = 5.0


def carregar_curvas_e5(caminho: str | Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Lê o CSV do E5: métrica -> (erro de registro em m, erro relativo em %)."""
    with Path(caminho).open(encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        raise ValueError("CSV do E5 vazio")

    x = np.array([float(l["erro_registro_medio_m"]) for l in linhas])
    ordem = np.argsort(x)
    curvas = {}
    for metrica in NIVEL:
        coluna = f"{metrica}__erro_rel_pct"
        if coluna in linhas[0]:
            y = np.array([float(l[coluna]) for l in linhas])
            curvas[metrica] = (x[ordem], y[ordem])
    return curvas


def decidir_exibicao(
    curvas: dict[str, tuple[np.ndarray, np.ndarray]],
    erro_registro_m: float,
    limiar_pct: float = LIMIAR_PADRAO_PCT,
) -> dict[str, dict]:
    """Para cada visualização, decide se pode ser exibida ao público.

    Returns:
        visualização -> {"exibir", "erro_pct" (pior métrica), "nivel", "motivo"}
    """
    decisao = {}
    for vis, metricas in VISUALIZACOES.items():
        faltando = [m for m in metricas if m not in curvas]
        if faltando:
            decisao[vis] = {"exibir": False, "erro_pct": None,
                            "nivel": NIVEL[metricas[0]],
                            "motivo": f"métricas sem medição: {faltando}"}
            continue

        piores, fora = [], False
        for m in metricas:
            x, y = curvas[m]
            if erro_registro_m > x.max() or erro_registro_m < x.min():
                fora = True
                break
            piores.append(float(np.interp(erro_registro_m, x, y)))

        if fora:
            decisao[vis] = {"exibir": False, "erro_pct": None,
                            "nivel": NIVEL[metricas[0]],
                            "motivo": "erro de registro fora da faixa medida no E5"}
            continue

        pior = max(piores)
        decisao[vis] = {
            "exibir": pior <= limiar_pct,
            "erro_pct": round(pior, 2),
            "nivel": NIVEL[metricas[0]],
            "motivo": f"erro relativo {pior:.2f}% {'<=' if pior <= limiar_pct else '>'} limiar {limiar_pct}%",
        }
    return decisao
