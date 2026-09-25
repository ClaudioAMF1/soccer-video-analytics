"""Testes de regressão da máquina de estados de posse.

A implementação anterior nunca devolvia `time_com_posse` a `None`. Uma vez que
uma equipe tocasse na bola, o contador incrementava em todo quadro seguinte —
com a bola fora, em faltas, em replays. Os testes abaixo fixam o comportamento
correto para que a regressão não volte.
"""
import numpy as np
import pytest

pytest.importorskip("PIL", reason="a camada de desenho exige Pillow")

from soccer.partida import EstadoPosse, Partida  # noqa: E402
from soccer.time import Time  # noqa: E402


class _DeteccaoFalsa:
    def __init__(self):
        self.points = np.array([[0.0, 0.0], [10.0, 20.0]])
        self.data = {}


class _BolaFalsa:
    def __init__(self, presente=True):
        self.detection = _DeteccaoFalsa() if presente else None
        self.centro = np.array([50.0, 50.0]) if presente else None


class _JogadorFalso:
    """Atleta com distância até a bola fixada pelo teste."""

    def __init__(self, time, distancia):
        self.time = time
        self.detection = _DeteccaoFalsa()
        self._distancia = distancia

    def distancia_para_bola(self, bola, homografia=None):
        return self._distancia


@pytest.fixture
def partida():
    casa = Time("Casa", "CAS", (255, 0, 0))
    fora = Time("Fora", "FOR", (0, 0, 255))
    return Partida(casa, fora, fps=30.0, quadros_confirmacao=3, quadros_ate_bola_morta=5)


def _rodar(p, jogadores, bola, n):
    for _ in range(n):
        p.atualizar(jogadores, bola)


def test_comeca_sem_posse(partida):
    assert partida.time_com_posse is None
    assert partida.estado is EstadoPosse.BOLA_MORTA
    assert partida.quadros_com_posse == 0


def test_histerese_exige_quadros_consecutivos(partida):
    casa = partida.time_casa
    jog = [_JogadorFalso(casa, 1.0)]
    bola = _BolaFalsa()

    partida.atualizar(jog, bola)
    assert partida.time_com_posse is None, "não pode confirmar posse num só quadro"
    _rodar(partida, jog, bola, 2)
    assert partida.time_com_posse is casa


def test_contador_nao_avanca_sem_controle(partida):
    """Com a bola longe de todos, ninguém acumula posse."""
    jog = [_JogadorFalso(partida.time_casa, 500.0)]
    _rodar(partida, jog, _BolaFalsa(), 50)
    assert partida.time_casa.posse_de_bola_frames == 0
    assert partida.quadros_com_posse == 0


def test_bola_ausente_encerra_a_posse(partida):
    """O defeito original: a posse persistia indefinidamente após o último toque."""
    casa = partida.time_casa
    jog = [_JogadorFalso(casa, 1.0)]
    _rodar(partida, jog, _BolaFalsa(), 10)
    assert partida.time_com_posse is casa
    acumulado = casa.posse_de_bola_frames

    _rodar(partida, jog, _BolaFalsa(presente=False), 20)
    assert partida.time_com_posse is None
    assert partida.estado is EstadoPosse.BOLA_MORTA
    # Após a bola morta, o contador congela: no máximo os quadros de tolerância.
    assert casa.posse_de_bola_frames - acumulado <= partida.quadros_ate_bola_morta


def test_troca_de_posse_entre_equipes(partida):
    casa, fora = partida.time_casa, partida.time_visitante
    bola = _BolaFalsa()
    _rodar(partida, [_JogadorFalso(casa, 1.0)], bola, 10)
    assert partida.time_com_posse is casa
    _rodar(partida, [_JogadorFalso(fora, 1.0)], bola, 10)
    assert partida.time_com_posse is fora


def test_percentuais_somam_cem(partida):
    casa, fora = partida.time_casa, partida.time_visitante
    bola = _BolaFalsa()
    _rodar(partida, [_JogadorFalso(casa, 1.0)], bola, 30)
    _rodar(partida, [_JogadorFalso(fora, 1.0)], bola, 10)
    total = partida.percentual_posse(casa) + partida.percentual_posse(fora)
    assert total == pytest.approx(1.0)
    assert partida.percentual_posse(casa) > partida.percentual_posse(fora)


def test_atletas_nao_classificados_sao_ignorados(partida):
    """Sem equipe atribuída, o atleta não pode gerar posse para ninguém."""
    _rodar(partida, [_JogadorFalso(None, 0.5)], _BolaFalsa(), 20)
    assert partida.time_com_posse is None


def test_limiar_em_metros_quando_ha_homografia():
    casa = Time("Casa", "CAS", (255, 0, 0))
    fora = Time("Fora", "FOR", (0, 0, 255))
    p = Partida(casa, fora, fps=30.0, homografia=np.eye(3), limiar_posse_m=2.0)
    assert p.limiar_efetivo == 2.0

    sem_h = Partida(casa, fora, fps=30.0, limiar_posse_px=120.0)
    assert sem_h.limiar_efetivo == 120.0


def test_oscilacao_curta_nao_troca_a_posse(partida):
    """Uma detecção isolada da outra equipe não pode roubar a posse."""
    casa, fora = partida.time_casa, partida.time_visitante
    bola = _BolaFalsa()
    _rodar(partida, [_JogadorFalso(casa, 1.0)], bola, 10)
    partida.atualizar([_JogadorFalso(fora, 1.0)], bola)
    assert partida.time_com_posse is casa
