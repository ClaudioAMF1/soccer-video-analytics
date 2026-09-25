"""Métricas táticas calculadas no plano do campo, em unidades físicas.

Este módulo substitui o cálculo que `visualizacao_tatica.py` fazia em pixels.
A distinção não é cosmética: a área de um casco convexo medida no plano da
imagem varia com o zoom e o enquadramento da câmera, de modo que duas medições
do mesmo instante sob enquadramentos diferentes produzem valores distintos.
Em metros quadrados, a mesma grandeza é comparável entre lances, partidas e
com a literatura.

Todas as funções recebem posições (N, 2) em metros e devolvem valores em
metros ou metros quadrados.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull, QhullError

MIN_PONTOS_CASCO = 3


def centroide(posicoes: np.ndarray) -> np.ndarray:
    """Centro geométrico da equipe, em metros."""
    p = np.atleast_2d(np.asarray(posicoes, dtype=float))
    if len(p) == 0:
        return np.array([np.nan, np.nan])
    return p.mean(axis=0)


def largura(posicoes: np.ndarray) -> float:
    """Extensão da equipe no eixo transversal (y), em metros."""
    p = np.atleast_2d(np.asarray(posicoes, dtype=float))
    return float(p[:, 1].max() - p[:, 1].min()) if len(p) else float("nan")


def profundidade(posicoes: np.ndarray) -> float:
    """Extensão da equipe no eixo longitudinal (x), em metros."""
    p = np.atleast_2d(np.asarray(posicoes, dtype=float))
    return float(p[:, 0].max() - p[:, 0].min()) if len(p) else float("nan")


def area_ocupacao(posicoes: np.ndarray) -> float:
    """Área do casco convexo da equipe, em metros quadrados.

    Retorna 0 para configurações degeneradas (menos de três atletas, ou
    atletas colineares), em que o casco não tem área definida.
    """
    p = np.atleast_2d(np.asarray(posicoes, dtype=float))
    if len(p) < MIN_PONTOS_CASCO:
        return 0.0
    try:
        # Em 2D, o atributo `volume` do ConvexHull é a área delimitada;
        # `area` seria o perímetro.
        return float(ConvexHull(p).volume)
    except (QhullError, ValueError):
        return 0.0


def dispersao(posicoes: np.ndarray) -> float:
    """Distância média dos atletas ao centroide, em metros.

    Complementa a área de ocupação: o casco convexo é determinado apenas pelos
    atletas na periferia, enquanto a dispersão responde à distribuição interna.
    """
    p = np.atleast_2d(np.asarray(posicoes, dtype=float))
    if len(p) == 0:
        return float("nan")
    return float(np.sqrt(((p - p.mean(axis=0)) ** 2).sum(axis=1)).mean())


def resumo_equipe(posicoes: np.ndarray, fracao_visivel: float | None = None) -> dict:
    """Conjunto completo de métricas de nível de equipe.

    Args:
        fracao_visivel: proporção do elenco em campo efetivamente detectada no
            quadro. A transmissão mostra tipicamente 12 a 16 dos 22 atletas, e
            uma métrica agregada só é comparável entre lances quando
            acompanhada dessa proporção. É reportada junto, e não descartada.
    """
    p = np.atleast_2d(np.asarray(posicoes, dtype=float))
    c = centroide(p)
    return {
        "n_atletas": int(len(p)),
        "fracao_visivel": fracao_visivel,
        "centroide_x": float(c[0]),
        "centroide_y": float(c[1]),
        "largura_m": largura(p),
        "profundidade_m": profundidade(p),
        "area_ocupacao_m2": area_ocupacao(p),
        "dispersao_m": dispersao(p),
    }


def distancia_entre_centroides(pos_a: np.ndarray, pos_b: np.ndarray) -> float:
    """Distância entre os centroides de duas equipes, em metros."""
    return float(np.linalg.norm(centroide(pos_a) - centroide(pos_b)))
