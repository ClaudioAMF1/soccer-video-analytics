"""Estimação e aplicação da homografia entre o plano da imagem e o gramado.

A transformação é estimada pelo algoritmo DLT (Direct Linear Transform) com
normalização de Hartley, que condiciona o sistema linear e reduz
substancialmente a sensibilidade a ruído nas correspondências.

Convenção: `H` leva pontos da **imagem** para o **campo**, de modo que
`[X, Y, 1]^T ~ H @ [x, y, 1]^T`, com (x, y) em pixels e (X, Y) em metros.
"""
from __future__ import annotations

import numpy as np

MIN_CORRESPONDENCIAS = 4


def _normalizar(pontos: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Normalização de Hartley: centroide na origem, distância média sqrt(2).

    Retorna (T, pontos_normalizados), com `T` a matriz 3x3 tal que
    `pontos_norm_h = T @ pontos_h`.
    """
    p = np.asarray(pontos, dtype=float)
    centroide = p.mean(axis=0)
    deslocado = p - centroide
    dist_media = np.sqrt((deslocado ** 2).sum(axis=1)).mean()

    # Conjuntos degenerados (todos os pontos coincidentes) não admitem escala.
    escala = np.sqrt(2.0) / dist_media if dist_media > 1e-12 else 1.0

    T = np.array([
        [escala, 0.0, -escala * centroide[0]],
        [0.0, escala, -escala * centroide[1]],
        [0.0, 0.0, 1.0],
    ])
    return T, deslocado * escala


def estimar_homografia(pts_img: np.ndarray, pts_campo: np.ndarray) -> np.ndarray:
    """Estima H (imagem -> campo) por DLT normalizado.

    Args:
        pts_img: array (N, 2) de pontos na imagem, em pixels.
        pts_campo: array (N, 2) dos mesmos pontos no campo, em metros.

    Returns:
        Matriz 3x3 normalizada para H[2, 2] == 1 quando possível.

    Raises:
        ValueError: se houver menos de quatro correspondências.
    """
    origem = np.asarray(pts_img, dtype=float)
    destino = np.asarray(pts_campo, dtype=float)

    if origem.shape != destino.shape or origem.ndim != 2 or origem.shape[1] != 2:
        raise ValueError("pts_img e pts_campo devem ter o mesmo formato (N, 2)")
    if len(origem) < MIN_CORRESPONDENCIAS:
        raise ValueError(
            f"são necessárias ao menos {MIN_CORRESPONDENCIAS} correspondências, "
            f"recebidas {len(origem)}"
        )

    T_o, o = _normalizar(origem)
    T_d, d = _normalizar(destino)

    # Duas linhas por correspondência, conforme a formulação padrão do DLT.
    linhas = []
    for (x, y), (u, v) in zip(o, d):
        linhas.append([0.0, 0.0, 0.0, -x, -y, -1.0, v * x, v * y, v])
        linhas.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y, -u])
    A = np.array(linhas)

    # A solução é o vetor singular associado ao menor valor singular.
    _, _, Vt = np.linalg.svd(A)
    H_norm = Vt[-1].reshape(3, 3)

    H = np.linalg.inv(T_d) @ H_norm @ T_o
    if abs(H[2, 2]) > 1e-12:
        H = H / H[2, 2]
    return H


def projetar(H: np.ndarray, pontos: np.ndarray) -> np.ndarray:
    """Aplica H a pontos (N, 2), devolvendo (N, 2) no espaço de destino.

    Pontos cuja coordenada homogênea se anula caem sobre a linha do horizonte
    e não têm imagem finita; são devolvidos como NaN em vez de infinito, para
    que sigam detectáveis por `np.isnan` a jusante.
    """
    p = np.atleast_2d(np.asarray(pontos, dtype=float))
    homogeneos = np.column_stack([p, np.ones(len(p))])
    projetados = homogeneos @ np.asarray(H, dtype=float).T

    w = projetados[:, 2]
    degenerado = np.abs(w) < 1e-12
    w_seguro = np.where(degenerado, 1.0, w)

    saida = projetados[:, :2] / w_seguro[:, None]
    saida[degenerado] = np.nan
    return saida


def erro_reprojecao(
    H: np.ndarray, pts_img: np.ndarray, pts_campo: np.ndarray
) -> np.ndarray:
    """Erro por ponto, em metros, entre a projeção de `pts_img` e `pts_campo`."""
    projetados = projetar(H, pts_img)
    return np.sqrt(((projetados - np.asarray(pts_campo, dtype=float)) ** 2).sum(axis=1))


def estimar_homografia_ransac(
    pts_img: np.ndarray,
    pts_campo: np.ndarray,
    limiar_m: float = 0.5,
    iteracoes: int = 1000,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimação robusta de H, tolerante a correspondências espúrias.

    A detecção automática de linhas produz correspondências erradas com
    frequência não desprezível (linhas de publicidade, sombras, marcas de
    desgaste do gramado). Ajustar por mínimos quadrados sobre o conjunto
    completo deixa o resultado refém desses pontos.

    Args:
        limiar_m: erro de reprojeção, em metros, abaixo do qual uma
            correspondência é considerada inlier.

    Returns:
        (H, mascara_inliers). O H devolvido é reajustado sobre todos os
        inliers do melhor consenso, não apenas sobre a amostra sorteada.
    """
    origem = np.asarray(pts_img, dtype=float)
    destino = np.asarray(pts_campo, dtype=float)
    n = len(origem)

    if n < MIN_CORRESPONDENCIAS:
        raise ValueError(
            f"são necessárias ao menos {MIN_CORRESPONDENCIAS} correspondências, "
            f"recebidas {n}"
        )
    if n == MIN_CORRESPONDENCIAS:
        H = estimar_homografia(origem, destino)
        return H, np.ones(n, dtype=bool)

    gerador = rng if rng is not None else np.random.default_rng()
    melhor_H = None
    melhor_inliers = np.zeros(n, dtype=bool)

    for _ in range(iteracoes):
        amostra = gerador.choice(n, size=MIN_CORRESPONDENCIAS, replace=False)
        try:
            H_cand = estimar_homografia(origem[amostra], destino[amostra])
        except (ValueError, np.linalg.LinAlgError):
            continue

        erros = erro_reprojecao(H_cand, origem, destino)
        inliers = np.nan_to_num(erros, nan=np.inf) < limiar_m

        if inliers.sum() > melhor_inliers.sum():
            melhor_inliers = inliers
            melhor_H = H_cand

    if melhor_H is None:
        raise RuntimeError("RANSAC não encontrou nenhuma homografia válida")

    # Reajuste final sobre o consenso, que usa toda a informação disponível.
    if melhor_inliers.sum() >= MIN_CORRESPONDENCIAS:
        melhor_H = estimar_homografia(origem[melhor_inliers], destino[melhor_inliers])

    return melhor_H, melhor_inliers
