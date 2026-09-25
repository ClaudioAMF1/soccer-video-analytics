"""Classificação de equipe por faixas de cor no espaço HSV.

Mantido como linha de base interpretável do artigo: a regra de decisão é
explícita e auditável, ao contrário de um classificador aprendido. Serve de
termo de comparação para o agrupamento não supervisionado, e sua limitação
principal — as faixas precisam ser definidas à mão para cada partida — é
justamente o resultado que motiva a alternativa.

Correção em relação à versão anterior: `max_pixels` iniciava em -1 com
comparação estrita, de modo que um recorte sem nenhum pixel correspondente
retornava o *primeiro* filtro da lista. Como o filtro do árbitro vinha
primeiro, todo atleta não classificável era rotulado como árbitro e removido
silenciosamente das métricas táticas.
"""
from __future__ import annotations

import cv2
import numpy as np

from .base_classifier import BaseClassifier

DESCONHECIDO = "unknown"


class HSVClassifier(BaseClassifier):
    """Atribui a equipe pela cor predominante na região do torso.

    Args:
        min_fracao: fração mínima de pixels do recorte que precisam
            corresponder a alguma faixa para que a classificação seja aceita.
            Abaixo disso o resultado é `DESCONHECIDO`, o que é preferível a um
            palpite: um atleta mal classificado contamina o casco convexo e a
            atribuição de posse da equipe errada.
    """

    def __init__(self, filters, min_fracao: float = 0.05):
        self.filters = filters
        self.min_fracao = min_fracao

    def predict(self, input_images):
        return [self._predict_img(img) for img in input_images]

    def _predict_img(self, img) -> str:
        if img is None or getattr(img, "size", 0) == 0:
            return DESCONHECIDO

        recorte = self._crop_jersey(img)
        if recorte.size == 0:
            return DESCONHECIDO

        hsv = cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)
        area = recorte.shape[0] * recorte.shape[1]

        melhor_nome = DESCONHECIDO
        melhor_contagem = 0
        for team_filter in self.filters:
            contagem = sum(
                self._count_color_pixels(hsv, cor) for cor in team_filter["colors"]
            )
            if contagem > melhor_contagem:
                melhor_contagem = contagem
                melhor_nome = team_filter["name"]

        if area == 0 or melhor_contagem / area < self.min_fracao:
            return DESCONHECIDO
        return melhor_nome

    @staticmethod
    def _count_color_pixels(img_hsv: np.ndarray, color_filter: dict) -> int:
        mask = cv2.inRange(img_hsv, color_filter["lower_hsv"], color_filter["upper_hsv"])
        return int(cv2.countNonZero(mask))

    @staticmethod
    def _crop_jersey(img: np.ndarray) -> np.ndarray:
        """Recorta a faixa do torso, evitando cabeça, shorts e gramado ao redor."""
        h, w = img.shape[:2]
        return img[int(h * 0.15):int(h * 0.60), int(w * 0.10):int(w * 0.90)]
