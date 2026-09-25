"""Controle de espaço por tempo até a interceptação.

Implementa duas formulações, ambas sobre posições e velocidades em coordenadas
métricas do campo:

- **Região dominante** (determinística), no espírito de Taki e Hasegawa (2000):
  cada célula pertence integralmente ao atleta que a alcança primeiro.
- **Controle probabilístico**, no espírito de Spearman et al. (2017): o tempo
  até o controle é convertido em probabilidade, distribuindo a posse da célula
  entre os atletas.

A entrada exige metros e metros por segundo. Alimentar estas funções com
coordenadas de pixel produz números sem significado físico — é exatamente o
erro que o artigo se propõe a quantificar.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ParametrosMovimento:
    """Parâmetros do modelo de movimento do atleta.

    Os valores padrão correspondem a um jogador profissional de futebol de
    campo. São hiperparâmetros do modelo e devem ser reportados no artigo.
    """

    velocidade_max: float = 8.0      # m/s
    aceleracao_max: float = 7.0      # m/s^2
    tempo_reacao: float = 0.7        # s
    temperatura: float = 0.45        # s, escala da conversão tempo -> probabilidade

    def __post_init__(self) -> None:
        if self.velocidade_max <= 0 or self.aceleracao_max <= 0:
            raise ValueError("velocidade_max e aceleracao_max devem ser positivas")
        if self.tempo_reacao < 0:
            raise ValueError("tempo_reacao não pode ser negativo")
        if self.temperatura <= 0:
            raise ValueError("temperatura deve ser positiva")


def _tempo_percurso(distancia: np.ndarray, par: ParametrosMovimento) -> np.ndarray:
    """Tempo para percorrer `distancia` partindo do repouso.

    Fase de aceleração constante até `velocidade_max`, depois velocidade
    constante.
    """
    d = np.asarray(distancia, dtype=float)
    d_acel = par.velocidade_max ** 2 / (2.0 * par.aceleracao_max)

    t_curta = np.sqrt(np.maximum(2.0 * d, 0.0) / par.aceleracao_max)
    t_longa = (
        par.velocidade_max / par.aceleracao_max
        + (d - d_acel) / par.velocidade_max
    )
    return np.where(d <= d_acel, t_curta, t_longa)


def tempo_ate_interceptar(
    posicoes: np.ndarray,
    velocidades: np.ndarray | None,
    alvos: np.ndarray,
    par: ParametrosMovimento | None = None,
) -> np.ndarray:
    """Tempo, em segundos, para cada atleta alcançar cada célula-alvo.

    Durante o tempo de reação o atleta mantém a velocidade corrente; só então
    inicia o deslocamento em direção ao alvo. É esse termo que faz a direção do
    movimento importar — um jogador próximo mas correndo para longe do alvo
    chega depois de um mais distante que já se desloca em sua direção.

    Args:
        posicoes: (N, 2) em metros.
        velocidades: (N, 2) em m/s, ou None para atletas parados.
        alvos: (M, 2) em metros.

    Returns:
        Matriz (N, M) de tempos em segundos.
    """
    par = par or ParametrosMovimento()
    p = np.atleast_2d(np.asarray(posicoes, dtype=float))
    a = np.atleast_2d(np.asarray(alvos, dtype=float))

    if velocidades is None:
        v = np.zeros_like(p)
    else:
        v = np.atleast_2d(np.asarray(velocidades, dtype=float))
        if v.shape != p.shape:
            raise ValueError("velocidades deve ter o mesmo formato que posicoes")

    # Posição projetada ao fim do tempo de reação.
    p_reacao = p + v * par.tempo_reacao

    deltas = a[None, :, :] - p_reacao[:, None, :]
    distancias = np.sqrt((deltas ** 2).sum(axis=2))

    return par.tempo_reacao + _tempo_percurso(distancias, par)


def regiao_dominante(
    posicoes: np.ndarray,
    velocidades: np.ndarray | None,
    alvos: np.ndarray,
    par: ParametrosMovimento | None = None,
) -> np.ndarray:
    """Índice do atleta que domina cada célula (formulação determinística)."""
    tempos = tempo_ate_interceptar(posicoes, velocidades, alvos, par)
    return np.argmin(tempos, axis=0)


def controle_espaco(
    posicoes: np.ndarray,
    velocidades: np.ndarray | None,
    alvos: np.ndarray,
    par: ParametrosMovimento | None = None,
) -> np.ndarray:
    """Probabilidade de cada atleta controlar cada célula.

    A conversão de tempo em probabilidade é uma softmax sobre o tempo negativo,
    com escala `par.temperatura`. No limite de temperatura tendendo a zero, a
    formulação recupera a região dominante.

    Returns:
        Matriz (N, M) cujas colunas somam 1.
    """
    par = par or ParametrosMovimento()
    tempos = tempo_ate_interceptar(posicoes, velocidades, alvos, par)

    # Subtrair o mínimo por coluna evita estouro na exponencial sem alterar
    # o resultado da softmax.
    escores = -(tempos - tempos.min(axis=0, keepdims=True)) / par.temperatura
    pesos = np.exp(escores)
    return pesos / pesos.sum(axis=0, keepdims=True)


def controle_por_equipe(
    posicoes: np.ndarray,
    velocidades: np.ndarray | None,
    equipes: np.ndarray,
    alvos: np.ndarray,
    equipe_alvo: int = 0,
    par: ParametrosMovimento | None = None,
) -> np.ndarray:
    """Probabilidade de `equipe_alvo` controlar cada célula.

    Args:
        equipes: (N,) com o identificador de equipe de cada atleta.

    Returns:
        Vetor (M,) de probabilidades em [0, 1].
    """
    controle = controle_espaco(posicoes, velocidades, alvos, par)
    mascara = np.asarray(equipes) == equipe_alvo
    if not mascara.any():
        return np.zeros(controle.shape[1])
    return controle[mascara].sum(axis=0)


def fracao_campo_controlada(
    posicoes: np.ndarray,
    velocidades: np.ndarray | None,
    equipes: np.ndarray,
    alvos: np.ndarray,
    equipe_alvo: int = 0,
    par: ParametrosMovimento | None = None,
) -> float:
    """Fração do campo controlada por `equipe_alvo`, em [0, 1].

    Métrica agregada de nível de equipe: a média do controle sobre todas as
    células da grade.
    """
    por_celula = controle_por_equipe(
        posicoes, velocidades, equipes, alvos, equipe_alvo, par
    )
    return float(por_celula.mean())
