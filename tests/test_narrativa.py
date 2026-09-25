"""Testes da camada narrativa."""
import csv

import numpy as np
import pytest

from narrativa import (
    EstadoNarrativo as E, MaquinaNarrativa, ParametrosNarrativa,
    carregar_curvas_e5, decidir_exibicao, legenda,
)

FPS = 25.0


def _rodar(maquina, quadros):
    """quadros: lista de (posse, bola, adversarios). Retorna a sequência de estados."""
    return [maquina.atualizar(i / FPS, p, b, a) for i, (p, b, a) in enumerate(quadros)]


def _distintos(seq):
    saida = []
    for s in seq:
        if not saida or saida[-1] != s:
            saida.append(s)
    return saida


def test_jogada_progride_ate_a_finalizacao():
    m = MaquinaNarrativa({0: 1, 1: -1})
    longe = np.array([[10.0, 5.0]])
    quadros = [(0, np.array([x, 34.0]), longe) for x in np.linspace(20, 95, 150)]
    ordem = _distintos(_rodar(m, quadros))
    assert ordem == [E.BOLA_MORTA, E.CONSTRUCAO, E.ATAQUE, E.FINALIZACAO]


def test_defensor_no_limite_nao_faz_o_estado_piscar():
    """Defensor oscilando entre 4,8 e 5,2 m: um corte único alternaria sem parar."""
    m = MaquinaNarrativa({0: 1, 1: -1})
    bola = np.array([90.0, 34.0])
    quadros = [(0, bola, np.array([[90.0, 34.0 + (5.2 if i % 2 else 4.8)]])) for i in range(200)]
    trocas = len(_distintos(_rodar(m, quadros))) - 1

    ingenuo = [5.2 if i % 2 else 4.8 for i in range(200)]
    trocas_ingenuas = sum(1 for a, b in zip(ingenuo, ingenuo[1:]) if (a >= 5) != (b >= 5))

    assert trocas <= 2
    assert trocas_ingenuas > 100


def test_troca_de_posse_gera_transicao_temporaria():
    m = MaquinaNarrativa({0: 1, 1: -1}, ParametrosNarrativa(duracao_transicao=2.0))
    bola = np.array([40.0, 34.0])
    longe = np.array([[100.0, 5.0]])
    antes = [(0, bola, longe)] * 50
    depois = [(1, bola, longe)] * 150
    seq = _rodar(m, antes + depois)
    assert E.TRANSICAO in seq[50:110]
    # Após os 2 s, volta a refletir a posição: equipe 1 ataca para x=0, bola em x=40 é ataque.
    assert seq[-1] == E.ATAQUE


def test_bola_ausente_leva_a_bola_morta():
    m = MaquinaNarrativa({0: 1, 1: -1})
    bola = np.array([40.0, 34.0])
    seq = _rodar(m, [(0, bola, None)] * 30 + [(0, None, None)] * 30)
    assert seq[-1] == E.BOLA_MORTA


def test_direcao_de_ataque_invertida():
    m = MaquinaNarrativa({0: 1, 1: -1})
    assert m.progresso(1, 10.0) == pytest.approx(1 - 10 / 105)
    assert np.allclose(m.gol_adversario(1), [0.0, 34.0])
    seq = _rodar(m, [(1, np.array([12.0, 34.0]), np.array([[60.0, 10.0]]))] * 20)
    assert seq[-1] == E.FINALIZACAO


def test_confirmacao_temporal_ignora_quadro_isolado():
    m = MaquinaNarrativa({0: 1, 1: -1})
    longe = np.array([[100.0, 5.0]])
    quadros = [(0, np.array([30.0, 34.0]), longe)] * 20
    quadros.append((None, np.array([30.0, 34.0]), longe))  # um único quadro sem posse
    quadros += [(0, np.array([30.0, 34.0]), longe)] * 20
    assert E.DISPUTA not in _rodar(m, quadros)


def test_parametros_incoerentes():
    with pytest.raises(ValueError):
        ParametrosNarrativa(raio_finalizacao_entrada=25, raio_finalizacao_saida=20)
    with pytest.raises(ValueError):
        ParametrosNarrativa(folga_entrada=3, folga_saida=5)
    with pytest.raises(ValueError):
        MaquinaNarrativa({0: 2})


