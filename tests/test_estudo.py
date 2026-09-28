"""Testes da análise do estudo com usuários."""
import numpy as np
import pytest

from estudo.analise import (
    agregar, analisar, comparar, holm, rank_biserial_pareado, simular,
)


def test_rank_biserial_extremos():
    assert rank_biserial_pareado(np.array([1.0, 2.0, 3.0])) == 1.0
    assert rank_biserial_pareado(np.array([-1.0, -2.0])) == -1.0
    assert rank_biserial_pareado(np.array([1.0, -1.0])) == 0.0
    assert rank_biserial_pareado(np.array([0.0, 0.0])) == 0.0


def test_holm_exemplo_conhecido():
    # p ordenados 0,01 / 0,02 / 0,04 -> 0,03 / 0,04 / 0,04
    assert holm([0.04, 0.01, 0.02]) == pytest.approx([0.04, 0.03, 0.04])


def test_holm_nunca_ultrapassa_um():
    assert max(holm([0.6, 0.7, 0.9])) == 1.0


def test_agregar_calcula_acuracia_e_rtlx():
    respostas = [
        {"participante": "P1", "condicao": "estatica", "acerto": "1", "tempo_s": "10"},
        {"participante": "P1", "condicao": "estatica", "acerto": "0", "tempo_s": "14"},
    ]
    carga = [{"participante": "P1", "condicao": "estatica", "mental": 60, "fisica": 0,
              "temporal": 30, "desempenho": 30, "esforco": 60, "frustracao": 0}]
    a = agregar(respostas, carga)["P1"]["estatica"]
    assert a["acuracia"] == 0.5 and a["tempo_mediano"] == 12.0 and a["rtlx"] == 30.0


def test_efeito_forte_e_detectado():
    agregado = {f"P{i}": {"estatica": {"acuracia": 0.4 + 0.01 * i},
                          "dinamica": {"acuracia": 0.7 + 0.01 * i}} for i in range(12)}
    r = comparar(agregado, "acuracia", maior_e_melhor=True)
    assert r["p"] < 0.01 and r["r_rb"] == 1.0


def test_tempo_menor_conta_como_vantagem():
    agregado = {f"P{i}": {"estatica": {"tempo_mediano": 15.0 + i},
                          "dinamica": {"tempo_mediano": 10.0 + i}} for i in range(10)}
    assert comparar(agregado, "tempo_mediano", maior_e_melhor=False)["r_rb"] == 1.0


def test_participante_incompleto_e_excluido():
    agregado = {"P1": {"estatica": {"acuracia": 0.5}, "dinamica": {"acuracia": 0.9}},
                "P2": {"estatica": {"acuracia": 0.4}, "dinamica": {"acuracia": 0.8}},
                "P3": {"estatica": {"acuracia": 0.6}}}
    assert comparar(agregado, "acuracia", True)["n"] == 2


def test_analise_completa_com_dados_simulados():
    resultados = analisar(*simular(24))
    assert [r["medida"] for r in resultados] == ["acuracia", "tempo_mediano", "rtlx"]
    assert all(r["n"] == 24 for r in resultados)
    assert all(r["p_holm"] >= r["p"] for r in resultados)
    assert all(r["r_rb"] > 0 for r in resultados)  # a simulação favorece a dinâmica
