"""Modelo métrico do campo de futebol.

Dimensões conforme as Regras de Jogo da IFAB para partidas internacionais.
O sistema de coordenadas tem origem no canto inferior esquerdo, com o eixo x
ao longo do comprimento (0 a 105 m) e o eixo y ao longo da largura (0 a 68 m).
Todas as unidades são metros.
"""
from __future__ import annotations

import numpy as np

COMPRIMENTO = 105.0
LARGURA = 68.0

# Medidas regulamentares fixas, independentes do tamanho do campo.
PROF_GRANDE_AREA = 16.5
LARG_GRANDE_AREA = 40.32
PROF_PEQUENA_AREA = 5.5
LARG_PEQUENA_AREA = 18.32
RAIO_CIRCULO_CENTRAL = 9.15
DIST_MARCA_PENALTI = 11.0
LARG_GOL = 7.32


def _meia_corda_arco() -> float:
    """Meia-corda do arco da grande área sobre a linha frontal da área.

    O arco tem raio de 9,15 m centrado na marca de pênalti (a 11 m da linha de
    fundo) e corta a linha frontal da área (a 16,5 m) a sqrt(9,15² - 5,5²) m
    do eixo do campo.
    """
    return float(np.sqrt(RAIO_CIRCULO_CENTRAL ** 2 - (PROF_GRANDE_AREA - DIST_MARCA_PENALTI) ** 2))


class ModeloCampo:
    """Pontos de referência do campo em coordenadas métricas.

    Os marcos (`landmarks`) são interseções de linhas inequivocamente
    identificáveis em imagem, usadas como correspondências para estimar a
    transformação entre o plano da imagem e o plano do gramado.
    """

    def __init__(self, comprimento: float = COMPRIMENTO, largura: float = LARGURA):
        self.comprimento = float(comprimento)
        self.largura = float(largura)

    # ------------------------------------------------------------------ #
    @property
    def centro(self) -> np.ndarray:
        return np.array([self.comprimento / 2.0, self.largura / 2.0])

    @property
    def area(self) -> float:
        return self.comprimento * self.largura

    def marcos(self) -> dict[str, np.ndarray]:
        """Marcos nomeados do campo, em metros."""
        c, l = self.comprimento, self.largura
        meio_y = l / 2.0
        ga_inf = (l - LARG_GRANDE_AREA) / 2.0
        ga_sup = (l + LARG_GRANDE_AREA) / 2.0
        pa_inf = (l - LARG_PEQUENA_AREA) / 2.0
        pa_sup = (l + LARG_PEQUENA_AREA) / 2.0

        return {
            # Cantos
            "canto_inf_esq": np.array([0.0, 0.0]),
            "canto_inf_dir": np.array([c, 0.0]),
            "canto_sup_dir": np.array([c, l]),
            "canto_sup_esq": np.array([0.0, l]),
            # Linha de meio-campo
            "meio_inf": np.array([c / 2.0, 0.0]),
            "meio_sup": np.array([c / 2.0, l]),
            "centro": np.array([c / 2.0, meio_y]),
            # Grande área esquerda
            "ga_esq_inf_linha": np.array([0.0, ga_inf]),
            "ga_esq_sup_linha": np.array([0.0, ga_sup]),
            "ga_esq_inf_frente": np.array([PROF_GRANDE_AREA, ga_inf]),
            "ga_esq_sup_frente": np.array([PROF_GRANDE_AREA, ga_sup]),
            # Grande área direita
            "ga_dir_inf_linha": np.array([c, ga_inf]),
            "ga_dir_sup_linha": np.array([c, ga_sup]),
            "ga_dir_inf_frente": np.array([c - PROF_GRANDE_AREA, ga_inf]),
            "ga_dir_sup_frente": np.array([c - PROF_GRANDE_AREA, ga_sup]),
            # Pequena área esquerda
            "pa_esq_inf_frente": np.array([PROF_PEQUENA_AREA, pa_inf]),
            "pa_esq_sup_frente": np.array([PROF_PEQUENA_AREA, pa_sup]),
            # Pequena área direita
            "pa_dir_inf_frente": np.array([c - PROF_PEQUENA_AREA, pa_inf]),
            "pa_dir_sup_frente": np.array([c - PROF_PEQUENA_AREA, pa_sup]),
            # Marcas de pênalti
            "penalti_esq": np.array([DIST_MARCA_PENALTI, meio_y]),
            "penalti_dir": np.array([c - DIST_MARCA_PENALTI, meio_y]),
            # Círculo central: interseções com a linha de meio-campo e extremos.
            # São os únicos pontos anotáveis quando a câmera enquadra o meio do
            # campo, onde nenhum canto de área aparece.
            "circulo_inf": np.array([c / 2.0, meio_y - RAIO_CIRCULO_CENTRAL]),
            "circulo_sup": np.array([c / 2.0, meio_y + RAIO_CIRCULO_CENTRAL]),
            "circulo_esq": np.array([c / 2.0 - RAIO_CIRCULO_CENTRAL, meio_y]),
            "circulo_dir": np.array([c / 2.0 + RAIO_CIRCULO_CENTRAL, meio_y]),
            # Arco da grande área: interseções com a linha frontal da área.
            "arco_esq_inf": np.array([PROF_GRANDE_AREA, meio_y - _meia_corda_arco()]),
            "arco_esq_sup": np.array([PROF_GRANDE_AREA, meio_y + _meia_corda_arco()]),
            "arco_dir_inf": np.array([c - PROF_GRANDE_AREA, meio_y - _meia_corda_arco()]),
            "arco_dir_sup": np.array([c - PROF_GRANDE_AREA, meio_y + _meia_corda_arco()]),
        }

    def marcos_array(self, nomes: list[str] | None = None) -> tuple[list[str], np.ndarray]:
        """Retorna (nomes, array Nx2) dos marcos pedidos, ou de todos."""
        todos = self.marcos()
        chaves = list(todos.keys()) if nomes is None else list(nomes)
        faltando = [k for k in chaves if k not in todos]
        if faltando:
            raise KeyError(f"marcos desconhecidos: {faltando}")
        return chaves, np.array([todos[k] for k in chaves], dtype=float)

    def dentro(self, pontos: np.ndarray, margem: float = 0.0) -> np.ndarray:
        """Máscara booleana dos pontos dentro das quatro linhas do campo."""
        p = np.atleast_2d(np.asarray(pontos, dtype=float))
        return (
            (p[:, 0] >= -margem) & (p[:, 0] <= self.comprimento + margem)
            & (p[:, 1] >= -margem) & (p[:, 1] <= self.largura + margem)
        )

    def grade(self, passo: float = 1.0) -> np.ndarray:
        """Grade regular de células do campo, em metros.

        Retorna um array (N, 2) com os centros das células, usado como domínio
        de avaliação dos modelos de controle de espaço.
        """
        xs = np.arange(passo / 2.0, self.comprimento, passo)
        ys = np.arange(passo / 2.0, self.largura, passo)
        gx, gy = np.meshgrid(xs, ys, indexing="ij")
        return np.column_stack([gx.ravel(), gy.ravel()])

    def formato_grade(self, passo: float = 1.0) -> tuple[int, int]:
        """Dimensões (nx, ny) da grade produzida por `grade(passo)`."""
        nx = len(np.arange(passo / 2.0, self.comprimento, passo))
        ny = len(np.arange(passo / 2.0, self.largura, passo))
        return nx, ny
