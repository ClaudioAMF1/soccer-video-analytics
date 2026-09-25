"""Perturbação controlada da homografia (experimento E5 do artigo).

A análise de sensibilidade precisa injetar erro de registro de magnitude
conhecida. Somar ruído independente às posições já projetadas seria incorreto:
o erro de homografia real não é independente entre jogadores, e sim
espacialmente correlacionado — quando o registro está deslocado, *todos* os
jogadores de uma região do campo deslocam-se junto, e é essa correlação que
determina o efeito sobre métricas agregadas de equipe.

O modelo adotado reproduz a origem física do erro: perturba-se a posição das
correspondências detectadas na imagem e reajusta-se a transformação. O campo de
erro resultante é, por construção, correlacionado e compatível com uma
homografia.
"""
from __future__ import annotations

import numpy as np

from .homografia import erro_reprojecao, estimar_homografia


def perturbar_homografia(
    pts_img: np.ndarray,
    pts_campo: np.ndarray,
    sigma_px: float,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Reajusta H a partir de correspondências de imagem com ruído gaussiano.

    Args:
        sigma_px: desvio padrão do ruído somado às correspondências, em pixels.

    Returns:
        A homografia perturbada (imagem -> campo).
    """
    gerador = rng if rng is not None else np.random.default_rng()
    origem = np.asarray(pts_img, dtype=float)
    ruido = gerador.normal(0.0, sigma_px, origem.shape) if sigma_px > 0 else 0.0
    return estimar_homografia(origem + ruido, pts_campo)


def erro_induzido(
    pts_img: np.ndarray,
    pts_campo: np.ndarray,
    sigma_px: float,
    repeticoes: int = 50,
    rng: np.random.Generator | None = None,
) -> float:
    """Erro médio de reprojeção, em metros, induzido por `sigma_px`.

    Estimado por Monte Carlo sobre `repeticoes` realizações do ruído.
    """
    gerador = rng if rng is not None else np.random.default_rng()
    erros = []
    for _ in range(repeticoes):
        try:
            H = perturbar_homografia(pts_img, pts_campo, sigma_px, gerador)
        except (ValueError, np.linalg.LinAlgError):
            continue
        e = erro_reprojecao(H, pts_img, pts_campo)
        e = e[np.isfinite(e)]
        if len(e):
            erros.append(e.mean())
    return float(np.mean(erros)) if erros else float("nan")


def calibrar_sigma(
    pts_img: np.ndarray,
    pts_campo: np.ndarray,
    erro_alvo_m: float,
    repeticoes: int = 50,
    sigma_max: float = 200.0,
    tolerancia: float = 0.01,
    max_iter: int = 40,
    rng: np.random.Generator | None = None,
) -> float:
    """Encontra o `sigma_px` que induz um erro médio de `erro_alvo_m` metros.

    Permite parametrizar o experimento na unidade que interessa ao leitor
    (metros no campo) em vez de pixels, cuja interpretação depende da resolução
    e do enquadramento.

    A busca é uma bisseção sobre sigma, válida porque o erro induzido cresce
    monotonicamente com a magnitude do ruído.
    """
    if erro_alvo_m <= 0:
        return 0.0

    gerador = rng if rng is not None else np.random.default_rng()
    baixo, alto = 0.0, sigma_max

    # O limite superior precisa de fato ultrapassar o alvo, sob pena de a
    # bisseção convergir para sigma_max e devolver um erro menor que o pedido.
    if erro_induzido(pts_img, pts_campo, alto, repeticoes, gerador) < erro_alvo_m:
        return alto

    for _ in range(max_iter):
        meio = (baixo + alto) / 2.0
        obtido = erro_induzido(pts_img, pts_campo, meio, repeticoes, gerador)
        if not np.isfinite(obtido):
            alto = meio
            continue
        if abs(obtido - erro_alvo_m) < tolerancia:
            return meio
        if obtido < erro_alvo_m:
            baixo = meio
        else:
            alto = meio

    return (baixo + alto) / 2.0
