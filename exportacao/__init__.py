"""Etapa 1 da arquitetura: extrair do vídeo gravado dados estruturados, sem desenhar."""
from .esquema import VERSAO, carregar, montar_documento, salvar, validar
from .pipeline import QuadroBruto, anotacoes_para_chaves, montar_exportacao

__all__ = [
    "VERSAO", "carregar", "montar_documento", "salvar", "validar",
    "QuadroBruto", "anotacoes_para_chaves", "montar_exportacao",
]
