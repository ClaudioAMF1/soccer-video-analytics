"""Testes das métricas táticas em coordenadas métricas."""
import numpy as np
import pytest

from soccer import metricas_taticas as mt


def test_area_de_quadrado_conhecido():
    quadrado = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]])
    assert mt.area_ocupacao(quadrado) == pytest.approx(100.0)


def test_area_zero_para_configuracoes_degeneradas():
    assert mt.area_ocupacao(np.array([[1.0, 1.0], [2.0, 2.0]])) == 0.0
    colineares = np.array([[0.0, 0.0], [1.0, 1.0], [2.0, 2.0], [3.0, 3.0]])
    assert mt.area_ocupacao(colineares) == 0.0


def test_largura_e_profundidade():
    pos = np.array([[10.0, 20.0], [40.0, 55.0], [25.0, 30.0]])
    assert mt.profundidade(pos) == 30.0
    assert mt.largura(pos) == 35.0


def test_invariancia_a_translacao():
    """Métricas de forma não podem depender de onde a equipe está no campo."""
    pos = np.array([[10.0, 10.0], [20.0, 15.0], [15.0, 25.0], [25.0, 20.0]])
    deslocada = pos + np.array([30.0, 12.0])
    assert mt.area_ocupacao(deslocada) == pytest.approx(mt.area_ocupacao(pos))
    assert mt.largura(deslocada) == mt.largura(pos)
    assert mt.dispersao(deslocada) == pytest.approx(mt.dispersao(pos))


def test_area_escala_com_o_quadrado():
    pos = np.array([[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]])
    assert mt.area_ocupacao(pos * 2) == pytest.approx(4 * mt.area_ocupacao(pos))


def test_centroide_e_distancia_entre_equipes():
    a = np.array([[0.0, 0.0], [10.0, 0.0]])
    b = np.array([[0.0, 20.0], [10.0, 20.0]])
    assert np.allclose(mt.centroide(a), [5.0, 0.0])
    assert mt.distancia_entre_centroides(a, b) == 20.0


def test_resumo_preserva_fracao_visivel():
    """A proporção do elenco detectada acompanha a métrica, e não se perde."""
    pos = np.array([[10.0, 10.0], [20.0, 20.0], [30.0, 10.0]])
    r = mt.resumo_equipe(pos, fracao_visivel=0.6)
    assert r["fracao_visivel"] == 0.6
    assert r["n_atletas"] == 3
