"""Camada narrativa: decide *o que* mostrar ao espectador, e *quando*."""
from .estados import EstadoNarrativo, MaquinaNarrativa, ParametrosNarrativa, legenda
from .confiabilidade import carregar_curvas_e5, decidir_exibicao

__all__ = [
    "EstadoNarrativo", "MaquinaNarrativa", "ParametrosNarrativa", "legenda",
    "carregar_curvas_e5", "decidir_exibicao",
]
