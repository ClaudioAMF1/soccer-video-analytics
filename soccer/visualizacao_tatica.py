# soccer/visualizacao_tatica.py
import numpy as np
import PIL
from PIL import ImageDraw
from scipy.spatial import ConvexHull
import math

class VisualizacaoTatica:
    def __init__(self):
        self.alfa_poligono = 45 # Mais transparente
        self.alfa_linha = 100
        self.max_conexoes_por_jogador = 2
        self.distancia_max_conexao = 350 # AUMENTADO para garantir que as linhas apareçam

    def obter_jogadores_por_time(self, jogadores, time):
        return [j for j in jogadores if j.time == time and j.detection]

    def obter_posicoes_jogadores(self, jogadores):
        return [tuple(j.centro) for j in jogadores if j.centro is not None]

    def desenhar_linhas_conexao(self, img, posicoes, cor):
        if len(posicoes) < 2: return img
        desenhador = ImageDraw.Draw(img, "RGBA")
        cor_com_alfa = cor + (self.alfa_linha,)
        for i, pos1 in enumerate(posicoes):
            distancias = sorted([(math.dist(pos1, pos2), pos2) for j, pos2 in enumerate(posicoes) if i != j and math.dist(pos1, pos2) < self.distancia_max_conexao])
            for k in range(min(self.max_conexoes_por_jogador, len(distancias))):
                desenhador.line([pos1, distancias[k][1]], fill=cor_com_alfa, width=2)
        return img

    def desenhar_poligono_formacao(self, img, posicoes, cor):
        if len(posicoes) < 3: return img
        try:
            pontos_np = np.array(posicoes)
            casco = ConvexHull(pontos_np)
            pontos_casco = [tuple(p) for p in pontos_np[casco.vertices]]
            desenhador = ImageDraw.Draw(img, "RGBA")
            desenhador.polygon(pontos_casco, fill=cor+(self.alfa_poligono,), outline=cor+(self.alfa_poligono+40,), width=2)
            
            # Desenha o centroide do time
            centroide = np.mean(pontos_np, axis=0)
            cx, cy = int(centroide[0]), int(centroide[1])
            raio = 5
            desenhador.ellipse((cx-raio, cy-raio, cx+raio, cy+raio), fill=cor)
        except Exception: pass
        return img

    def desenhar_analise_tatica(self, img, jogadores, times, args):
        for time in times:
            jogadores_time = self.obter_jogadores_por_time(jogadores, time)
            posicoes = self.obter_posicoes_jogadores(jogadores_time)
            if not posicoes: continue
            if args.poligonos_formacao:
                img = self.desenhar_poligono_formacao(img, posicoes, time.cor)
            if args.linhas_formacao:
                img = self.desenhar_linhas_conexao(img, posicoes, time.cor)
        return img