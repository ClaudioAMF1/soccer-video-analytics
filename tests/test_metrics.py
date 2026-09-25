"""Testes das métricas de avaliação."""
import numpy as np
import pytest

from metrics import acuracia_topk, brier, brier_multiclasse, log_loss
from metrics.registro import erro_por_regiao, estatisticas_erro


def test_brier_perfeito_e_pessimo():
    assert brier(np.array([1.0, 0.0]), np.array([1.0, 0.0])) == 0.0
    assert brier(np.array([0.0, 1.0]), np.array([1.0, 0.0])) == 1.0


def test_brier_do_chute_constante():
    """Previsão de 0,5 sobre eventos equiprováveis: a linha de base é 0,25."""
    assert brier(np.full(100, 0.5), np.tile([0.0, 1.0], 50)) == pytest.approx(0.25)


def test_acuracia_topk_cresce_com_k():
    p = np.array([[0.1, 0.5, 0.4], [0.7, 0.2, 0.1]])
    alvo = np.array([2, 1])
    assert acuracia_topk(p, alvo, 1) == 0.0
    assert acuracia_topk(p, alvo, 2) == 1.0


def test_topk_saturado_em_k_maior_que_candidatos():
    p = np.array([[0.6, 0.4]])
    assert acuracia_topk(p, np.array([1]), k=10) == 1.0


def test_brier_multiclasse_perfeito():
    p = np.array([[1.0, 0.0], [0.0, 1.0]])
    assert brier_multiclasse(p, np.array([0, 1])) == 0.0


def test_log_loss_penaliza_confianca_errada():
    certo = log_loss(np.array([[0.9, 0.1]]), np.array([0]))
    errado = log_loss(np.array([[0.9, 0.1]]), np.array([1]))
    assert errado > certo


def test_log_loss_nao_estoura_com_probabilidade_zero():
    assert np.isfinite(log_loss(np.array([[1.0, 0.0]]), np.array([1])))


def test_estatisticas_com_vetor_vazio():
    r = estatisticas_erro(np.array([]))
    assert r["n"] == 0 and np.isnan(r["media_m"])


def test_estatisticas_ignoram_nao_finitos():
    r = estatisticas_erro(np.array([1.0, 2.0, np.nan, np.inf]))
    assert r["n"] == 2 and r["media_m"] == pytest.approx(1.5)


def test_erro_por_regiao_cobre_todo_o_campo():
    """Nenhum ponto pode cair fora das faixas, inclusive na linha de fundo."""
    pontos = np.array([[5.0, 30.0], [52.5, 30.0], [100.0, 30.0], [105.0, 30.0]])
    erros = np.array([0.1, 0.2, 0.3, 0.4])
    r = erro_por_regiao(pontos, erros)
    assert r["defensivo"]["n"] + r["central"]["n"] + r["ofensivo"]["n"] == 4


def test_erro_por_regiao_valida_comprimentos():
    with pytest.raises(ValueError):
        erro_por_regiao(np.zeros((3, 2)), np.zeros(2))