def test_legenda_em_linguagem_comum():
    t = legenda(E.ATAQUE, "Palmeiras", 0.584)
    assert "Palmeiras ataca" in t and "58% do campo" in t
    assert "%" not in legenda(E.DISPUTA, "Palmeiras", 0.5)


# ------------------------- confiabilidade ------------------------- #
# Valores obtidos no E5 (200 repetições), usados como fixture.
E5 = [
    (0.0, 0.00, 0.00, 0.00, 0.00, 0.00),
    (0.52, 1.07, 0.57, 1.24, 0.40, 2.58),
    (1.07, 2.31, 1.03, 2.46, 0.82, 4.54),
    (1.92, 4.22, 1.87, 4.67, 1.63, 8.00),
    (2.89, 6.23, 3.05, 6.90, 2.36, 11.92),
]


def _csv(tmp_path):
    caminho = tmp_path / "e5.csv"
    campos = ["erro_registro_medio_m", "largura_a_m__erro_rel_pct",
              "profundidade_a_m__erro_rel_pct", "area_ocupacao_a_m2__erro_rel_pct",
              "controle_a__erro_rel_pct", "concordancia_dominante__erro_rel_pct",
              "area_maior_dominio_m2__erro_rel_pct", "dist_centroides_m__erro_rel_pct"]
    with caminho.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(campos)
        for e, larg, prof, area, contr, dom in E5:
            w.writerow([e, larg, prof, area, contr, dom, dom * 0.4, contr])
    return caminho


def test_erro_baixo_libera_tudo(tmp_path):
    d = decidir_exibicao(carregar_curvas_e5(_csv(tmp_path)), 0.5)
    assert all(v["exibir"] for v in d.values())


def test_erro_realista_bloqueia_so_o_nivel_de_jogador(tmp_path):
    d = decidir_exibicao(carregar_curvas_e5(_csv(tmp_path)), 1.5)
    assert d["zonas_de_controle"]["exibir"]
    assert d["forma_da_equipe"]["exibir"]
    assert not d["dominio_individual"]["exibir"]
    assert d["dominio_individual"]["nivel"] == "jogador"


def test_fora_da_faixa_medida_nao_exibe(tmp_path):
    d = decidir_exibicao(carregar_curvas_e5(_csv(tmp_path)), 10.0)
    assert not any(v["exibir"] for v in d.values())


def test_metrica_sem_medicao_nao_exibe():
    x = np.array([0.0, 3.0])
    d = decidir_exibicao({"controle_a": (x, np.array([0.0, 2.0]))}, 1.0)
    assert d["zonas_de_controle"]["exibir"]
    assert not d["forma_da_equipe"]["exibir"]


def test_equipe_narrada_muda_junto_com_o_estado():
    """A legenda não pode atribuir à equipe nova o estado ainda confirmado da antiga."""
    m = MaquinaNarrativa({0: 1, 1: -1}, ParametrosNarrativa(quadros_confirmacao=5))
    bola = np.array([70.0, 34.0])
    longe = np.array([[20.0, 5.0]])
    _rodar(m, [(0, bola, longe)] * 20)
    assert (m.estado, m.equipe) == (E.ATAQUE, 0)
    for i in range(4):  # menos quadros que a confirmação exige
        m.atualizar((20 + i) / FPS, 1, bola, longe)
        assert (m.estado, m.equipe) == (E.ATAQUE, 0)


def test_transicoes_de_equipes_diferentes_nao_se_fundem():
    m = MaquinaNarrativa({0: 1, 1: -1}, ParametrosNarrativa(duracao_transicao=5.0))
    bola = np.array([50.0, 34.0])
    longe = np.array([[100.0, 5.0]])
    seq = [(0, bola, longe)] * 30 + [(1, bola, longe)] * 30 + [(0, bola, longe)] * 30
    equipes = []
    for i, (p, b, a) in enumerate(seq):
        m.atualizar(i / FPS, p, b, a)
        if m.estado is E.TRANSICAO:
            equipes.append(m.equipe)
    assert 1 in equipes and 0 in equipes
