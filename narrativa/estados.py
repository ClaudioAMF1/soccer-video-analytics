"""Máquina de estados narrativos da jogada.

Cada estado corresponde a uma visualização e a uma legenda em linguagem comum,
exibidas ao espectador leigo sobre o vídeo. Os gatilhos são grandezas no plano
do campo, em metros, e por isso carregam o erro do registro. Dois mecanismos
impedem que esse erro faça a visualização piscar diante do espectador:

- **Faixa de histerese** nos limiares: entra-se na zona de finalização a 20 m
  do gol com o defensor mais próximo a pelo menos 5 m, mas só se sai dela acima
  de 23 m ou com um defensor a menos de 3,5 m. Um corte único em 5 m, sobre uma
  distância medida com cerca de 1 m de erro, alternaria de estado a cada quadro
  sempre que o defensor estivesse perto do limite.
- **Confirmação temporal**: um estado novo só é adotado após persistir por um
  número mínimo de quadros consecutivos.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class EstadoNarrativo(Enum):
    BOLA_MORTA = "bola_morta"
    DISPUTA = "disputa"
    CONSTRUCAO = "construcao"
    ATAQUE = "ataque"
    TRANSICAO = "transicao"
    FINALIZACAO = "finalizacao"


@dataclass(frozen=True)
class ParametrosNarrativa:
    """Limiares da narrativa, em metros e segundos. Hiperparâmetros do artigo."""

    raio_finalizacao_entrada: float = 20.0
    raio_finalizacao_saida: float = 23.0
    folga_entrada: float = 5.0
    folga_saida: float = 3.5
    duracao_transicao: float = 3.0
    quadros_confirmacao: int = 5
    comprimento: float = 105.0
    largura: float = 68.0

    def __post_init__(self) -> None:
        if self.raio_finalizacao_saida < self.raio_finalizacao_entrada:
            raise ValueError("o raio de saída deve ser maior ou igual ao de entrada")
        if self.folga_saida > self.folga_entrada:
            raise ValueError("a folga de saída deve ser menor ou igual à de entrada")
        if self.quadros_confirmacao < 1:
            raise ValueError("quadros_confirmacao deve ser ao menos 1")


class MaquinaNarrativa:
    """Acompanha a jogada quadro a quadro e decide o estado narrativo.

    Args:
        direcao_ataque: equipe -> +1 se ataca no sentido de x crescente
            (gol adversário em x = comprimento), -1 no sentido oposto.
    """

    def __init__(self, direcao_ataque: dict[int, int], par: ParametrosNarrativa | None = None):
        if any(d not in (1, -1) for d in direcao_ataque.values()):
            raise ValueError("direcao_ataque deve conter apenas +1 ou -1")
        self.direcao = dict(direcao_ataque)
        self.par = par or ParametrosNarrativa()

        self.estado = EstadoNarrativo.BOLA_MORTA
        self.equipe: int | None = None

        # O candidato é o par (estado, equipe): a equipe narrada só muda junto
        # com o estado confirmado. Confirmar só o estado deixava a legenda
        # atribuir o ataque de uma equipe à outra durante a janela de
        # confirmação, e fundia a transição de uma equipe com a da outra.
        self._candidato: tuple[EstadoNarrativo, int | None] = (self.estado, None)
        self._quadros_candidato = 0
        self._zona_finalizacao = False
        self._ultima_posse: int | None = None
        self._instante_troca: float | None = None

    # ------------------------------------------------------------------ #
    def gol_adversario(self, equipe: int) -> np.ndarray:
        x = self.par.comprimento if self.direcao[equipe] == 1 else 0.0
        return np.array([x, self.par.largura / 2.0])

    def progresso(self, equipe: int, x: float) -> float:
        """Fração do campo percorrida no sentido do ataque, em [0, 1]."""
        f = x / self.par.comprimento
        return f if self.direcao[equipe] == 1 else 1.0 - f

    def _atualizar_zona(self, equipe: int, bola: np.ndarray, adversarios: np.ndarray) -> None:
        d_gol = float(np.linalg.norm(bola - self.gol_adversario(equipe)))
        if len(adversarios):
            d_def = float(np.sqrt(((adversarios - bola) ** 2).sum(axis=1)).min())
        else:
            d_def = float("inf")

        p = self.par
        if self._zona_finalizacao:
            self._zona_finalizacao = d_gol <= p.raio_finalizacao_saida and d_def >= p.folga_saida
        else:
            self._zona_finalizacao = d_gol <= p.raio_finalizacao_entrada and d_def >= p.folga_entrada

    def _candidato_do_quadro(self, t, posse, bola, adversarios) -> EstadoNarrativo:
        if bola is None:
            self._zona_finalizacao = False
            return EstadoNarrativo.BOLA_MORTA
        if posse is None:
            self._zona_finalizacao = False
            return EstadoNarrativo.DISPUTA

        if self._ultima_posse is not None and posse != self._ultima_posse:
            self._instante_troca = t
        self._ultima_posse = posse

        self._atualizar_zona(posse, bola, adversarios)

        # Prioridade: finalização > transição > posição no campo.
        if self._zona_finalizacao:
            return EstadoNarrativo.FINALIZACAO
        if self._instante_troca is not None and t - self._instante_troca < self.par.duracao_transicao:
            return EstadoNarrativo.TRANSICAO
        if self.progresso(posse, bola[0]) >= 0.5:
            return EstadoNarrativo.ATAQUE
        return EstadoNarrativo.CONSTRUCAO

    def atualizar(
        self,
        t: float,
        posse: int | None,
        bola: np.ndarray | None,
        adversarios: np.ndarray | None = None,
    ) -> EstadoNarrativo:
        """Avança um quadro.

        Args:
            t: instante, em segundos.
            posse: equipe com a posse já confirmada (ver `soccer.partida`), ou None.
            bola: posição da bola no campo, em metros, ou None se não detectada.
            adversarios: (N, 2) posições da equipe sem a posse, em metros.
        """
        b = None if bola is None else np.asarray(bola, dtype=float)
        adv = np.zeros((0, 2)) if adversarios is None else np.atleast_2d(np.asarray(adversarios, dtype=float))
        estado = self._candidato_do_quadro(t, posse, b, adv)
        # Estados sem posse não têm equipe; os demais pertencem a quem tem a bola.
        equipe = posse if estado not in (EstadoNarrativo.BOLA_MORTA, EstadoNarrativo.DISPUTA) else None
        candidato = (estado, equipe)

        if candidato == self._candidato:
            self._quadros_candidato += 1
        else:
            self._candidato = candidato
            self._quadros_candidato = 1

        if candidato != (self.estado, self.equipe) and self._quadros_candidato >= self.par.quadros_confirmacao:
            self.estado, self.equipe = candidato
        return self.estado


_FRASES = {
    EstadoNarrativo.BOLA_MORTA: "Bola parada ou fora do enquadramento.",
    EstadoNarrativo.DISPUTA: "Bola em disputa: nenhuma equipe tem o controle.",
    EstadoNarrativo.CONSTRUCAO: "{eq} constrói a jogada no próprio campo.",
    EstadoNarrativo.ATAQUE: "{eq} ataca no campo adversário.",
    EstadoNarrativo.TRANSICAO: "Troca de posse: {eq} acabou de recuperar a bola.",
    EstadoNarrativo.FINALIZACAO: "{eq} chega perto do gol com espaço livre para finalizar.",
}


def legenda(estado: EstadoNarrativo, nome_equipe: str | None = None,
            controle_frac: float | None = None) -> str:
    """Frase em linguagem comum para o estado, exibida ao espectador."""
    texto = _FRASES[estado].format(eq=nome_equipe or "A equipe")
    if controle_frac is not None and nome_equipe and estado not in (
        EstadoNarrativo.BOLA_MORTA, EstadoNarrativo.DISPUTA
    ):
        texto += f" {nome_equipe} controla {round(controle_frac * 100)}% do campo."
    return texto
