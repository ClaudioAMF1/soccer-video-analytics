"""Testes do registro do campo."""
import numpy as np
import pytest

from pitch import (
    ModeloCampo, erro_reprojecao, estimar_homografia,
    estimar_homografia_ransac, projetar,
)
from pitch.perturbacao import calibrar_sigma, erro_induzido

# Homografia campo -> imagem representativa de enquadramento de transmissão.
H_CI = np.array([
    [12.0, 1.5, 300.0],
    [0.8, -9.0, 820.0],
    [0.0002, -0.0035, 1.0],
])


def _cenario():
    campo = ModeloCampo()
    _, pts_campo = campo.marcos_array()
    h = np.column_stack([pts_campo, np.ones(len(pts_campo))])
    p = h @ H_CI.T
    return p[:, :2] / p[:, 2:3], pts_campo


def test_recuperacao_exata():
    """Sem ruído, o DLT recupera a transformação até a precisão de máquina."""
    img, campo = _cenario()
    H = estimar_homografia(img, campo)
    assert erro_reprojecao(H, img, campo).max() < 1e-9


def test_ida_e_volta():
    img, campo = _cenario()
    H = estimar_homografia(img, campo)
    assert np.abs(projetar(np.linalg.inv(H), campo) - img).max() < 1e-6


def test_ruido_moderado_mantem_erro_submetrico():
    img, campo = _cenario()
    rng = np.random.default_rng(0)
    H = estimar_homografia(img + rng.normal(0, 2.0, img.shape), campo)
    assert erro_reprojecao(H, img, campo).mean() < 0.5


def test_ransac_rejeita_outliers():
    """Correspondências espúrias derrubam o DLT simples, mas não o RANSAC."""
    img, campo = _cenario()
    rng = np.random.default_rng(7)
    corrompido = img.copy()
    idx = rng.choice(len(img), 7, replace=False)
    corrompido[idx] += rng.normal(0, 150, (7, 2))

    erro_simples = erro_reprojecao(estimar_homografia(corrompido, campo), img, campo).mean()
    H, inliers = estimar_homografia_ransac(corrompido, campo, 0.5, 2000, rng)
    erro_ransac = erro_reprojecao(H, img, campo).mean()

    assert erro_ransac < 0.1
    assert erro_ransac < erro_simples / 10
    assert (~inliers[idx]).sum() >= 6  # detecta ao menos 6 dos 7 outliers


def test_exige_quatro_correspondencias():
    with pytest.raises(ValueError, match="ao menos 4"):
        estimar_homografia(np.zeros((3, 2)), np.zeros((3, 2)))


def test_formatos_incompativeis():
    with pytest.raises(ValueError):
        estimar_homografia(np.zeros((5, 2)), np.zeros((4, 2)))


def test_calibracao_de_sigma_atinge_o_alvo():
    """O sigma calibrado deve induzir o erro pedido, em metros."""
    img, campo = _cenario()
    rng = np.random.default_rng(3)
    for alvo in (0.5, 1.0, 2.0):
        sigma = calibrar_sigma(img, campo, alvo, repeticoes=40, rng=rng)
        obtido = erro_induzido(img, campo, sigma, 200, rng)
        assert abs(obtido - alvo) / alvo < 0.15


def test_erro_cresce_monotonicamente_com_sigma():
    img, campo = _cenario()
    rng = np.random.default_rng(11)
    erros = [erro_induzido(img, campo, s, 120, rng) for s in (2.0, 8.0, 20.0, 40.0)]
    assert all(a < b for a, b in zip(erros, erros[1:]))
