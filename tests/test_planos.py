"""Testes da segmentação da transmissão em planos de câmera."""
import numpy as np

from pitch.planos import (
    Plano, detectar_cortes, distancia_bhattacharyya, fracao_gramado,
    histograma, segmentar, sugerir_quadros_chave,
)

RNG = np.random.default_rng(0)


def plano_aberto(deslocamento=0):
    """Gramado com faixas de corte e linhas brancas; o deslocamento simula a panorâmica."""
    q = np.zeros((360, 640, 3), dtype=np.uint8)
    faixas = ((np.arange(640) + deslocamento) // 40) % 2
    q[..., 1] = np.where(faixas, 120, 105)[None, :]
    q[..., 0], q[..., 2] = 40, 35
    q[100:104, :] = 230
    q[:, (300 + deslocamento) % 640:(304 + deslocamento) % 640 or 640] = 230
    q[:40] = (70, 70, 80)  # arquibancada no topo
    return np.clip(q.astype(int) + RNG.integers(-6, 7, q.shape), 0, 255).astype(np.uint8)


def close_de_jogador():
    q = np.zeros((360, 640, 3), dtype=np.uint8)
    q[...] = (40, 30, 30)
    q[60:300, 200:440] = (205, 160, 130)  # pele
    q[200:360, 150:490] = (220, 30, 40)   # camisa vermelha
    return q


def test_panoramica_nao_e_corte():
    a, b = histograma(plano_aberto(0)), histograma(plano_aberto(25))
    assert distancia_bhattacharyya(a, b) < 0.15


def test_troca_de_camera_e_corte():
    a, b = histograma(plano_aberto()), histograma(close_de_jogador())
    assert distancia_bhattacharyya(a, b) > 0.6


def test_fracao_de_gramado_distingue_planos():
    assert fracao_gramado(plano_aberto()) > 0.7
    assert fracao_gramado(close_de_jogador()) < 0.05


def test_segmentacao_de_sequencia_com_corte_e_retorno():
    quadros = ([plano_aberto(i) for i in range(30)] + [close_de_jogador()] * 20
               + [plano_aberto(i) for i in range(30)])
    h = [histograma(q) for q in quadros]
    cortes = detectar_cortes(h)
    assert cortes == [30, 50]
    planos = segmentar([fracao_gramado(q) for q in quadros], cortes)
    assert [(p.inicio, p.fim, p.aberto) for p in planos] == [(0, 29, True), (30, 49, False), (50, 79, True)]


def test_sugestoes_so_em_planos_abertos_e_longos():
    planos = [Plano(0, 249, True, 0.8), Plano(250, 299, False, 0.1),
              Plano(300, 320, True, 0.8), Plano(321, 700, True, 0.8)]
    s = sugerir_quadros_chave(planos, fps=25.0, intervalo_s=8.0)
    assert all(not 250 <= q <= 320 for q in s)  # close e plano curto ignorados
    assert 2 in s and 247 in s and 323 in s and 698 in s
    assert all(b - a <= 200 for a, b in zip(s, s[1:]) if a >= 321)
