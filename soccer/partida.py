# soccer/partida.py
from soccer.time import Time
from soccer.bola import Bola
from soccer.visualizacao_tatica import VisualizacaoTatica
from soccer.desenho import Desenho

class Partida:
    def __init__(self, time_casa: Time, time_visitante: Time, fps: int):
        self.times = [time_casa, time_visitante]
        self.time_casa = time_casa
        self.time_visitante = time_visitante
        self.fps = fps if fps > 0 else 30.0
        self.duracao_total_frames = 0
        self.bola = None
        self.jogador_mais_proximo = None
        self.time_com_posse = None
        self.limiar_distancia_posse = 120.0
        self.visualizador_tatico = VisualizacaoTatica()

    def atualizar(self, jogadores: list, bola: Bola):
        self.duracao_total_frames += 1
        self.bola = bola
        
        jogador_com_posse_neste_frame = None
        
        # A lógica só é executada se houver jogadores e a bola for detectada
        if jogadores and bola.detection:
            jogadores_com_time = [j for j in jogadores if j.time]
            if jogadores_com_time:
                jogador_candidato = min(jogadores_com_time, key=lambda j: j.distancia_para_bola(bola))
                distancia = jogador_candidato.distancia_para_bola(bola)

                if distancia < self.limiar_distancia_posse:
                    jogador_com_posse_neste_frame = jogador_candidato
                    # ATRIBUI posse ao time do jogador
                    self.time_com_posse = jogador_candidato.time
        
        # O jogador mais próximo só é definido se ele realmente tiver a posse
        self.jogador_mais_proximo = jogador_com_posse_neste_frame
        
        # Incrementa o contador de posse para o time correto (se houver)
        if self.time_com_posse:
            self.time_com_posse.posse_de_bola_frames += 1

    def desenhar_elementos(self, frame, jogadores, args):
        # O rastro da bola é desenhado PRIMEIRO para ficar por baixo de outros elementos
        if self.bola and args.rastro_bola:
            # A cor do rastro é definida aqui, com base na posse atual
            self.bola.definir_cor(self)
            frame = self.bola.desenhar(frame)
        
        # Desenha os polígonos e linhas táticas
        if args.linhas_formacao or args.poligonos_formacao:
            frame = self.visualizador_tatico.desenhar_analise_tatica(frame, jogadores, self.times, args)
        
        # Desenha o ponteiro sobre o jogador com posse
        if self.jogador_mais_proximo and args.posse:
            frame = self.jogador_mais_proximo.desenhar_ponteiro(frame)

        # O painel de posse é desenhado por último para ficar por cima de tudo
        if args.posse:
            frame = Desenho.desenhar_painel_posse(frame, self)
            
        return frame