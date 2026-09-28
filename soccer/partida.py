"""Estado da partida, com posse de bola modelada como máquina de estados.

A implementação anterior atribuía `time_com_posse` e nunca voltava a `None`:
uma vez que uma equipe tocasse na bola, o contador passava a incrementar em
todo quadro subsequente, inclusive com a bola fora de jogo, em faltas e em
replays. O que o painel exibia não era posse de bola, e sim "qual equipe tocou
por último". Este módulo substitui aquela lógica por estados explícitos, com
histerese temporal e limiar expresso em metros quando há homografia disponível.
"""
from __future__ import annotations

from enum import Enum

import numpy as np

from soccer.bola import Bola
from soccer.desenho import Desenho
from soccer.time import Time
from soccer.visualizacao_tatica import VisualizacaoTatica


class EstadoPosse(Enum):
    """Estados possíveis da posse de bola."""

    BOLA_MORTA = "bola_morta"      # bola não detectada
    EM_DISPUTA = "em_disputa"      # detectada, sem controle claro
    CONTROLADA = "controlada"      # uma equipe controla


class Partida:
    """Agrega o estado de uma partida ao longo do vídeo.

    Args:
        em_metros: força a interpretação das distâncias em metros mesmo sem
            homografia, para quando os atletas já chegam com posições no campo.
        limiar_posse_m: distância, em metros, abaixo da qual se considera que
            o atleta controla a bola. Usado quando `homografia` é fornecida.
        limiar_posse_px: alternativa em pixels, usada apenas quando não há
            homografia. Não é invariante à escala — 120 px equivalem a cerca de
            2 m para um atleta ao fundo e a menos de 0,5 m para um em primeiro
            plano — e por isso serve apenas como modo degradado.
        quadros_confirmacao: número de quadros consecutivos exigidos para
            confirmar uma troca de posse. A histerese evita que oscilações de
            detecção em disputas de bola produzam trocas espúrias.
        quadros_ate_bola_morta: quadros sem detecção da bola após os quais a
            posse é encerrada.
    """

    def __init__(
        self,
        time_casa: Time,
        time_visitante: Time,
        fps: float,
        homografia: np.ndarray | None = None,
        em_metros: bool | None = None,
        limiar_posse_m: float = 2.0,
        limiar_posse_px: float = 120.0,
        quadros_confirmacao: int = 3,
        quadros_ate_bola_morta: int = 10,
    ):
        self.times = [time_casa, time_visitante]
        self.time_casa = time_casa
        self.time_visitante = time_visitante
        self.fps = fps if fps and fps > 0 else 30.0

        self.homografia = homografia
        self.em_metros = em_metros
        self.limiar_posse_m = limiar_posse_m
        self.limiar_posse_px = limiar_posse_px
        self.quadros_confirmacao = quadros_confirmacao
        self.quadros_ate_bola_morta = quadros_ate_bola_morta

        self.duracao_total_frames = 0
        self.quadros_com_posse = 0
        self.bola: Bola | None = None
        self.jogador_mais_proximo = None
        self.time_com_posse: Time | None = None
        self.estado = EstadoPosse.BOLA_MORTA

        self._candidato: Time | None = None
        self._quadros_candidato = 0
        self._quadros_sem_bola = 0

        self.visualizador_tatico = VisualizacaoTatica()

    # ------------------------------------------------------------------ #
    @property
    def limiar_efetivo(self) -> float:
        """Limiar de posse na unidade em uso (metros ou pixels).

        Em metros quando há homografia, ou quando `em_metros=True` indica que as
        distâncias já chegam medidas no plano do campo (caso do exportador).
        """
        usa_metros = self.em_metros if self.em_metros is not None else self.homografia is not None
        return self.limiar_posse_m if usa_metros else self.limiar_posse_px

    def _distancia(self, jogador, bola: Bola) -> float:
        """Distância jogador-bola, em metros se houver homografia, senão em pixels."""
        return jogador.distancia_para_bola(bola, homografia=self.homografia)

    # ------------------------------------------------------------------ #
    def atualizar(self, jogadores: list, bola: Bola) -> None:
        """Avança o estado da partida em um quadro."""
        self.duracao_total_frames += 1
        self.bola = bola

        if bola is None or bola.detection is None:
            self._quadros_sem_bola += 1
            if self._quadros_sem_bola >= self.quadros_ate_bola_morta:
                self._encerrar_posse()
            self._contabilizar()
            return

        self._quadros_sem_bola = 0

        classificados = [j for j in jogadores if j.time is not None and j.detection]
        if not classificados:
            self.jogador_mais_proximo = None
            self._registrar_candidato(None)
            self._contabilizar()
            return

        proximo = min(classificados, key=lambda j: self._distancia(j, bola))
        distancia = self._distancia(proximo, bola)

        if distancia < self.limiar_efetivo:
            self.jogador_mais_proximo = proximo
            self._registrar_candidato(proximo.time)
        else:
            # Bola em trânsito (um passe, um chute): a posse não muda. No
            # futebol, a equipe que passa a bola continua com a posse até que o
            # adversário a domine; encerrá-la aqui faria cada passe aparecer
            # como perda de posse. O candidato é descartado para que contatos
            # esparsos, separados por trânsito, não se acumulem numa troca.
            self.jogador_mais_proximo = None
            self._candidato = None
            self._quadros_candidato = 0

        self._contabilizar()

    def _registrar_candidato(self, time: Time | None) -> None:
        """Aplica a histerese antes de confirmar uma mudança de posse."""
        if time == self.time_com_posse:
            self._candidato = None
            self._quadros_candidato = 0
            if time is not None:
                self.estado = EstadoPosse.CONTROLADA
            return

        if time == self._candidato:
            self._quadros_candidato += 1
        else:
            self._candidato = time
            self._quadros_candidato = 1

        if self._quadros_candidato >= self.quadros_confirmacao:
            self.time_com_posse = time
            self.estado = EstadoPosse.CONTROLADA if time else EstadoPosse.EM_DISPUTA
            self._candidato = None
            self._quadros_candidato = 0

    def _encerrar_posse(self) -> None:
        self.time_com_posse = None
        self.jogador_mais_proximo = None
        self.estado = EstadoPosse.BOLA_MORTA
        self._candidato = None
        self._quadros_candidato = 0

    def _contabilizar(self) -> None:
        """Incrementa os contadores apenas quando há controle efetivo."""
        if self.time_com_posse is not None:
            self.time_com_posse.posse_de_bola_frames += 1
            self.quadros_com_posse += 1

    # ------------------------------------------------------------------ #
    def percentual_posse(self, time: Time) -> float:
        """Posse da equipe como fração dos quadros em que houve controle.

        O denominador é o tempo de bola efetivamente controlada, e não a
        duração do vídeo: é assim que a posse é definida na prática, e é o que
        faz as duas equipes somarem 100%.
        """
        if self.quadros_com_posse == 0:
            return 0.0
        return time.posse_de_bola_frames / self.quadros_com_posse

    # ------------------------------------------------------------------ #
    def desenhar_elementos(self, frame, jogadores, args):
        if self.bola and getattr(args, "rastro_bola", False):
            self.bola.definir_cor(self)
            frame = self.bola.desenhar(frame)

        if getattr(args, "linhas_formacao", False) or getattr(args, "poligonos_formacao", False):
            frame = self.visualizador_tatico.desenhar_analise_tatica(
                frame, jogadores, self.times, args
            )

        if self.jogador_mais_proximo and getattr(args, "posse", False):
            frame = self.jogador_mais_proximo.desenhar_ponteiro(frame)

        if getattr(args, "posse", False):
            frame = Desenho.desenhar_painel_posse(frame, self)

        return frame
