"""Testes do registro por quadros-chave em vídeo gravado."""
import numpy as np
import pytest

from pitch.homografia import projetar
from pitch.propagacao import (
    RegistroPorChaves, deriva_m, grade_imagem, homografia_por_amostragem,
)

LARG, ALT = 1280.0, 720.0

# Referência absoluta (imagem do 1º quadro) -> campo.
G_ABS = np.linalg.inv(np.array([
    [9.0, 1.2, 180.0],
    [0.6, -7.0, 640.0],
    [0.0002, -0.003, 1.0],
]))


def camera(t: int) -> np.ndarray:
    """Movimento verdadeiro: imagem do quadro t -> referência absoluta.

    Panorâmica horizontal com leve zoom, como numa transmissão acompanhando
    a jogada.
    """
    zoom = 1.0 + 0.001 * t
    return np.array([
        [1.0 / zoom, 0.0, 4.0 * t],
        [0.0, 1.0 / zoom, 0.5 * t],
        [0.0, 0.0, 1.0],
    ])


def verdade(t: int) -> np.ndarray:
    return G_ABS @ camera(t)


def test_amostragem_recupera_homografia_exata():
    H = verdade(30)
    Hf = homografia_por_amostragem(lambda p: projetar(H, p), LARG, ALT)
    assert deriva_m(Hf, H, grade_imagem(LARG, ALT)).max() < 1e-6


def test_propagacao_exata_com_movimento_exato():
    """Sem erro no movimento, qualquer chave reproduz a verdade em todo quadro."""
    reg = RegistroPorChaves({0: verdade(0), 120: verdade(120)}, camera, LARG, ALT)
    pts = grade_imagem(LARG, ALT)
    for t in (0, 17, 60, 119, 120, 150):
        assert deriva_m(reg.homografia(t), verdade(t), pts).max() < 1e-4


def test_quadro_chave_e_reproduzido_exatamente():
    reg = RegistroPorChaves({0: verdade(0), 50: verdade(50)}, camera, LARG, ALT)
    assert deriva_m(reg.homografia(50), verdade(50), grade_imagem(LARG, ALT)).max() < 1e-6


def test_reancoragem_reduz_a_deriva():
    """Com deriva acumulada no movimento, combinar as duas chaves compensa o erro."""
    deslocamento_por_quadro = 0.8  # px de deriva acumulada por quadro

    def movimento_com_deriva(t):
        D = np.array([[1.0, 0.0, deslocamento_por_quadro * t],
                      [0.0, 1.0, 0.0],
                      [0.0, 0.0, 1.0]])
        return D @ camera(t)

    reg = RegistroPorChaves({0: verdade(0), 100: verdade(100)}, movimento_com_deriva, LARG, ALT)
    pts = grade_imagem(LARG, ALT)
    so_anterior = deriva_m(reg.homografia(50, reancorar=False), verdade(50), pts).mean()
    reancorado = deriva_m(reg.homografia(50, reancorar=True), verdade(50), pts).mean()

    assert so_anterior > 0.5
    assert reancorado < so_anterior / 5


def test_fora_do_intervalo_usa_chave_mais_proxima():
    reg = RegistroPorChaves({10: verdade(10), 20: verdade(20)}, camera, LARG, ALT)
    assert reg.vizinhas(3) == (10, 10)
    assert reg.vizinhas(40) == (20, 20)
    assert reg.vizinhas(15) == (10, 20)


def test_exige_ao_menos_uma_chave():
    with pytest.raises(ValueError, match="quadro-chave"):
        RegistroPorChaves({}, camera, LARG, ALT)
