"""Métricas de qualidade probabilística (experimento E4).

O modelo de controle de espaço é avaliado contra o desfecho efetivamente
observado em campo — quem de fato recebeu a bola — e não contra um juízo de
especialista. Isso exige métricas próprias para predições probabilísticas.
"""
from __future__ import annotations

import numpy as np

EPS = 1e-15


def brier(probabilidades: np.ndarray, desfechos: np.ndarray) -> float:
    """Brier score binário: erro quadrático médio da probabilidade prevista.

    Varia de 0 (previsão perfeita) a 1. Uma previsão constante de 0,5 sobre
    eventos equiprováveis resulta em 0,25 — é essa a linha de base contra a
    qual o modelo deve ser comparado.
    """
    p = np.asarray(probabilidades, dtype=float)
    y = np.asarray(desfechos, dtype=float)
    if p.shape != y.shape:
        raise ValueError("probabilidades e desfechos devem ter o mesmo formato")
    return float(((p - y) ** 2).mean())


def brier_multiclasse(probabilidades: np.ndarray, indices_corretos: np.ndarray) -> float:
    """Brier multiclasse, para a predição de qual atleta recebe a bola.

    Args:
        probabilidades: (M, N) — M lances, N candidatos, linhas somando 1.
        indices_corretos: (M,) índice do receptor efetivo em cada lance.
    """
    p = np.atleast_2d(np.asarray(probabilidades, dtype=float))
    idx = np.asarray(indices_corretos, dtype=int)
    if len(p) != len(idx):
        raise ValueError("número de lances incompatível entre previsões e desfechos")

    alvo = np.zeros_like(p)
    alvo[np.arange(len(idx)), idx] = 1.0
    return float(((p - alvo) ** 2).sum(axis=1).mean())


def acuracia_topk(probabilidades: np.ndarray, indices_corretos: np.ndarray, k: int = 1) -> float:
    """Proporção de lances em que o receptor efetivo está entre os k mais prováveis."""
    p = np.atleast_2d(np.asarray(probabilidades, dtype=float))
    idx = np.asarray(indices_corretos, dtype=int)
    if k < 1:
        raise ValueError("k deve ser ao menos 1")

    k_efetivo = min(k, p.shape[1])
    # argpartition evita ordenar o vetor inteiro quando só interessam os k maiores.
    topk = np.argpartition(-p, k_efetivo - 1, axis=1)[:, :k_efetivo]
    return float((topk == idx[:, None]).any(axis=1).mean())


def log_loss(probabilidades: np.ndarray, indices_corretos: np.ndarray) -> float:
    """Entropia cruzada média, em nats.

    Penaliza previsões confiantes e erradas muito mais que o Brier, o que a
    torna a métrica mais severa para detectar excesso de confiança do modelo.
    """
    p = np.atleast_2d(np.asarray(probabilidades, dtype=float))
    idx = np.asarray(indices_corretos, dtype=int)
    escolhidas = p[np.arange(len(idx)), idx]
    return float(-np.log(np.clip(escolhidas, EPS, 1.0)).mean())
