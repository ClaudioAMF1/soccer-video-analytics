"""Registro do campo em vídeo gravado, por quadros-chave anotados.

Em transmissões gravadas a câmera se move o tempo todo, e a homografia entre a
imagem e o gramado muda a cada quadro. Treinar um detector automático de linhas
do campo está fora do escopo deste trabalho; como o processamento é offline,
adota-se uma alternativa mais simples e verificável:

1. Em alguns **quadros-chave**, marcam-se à mão pontos de referência do campo
   (cantos das áreas, interseções de linhas) e estima-se a homografia exata
   daquele quadro.
2. Entre os quadros-chave, a homografia é **propagada** pelo movimento de câmera
   estimado quadro a quadro (o `MotionEstimator` do Norfair fornece, para cada
   quadro, a transformação da imagem corrente para a do primeiro quadro).
3. Como a propagação acumula deriva, cada quadro intermediário recebe as
   estimativas das duas chaves vizinhas, combinadas com peso proporcional à
   proximidade. É a **reancoragem**: a deriva de uma chave é compensada pela da
   outra, e o erro deixa de crescer indefinidamente.

A deriva remanescente é mensurável contra a referência do SoccerNet e constitui
parte do experimento E2.

Convenções:
    H_k : imagem do quadro k -> campo (metros)
    M_t : imagem do quadro t -> imagem de referência absoluta (pixels)
"""
from __future__ import annotations

from typing import Callable, Mapping

import numpy as np

from .homografia import estimar_homografia, projetar

PONTOS_AMOSTRA = 7  # grade de 7x7 pontos para reajustar H após a combinação


def grade_imagem(largura: float, altura: float, n: int = PONTOS_AMOSTRA) -> np.ndarray:
    """Grade regular de pontos cobrindo a imagem, em pixels."""
    xs = np.linspace(0.0, largura, n)
    ys = np.linspace(0.0, altura, n)
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    return np.column_stack([gx.ravel(), gy.ravel()])


def homografia_por_amostragem(
    transformar: Callable[[np.ndarray], np.ndarray],
    largura: float,
    altura: float,
    n: int = PONTOS_AMOSTRA,
) -> np.ndarray:
    """Ajusta H (imagem -> campo) a partir de uma função ponto a ponto.

    Permite representar como matriz uma transformação obtida por composição ou
    combinação de outras, que é o formato exigido pelo exportador e pelo
    player web.
    """
    origem = grade_imagem(largura, altura, n)
    destino = np.asarray(transformar(origem), dtype=float)
    validos = np.isfinite(destino).all(axis=1)
    if validos.sum() < 4:
        raise ValueError("a transformação não produziu pontos finitos suficientes")
    return estimar_homografia(origem[validos], destino[validos])


def deriva_m(H_estimada: np.ndarray, H_referencia: np.ndarray, pts_img: np.ndarray) -> np.ndarray:
    """Distância, em metros, entre as projeções de duas homografias."""
    a = projetar(H_estimada, pts_img)
    b = projetar(H_referencia, pts_img)
    return np.sqrt(((a - b) ** 2).sum(axis=1))


class RegistroPorChaves:
    """Homografia de qualquer quadro a partir de quadros-chave anotados.

    Args:
        chaves: quadro -> H_k (imagem do quadro k -> campo), estimada a partir
            das correspondências anotadas à mão.
        movimento: função quadro -> M_t (imagem do quadro t -> referência
            absoluta). Com o Norfair, é a `homography_matrix` da transformação
            devolvida pelo `MotionEstimator` naquele quadro.
        largura, altura: dimensões do quadro, em pixels.
    """

    def __init__(
        self,
        chaves: Mapping[int, np.ndarray],
        movimento: Callable[[int], np.ndarray],
        largura: float,
        altura: float,
    ):
        if not chaves:
            raise ValueError("é necessário ao menos um quadro-chave anotado")
        self.movimento = movimento
        self.largura = float(largura)
        self.altura = float(altura)
        self.quadros_chave = sorted(int(k) for k in chaves)

        # Cada chave é reescrita como transformação referência absoluta -> campo,
        # o que permite aplicá-la a qualquer quadro pela composição com M_t.
        self._abs_para_campo = {
            k: np.asarray(chaves[k], dtype=float) @ np.linalg.inv(self._m(k))
            for k in self.quadros_chave
        }

    def _m(self, quadro: int) -> np.ndarray:
        return np.asarray(self.movimento(quadro), dtype=float)

    def _pela_chave(self, quadro: int, chave: int) -> np.ndarray:
        """H do quadro propagada a partir de uma única chave."""
        H = self._abs_para_campo[chave] @ self._m(quadro)
        return H / H[2, 2] if abs(H[2, 2]) > 1e-12 else H

    def vizinhas(self, quadro: int) -> tuple[int, int]:
        """Chaves imediatamente anterior e posterior (iguais nos extremos)."""
        anteriores = [k for k in self.quadros_chave if k <= quadro]
        posteriores = [k for k in self.quadros_chave if k >= quadro]
        antes = anteriores[-1] if anteriores else self.quadros_chave[0]
        depois = posteriores[0] if posteriores else self.quadros_chave[-1]
        return antes, depois

    def homografia(self, quadro: int, reancorar: bool = True) -> np.ndarray:
        """H (imagem do quadro -> campo).

        Args:
            reancorar: se falso, usa apenas a chave anterior. Existe para que o
                experimento E2 possa medir quanto a reancoragem reduz a deriva.
        """
        antes, depois = self.vizinhas(quadro)
        if not reancorar or antes == depois:
            return self._pela_chave(quadro, antes)

        alpha = (quadro - antes) / (depois - antes)
        H_a = self._pela_chave(quadro, antes)
        H_d = self._pela_chave(quadro, depois)

        # A combinação é feita sobre pontos projetados no campo, e não sobre os
        # elementos das matrizes: somar matrizes de homografia não tem
        # interpretação geométrica, enquanto a média ponderada de posições em
        # metros tem.
        def combinado(pts: np.ndarray) -> np.ndarray:
            return (1.0 - alpha) * projetar(H_a, pts) + alpha * projetar(H_d, pts)

        return homografia_por_amostragem(combinado, self.largura, self.altura)
