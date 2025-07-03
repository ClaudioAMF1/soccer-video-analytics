# soccer/jogador.py
import numpy as np
from soccer.desenho import Desenho

class Jogador:
    def __init__(self, detection):
        self.detection = detection
        self.time = detection.data.get("team")

    @property
    def centro(self) -> np.ndarray:
        if not self.detection: return None
        x1, y1 = self.detection.points[0]; x2, y2 = self.detection.points[1]
        return np.array([(x1 + x2) / 2, (y1 + y2) / 2])

    def distancia_para_bola(self, bola) -> float:
        if self.centro is None or bola.centro is None: return float('inf')
        return np.linalg.norm(self.centro - bola.centro)

    def desenhar(self, frame, **kwargs):
        if self.detection:
            # Garante que o jogador seja desenhado com a cor do seu time, ou cinza se não classificado
            cor = self.time.cor if self.time else (128, 128, 128)
            return Desenho.desenhar_deteccao(self.detection, frame, cor=cor)
        return frame

    def desenhar_ponteiro(self, frame):
        if self.detection and self.time:
            return Desenho.desenhar_ponteiro(self.detection, frame, self.time.cor)
        return frame

    @staticmethod
    def criar_lista_de_deteccoes(detections, times):
        jogadores = []
        for det in detections:
            if "classification" in det.data:
                nome_time = det.data["classification"]
                det.data["team"] = next((t for t in times if t.nome == nome_time), None)
            jogadores.append(Jogador(det))
        return jogadores