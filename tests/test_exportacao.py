"""Testes da exportação (segunda passada) e do formato do arquivo."""
import copy

import numpy as np
import pytest

pytest.importorskip("PIL", reason="a posse reutiliza soccer.partida, que exige Pillow")

from exportacao import anotacoes_para_chaves, carregar, salvar, validar  # noqa: E402
from exportacao import demo  # noqa: E402
from exportacao.pipeline import _velocidades  # noqa: E402


@pytest.fixture(scope="module")
def doc_demo():
    return demo.gerar()


def test_documento_da_demo_e_valido(doc_demo):
    assert validar(doc_demo) == []


def test_posicoes_exportadas_batem_com_a_verdade(doc_demo):
    """Projeção por quadros-chave + propagação recupera as posições simuladas."""
    posicoes, bolas, _ = demo.simular()
    erros = []
    for q, verdade in zip(doc_demo["quadros"], posicoes):
        for a in q["j"]:
            erros.append(np.hypot(a["x"] - verdade[a["id"], 0], a["y"] - verdade[a["id"], 1]))
    assert max(erros) < 0.05  # arredondamento a 2 casas + resíduo numérico


def test_jogada_percorre_todos_os_estados(doc_demo):
    estados = {q["estado"] for q in doc_demo["quadros"]}
    assert {"construcao", "ataque", "transicao", "finalizacao"} <= estados


def test_controle_cresce_com_o_avanco(doc_demo):
    q = doc_demo["quadros"]
    inicio = np.mean([x["cf"] for x in q[:50]])
    fim = np.mean([x["cf"] for x in q[-20:]])
    assert fim > inicio + 0.1


def test_regra_de_exibicao_bloqueia_dominio_individual(doc_demo):
    assert doc_demo["exibicao"]["zonas_de_controle"]["exibir"]
    assert not doc_demo["exibicao"]["dominio_individual"]["exibir"]


def test_ida_e_volta_em_disco(doc_demo, tmp_path):
    caminho = salvar(doc_demo, tmp_path / "x.json")
    assert carregar(caminho)["quadros"][10] == doc_demo["quadros"][10]


def test_validar_aponta_problemas(doc_demo):
    ruim = copy.deepcopy(doc_demo)
    ruim["quadros"][0]["c"] = ruim["quadros"][0]["c"][:-1]
    ruim["quadros"][1]["posse"] = 7
    ruim["equipes"][0]["direcao"] = 0
    problemas = " | ".join(validar(ruim))
    assert "células" in problemas and "posse" in problemas and "direcao" in problemas


def test_salvar_recusa_documento_invalido(doc_demo, tmp_path):
    ruim = copy.deepcopy(doc_demo)
    del ruim["quadros"][0]["estado"]
    with pytest.raises(ValueError):
        salvar(ruim, tmp_path / "ruim.json")


def test_anotacoes_exigem_quatro_marcos_conhecidos():
    with pytest.raises(ValueError, match="ao menos 4"):
        anotacoes_para_chaves({"0": {"centro": [1, 2], "meio_sup": [3, 4], "circulo_sup": [5, 6]}})
    with pytest.raises(KeyError, match="desconhecidos"):
        anotacoes_para_chaves({"0": {"trave": [1, 2]}})


def test_velocidade_constante_e_recuperada():
    fps = 25.0
    traj = {7: [(f, 10.0 + 4.0 * f / fps, 30.0 - 2.0 * f / fps) for f in range(40)]}
    v = _velocidades(traj, fps)
    assert v[(7, 20)] == pytest.approx((4.0, -2.0), abs=1e-6)


def test_lacuna_no_rastreamento_nao_e_derivada_atraves():
    fps = 25.0
    pontos = [(f, float(f), 0.0) for f in range(10)] + [(f, 500.0 + f, 0.0) for f in range(20, 30)]
    v = _velocidades({1: pontos}, fps)
    assert abs(v[(1, 9)][0] - 25.0) < 1e-6  # 1 m/quadro = 25 m/s, sem o salto de 490 m
