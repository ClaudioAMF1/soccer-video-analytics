"""Segmentação da transmissão em planos de câmera.

A transmissão de um jogo alterna entre várias câmeras: planos abertos da
câmera principal, closes, câmeras atrás do gol, replays. O SoccerNet-v2
distingue 13 tipos. Só os planos abertos da câmera principal mostram linhas do
campo suficientes para o registro; além disso, um corte de câmera invalida a
propagação da homografia, que supõe movimento contínuo.

Duas técnicas clássicas de processamento de imagem resolvem isso sem modelo
treinado:

- **Detecção de cortes** pela distância de Bhattacharyya entre histogramas de
  cor de quadros consecutivos. Dentro de um plano, mesmo com a câmera girando,
  a distribuição de cores muda pouco; num corte, muda de uma vez.
- **Reconhecimento de plano aberto** pela fração de pixels de gramado. Num
  plano aberto o gramado ocupa a maior parte da imagem; num close, quase nada.

Todas as funções recebem quadros RGB (uint8, altura x largura x 3). Quadros
lidos pelo OpenCV vêm em BGR e devem ser invertidos com `quadro[..., ::-1]`.

Uso:
    python -m pitch.planos --video jogo.mp4
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np

CAIXAS_POR_CANAL = 8
PASSO_AMOSTRA = 4          # usa 1 a cada 4 pixels em cada eixo
LIMIAR_CORTE = 0.35        # distância de Bhattacharyya
LIMIAR_GRAMADO = 0.45      # fração mínima de gramado num plano aberto


def histograma(quadro: np.ndarray) -> np.ndarray:
    """Histograma de cor normalizado, com 8 caixas por canal (512 no total)."""
    amostra = quadro[::PASSO_AMOSTRA, ::PASSO_AMOSTRA].reshape(-1, 3).astype(np.int32)
    q = amostra * CAIXAS_POR_CANAL // 256
    indices = (q[:, 0] * CAIXAS_POR_CANAL + q[:, 1]) * CAIXAS_POR_CANAL + q[:, 2]
    h = np.bincount(indices, minlength=CAIXAS_POR_CANAL ** 3).astype(float)
    return h / h.sum()


def distancia_bhattacharyya(h1: np.ndarray, h2: np.ndarray) -> float:
    """0 para distribuições idênticas, 1 para distribuições sem sobreposição."""
    coef = float(np.sqrt(h1 * h2).sum())
    return float(np.sqrt(max(0.0, 1.0 - coef)))


def fracao_gramado(quadro: np.ndarray) -> float:
    """Fração de pixels cujo verde predomina sobre vermelho e azul."""
    a = quadro[::PASSO_AMOSTRA, ::PASSO_AMOSTRA].astype(np.int32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mascara = (g >= 60) & (g * 100 >= r * 105) & (g * 100 >= b * 105)
    return float(mascara.mean())


def detectar_cortes(histogramas: list[np.ndarray], limiar: float = LIMIAR_CORTE) -> list[int]:
    """Índices dos quadros que iniciam um novo plano (o primeiro não conta)."""
    return [
        i for i in range(1, len(histogramas))
        if distancia_bhattacharyya(histogramas[i - 1], histogramas[i]) > limiar
    ]


@dataclass(frozen=True)
class Plano:
    inicio: int
    fim: int              # inclusivo
    aberto: bool
    gramado: float        # mediana da fração de gramado no plano

    @property
    def duracao(self) -> int:
        return self.fim - self.inicio + 1


def segmentar(fracoes: list[float], cortes: list[int],
              limiar_gramado: float = LIMIAR_GRAMADO) -> list[Plano]:
    """Divide o vídeo em planos e marca quais são abertos."""
    n = len(fracoes)
    limites = [0] + sorted(c for c in cortes if 0 < c < n) + [n]
    planos = []
    for ini, fim in zip(limites, limites[1:]):
        if fim <= ini:
            continue
        g = float(np.median(fracoes[ini:fim]))
        planos.append(Plano(ini, fim - 1, g >= limiar_gramado, round(g, 3)))
    return planos


def sugerir_quadros_chave(planos: list[Plano], fps: float, intervalo_s: float = 8.0,
                          margem: int = 2, duracao_min_s: float = 2.0) -> list[int]:
    """Quadros a anotar: início e fim de cada plano aberto e um a cada intervalo.

    Planos curtos demais são descartados: não compensa anotar um trecho de
    menos de dois segundos.
    """
    sugeridos = []
    passo = max(1, int(round(intervalo_s * fps)))
    for p in planos:
        if not p.aberto or p.duracao < duracao_min_s * fps:
            continue
        ini, fim = p.inicio + margem, p.fim - margem
        if fim <= ini:
            continue
        sugeridos.extend(range(ini, fim, passo))
        sugeridos.append(fim)
    return sorted(set(sugeridos))


def analisar_video(caminho: str, passo: int = 1):
    """Lê o vídeo e devolve (planos, fps). Exige OpenCV."""
    import cv2

    captura = cv2.VideoCapture(caminho)
    if not captura.isOpened():
        raise FileNotFoundError(f"não foi possível abrir {caminho}")
    fps = captura.get(cv2.CAP_PROP_FPS) or 25.0
    histos, fracoes, i = [], [], 0
    while True:
        ok, bgr = captura.read()
        if not ok:
            break
        if i % passo == 0:
            rgb = bgr[..., ::-1]
            histos.append(histograma(rgb))
            fracoes.append(fracao_gramado(rgb))
        i += 1
    captura.release()
    planos = segmentar(fracoes, detectar_cortes(histos))
    if passo > 1:
        planos = [Plano(p.inicio * passo, p.fim * passo, p.aberto, p.gramado) for p in planos]
    return planos, fps


def main() -> None:
    ap = argparse.ArgumentParser(description="Segmenta a transmissão em planos de câmera")
    ap.add_argument("--video", required=True)
    ap.add_argument("--intervalo", type=float, default=8.0,
                    help="Segundos entre quadros-chave sugeridos num plano aberto")
    args = ap.parse_args()

    planos, fps = analisar_video(args.video)
    print(f"{'início':>8} {'fim':>8} {'duração':>9}  tipo       gramado")
    for p in planos:
        print(f"{p.inicio:8d} {p.fim:8d} {p.duracao / fps:8.1f}s  "
              f"{'ABERTO ' if p.aberto else 'outro  '}    {p.gramado:.2f}")
    abertos = [p for p in planos if p.aberto]
    print(f"\n{len(planos)} planos, {len(abertos)} abertos. Processe cada plano aberto "
          f"separadamente com extrair.py --inicio/--fim.")
    sugeridos = sugerir_quadros_chave(planos, fps, args.intervalo)
    print(f"Quadros-chave sugeridos para anotar.py:\n  --quadros {','.join(map(str, sugeridos))}")


if __name__ == "__main__":
    main()
