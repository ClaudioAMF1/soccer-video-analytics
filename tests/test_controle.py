"""Testes do modelo de controle de espaço."""
import numpy as np
import pytest

from controle import (
    ParametrosMovimento, controle_espaco, controle_por_equipe,
    fracao_campo_controlada, regiao_dominante, tempo_ate_interceptar,
)
from pitch import ModeloCampo

PAR = ParametrosMovimento()


def test_parado_o_mais_proximo_chega_antes():
    pos = np.array([[50.0, 30.0], [54.0, 30.0]])
    alvo = np.array([[60.0, 30.0]])
    t = tempo_ate_interceptar(pos, None, alvo, PAR).ravel()
    assert t[1] < t[0]


def test_direcao_do_movimento_inverte_a_ordem():
    """O jogador mais distante, correndo para o alvo, chega antes.

    É esta propriedade que torna o modelo dependente de velocidade — e,
    portanto, de vídeo. Uma imagem estática não a captura.
    """
    pos = np.array([[50.0, 30.0], [54.0, 30.0]])
    vel = np.array([[6.0, 0.0], [-6.0, 0.0]])
    alvo = np.array([[60.0, 30.0]])
    t = tempo_ate_interceptar(pos, vel, alvo, PAR).ravel()
    assert t[0] < t[1]


def test_tempo_inclui_reacao():
    pos = np.array([[10.0, 10.0]])
    t = tempo_ate_interceptar(pos, None, pos, PAR).ravel()[0]
    assert t == pytest.approx(PAR.tempo_reacao)


def test_controle_soma_um_por_celula():
    pos = np.random.default_rng(0).uniform([0, 0], [105, 68], (10, 2))
    grade = ModeloCampo().grade(5.0)
    c = controle_espaco(pos, None, grade, PAR)
    assert np.allclose(c.sum(axis=0), 1.0)


def test_controle_das_duas_equipes_soma_um():
    pos = np.random.default_rng(1).uniform([0, 0], [105, 68], (12, 2))
    eq = np.array([0] * 6 + [1] * 6)
    grade = ModeloCampo().grade(5.0)
    a = controle_por_equipe(pos, None, eq, grade, 0, PAR)
    b = controle_por_equipe(pos, None, eq, grade, 1, PAR)
    assert np.allclose(a + b, 1.0)


def test_equipe_ausente_nao_controla_nada():
    pos = np.array([[10.0, 10.0], [20.0, 20.0]])
    eq = np.array([0, 0])
    grade = ModeloCampo().grade(10.0)
    assert fracao_campo_controlada(pos, None, eq, grade, 1, PAR) == 0.0


def test_regiao_dominante_atribui_ao_mais_rapido():
    pos = np.array([[10.0, 34.0], [95.0, 34.0]])
    alvos = np.array([[12.0, 34.0], [93.0, 34.0]])
    assert list(regiao_dominante(pos, None, alvos, PAR)) == [0, 1]


def test_temperatura_baixa_converge_para_regiao_dominante():
    """Com temperatura tendendo a zero, o controle vira atribuição dura.

    As células exatamente equidistantes são excluídas: nelas o empate é real e
    0,5/0,5 é a resposta correta, não um defeito de convergência.
    """
    pos = np.array([[10.0, 34.0], [95.0, 34.0]])
    grade = ModeloCampo().grade(5.0)
    frio = ParametrosMovimento(temperatura=0.01)
    c = controle_espaco(pos, None, grade, frio)
    assert np.allclose(c.argmax(axis=0), regiao_dominante(pos, None, grade, frio))

    tempos = tempo_ate_interceptar(pos, None, grade, frio)
    ordenados = np.sort(tempos, axis=0)
    sem_empate = (ordenados[1] - ordenados[0]) > 1e-6
    assert sem_empate.any()
    assert c.max(axis=0)[sem_empate].min() > 0.99


def test_empate_exato_divide_o_controle():
    """Célula equidistante entre dois atletas parados: metade para cada um."""
    pos = np.array([[10.0, 34.0], [90.0, 34.0]])
    meio = np.array([[50.0, 34.0]])
    c = controle_espaco(pos, None, meio, PAR).ravel()
    assert c[0] == pytest.approx(0.5)
    assert c[1] == pytest.approx(0.5)


def test_parametros_invalidos():
    with pytest.raises(ValueError):
        ParametrosMovimento(velocidade_max=0)
    with pytest.raises(ValueError):
        ParametrosMovimento(temperatura=0)


def test_velocidades_com_formato_errado():
    with pytest.raises(ValueError, match="mesmo formato"):
        tempo_ate_interceptar(np.zeros((3, 2)), np.zeros((2, 2)), np.zeros((1, 2)))
