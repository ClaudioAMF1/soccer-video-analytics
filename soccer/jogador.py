"""Representação de um atleta detectado e rastreado."""
from __future__ import annotations

import numpy as np

from soccer.desenho import Desenho

COR_NAO_CLASSIFICADO = (128, 128, 128)


class Jogador:
    def __init__(self, detection):
        self.detection = detection
        self.time = detection.data.get("team") if detection is not None else None

    @property
    def centro(self) -> np.ndarray | None:
        """Centro da caixa delimitadora, em pixels."""
        if not self.detection:
            return None
        (x1, y1), (x2, y2) = self.detection.points
        return np.array([(x1 + x2) / 2.0, (y1 + y2) / 2.0])

    @property
    def ponto_apoio(self) -> np.ndarray | None:
        """Ponto médio da aresta inferior da caixa, em pixels.

        Aproxima o contato dos pés com o gramado, que é o ponto fisicamente
        correto para projetar no plano do campo. O centro da caixa fica na
        altura do tronco e, sob perspectiva, projeta-se vários metros além da
        posição real do atleta.
        """
        if not self.detection:
            return None
        (x1, _), (x2, y2) = self.detection.points
        return np.array([(x1 + x2) / 2.0, y2])

    def posicao_campo(self, homografia: np.ndarray) -> np.ndarray | None:
        """Posição do atleta no gramado, em metros."""
        apoio = self.ponto_apoio
        if apoio is None or homografia is None:
            return None
        from pitch.homografia import projetar

        return projetar(homografia, apoio)[0]

    def distancia_para_bola(self, bola, homografia: np.ndarray | None = None) -> float:
        """Distância até a bola, em metros se houver homografia, senão em pixels."""
        if bola is None or bola.centro is None:
            return float("inf")

        if homografia is not None:
            from pitch.homografia import projetar

            p_jog = self.posicao_campo(homografia)
            p_bola = projetar(homografia, np.asarray(bola.centro, dtype=float))[0]
            if p_jog is None or np.isnan(p_jog).any() or np.isnan(p_bola).any():
                return float("inf")
            return float(np.linalg.norm(p_jog - p_bola))

        if self.centro is None:
            return float("inf")
        return float(np.linalg.norm(self.centro - np.asarray(bola.centro, dtype=float)))

    # ------------------------------------------------------------------ #
    def desenhar(self, frame, **kwargs):
        if not self.detection:
            return frame
        cor = self.time.cor if self.time else COR_NAO_CLASSIFICADO
        return Desenho.desenhar_deteccao(self.detection, frame, cor=cor)

    def desenhar_ponteiro(self, frame):
        if self.detection and self.time:
            return Desenho.desenhar_ponteiro(self.detection, frame, self.time.cor)
        return frame

    @staticmethod
    def criar_lista_de_deteccoes(detections, times) -> list["Jogador"]:
        """Converte detecções classificadas em atletas, associando a equipe.

        Detecções cuja classificação não corresponde a nenhuma equipe (árbitro,
        ou recorte não classificável) permanecem com `time = None` e são
        excluídas das métricas táticas, mas seguem sendo desenhadas.
        """
        jogadores = []
        for det in detections:
            nome_time = det.data.get("classification")
            if nome_time is not None:
                det.data["team"] = next((t for t in times if t.nome == nome_time), None)
            jogadores.append(Jogador(det))
        return jogadores
