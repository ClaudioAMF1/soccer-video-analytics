# soccer/bola.py
import numpy as np
import PIL
from PIL import ImageDraw
from soccer.desenho import Desenho

class Bola:
    def __init__(self, detection):
        self.detection = detection
        self.cor = (255, 255, 255) # Cor padrão branca para bola sem posse
        self.pontos_rastro = []
        self.max_comprimento_rastro = 20
        self.rastro_habilitado = True

    def definir_cor(self, partida):
        """ Define a cor da bola (e do rastro) com base no time que tem a posse. """
        if partida and partida.time_com_posse:
            self.cor = partida.time_com_posse.cor
        else:
            self.cor = (255, 255, 255) # Bola branca se ninguém tem a posse
        
        if self.detection:
            # A cor da caixa da bola em si também muda
            self.detection.data["color"] = self.cor

    @property
    def centro(self) -> tuple:
        if self.detection is None: return None
        x1, y1 = self.detection.points[0]; x2, y2 = self.detection.points[1]
        return (np.round_((x1 + x2) / 2), np.round_((y1 + y2) / 2))

    def atualizar_rastro(self):
        if self.detection and self.rastro_habilitado and self.centro is not None:
            self.pontos_rastro.append(self.centro)
            if len(self.pontos_rastro) > self.max_comprimento_rastro:
                self.pontos_rastro.pop(0)

    def desenhar_rastro(self, frame: PIL.Image.Image) -> PIL.Image.Image:
        """ (REQUISITO DESEJÁVEL) Desenha o rastro da bola com a cor da posse. """
        if len(self.pontos_rastro) < 2: return frame
        desenhador = ImageDraw.Draw(frame, "RGBA")
        for i in range(1, len(self.pontos_rastro)):
            alfa = int(255 * (i / len(self.pontos_rastro)))
            largura = max(1, int(8 * (i / len(self.pontos_rastro))))
            cor_com_alfa = self.cor + (alfa,)
            ponto_inicial = tuple(map(int, self.pontos_rastro[i - 1]))
            ponto_final = tuple(map(int, self.pontos_rastro[i]))
            desenhador.line([ponto_inicial, ponto_final], fill=cor_com_alfa, width=largura)
        return frame

    def desenhar(self, frame: PIL.Image.Image) -> PIL.Image.Image:
        self.atualizar_rastro()
        if self.rastro_habilitado:
            frame = self.desenhar_rastro(frame)
        # Desenha a detecção da bola (caixa) se ela existir, por cima do rastro
        if self.detection:
            frame = Desenho.desenhar_deteccao(self.detection, frame, self.cor)
        return frame