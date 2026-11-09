"""E2 sobre transmissões reais: erro do registro por quadros-chave.

Para cada sequência do SN-GSR:

1. **Movimento de câmera.** Entre quadros consecutivos, rastreiam-se cantos do
   fundo (Shi-Tomasi) por fluxo óptico de Lucas-Kanade, com as caixas dos
   atletas e as faixas de grafismo da transmissão mascaradas, e ajusta-se uma
   homografia por RANSAC. É o mesmo procedimento do `MotionEstimator` da
   biblioteca Norfair, usado pelo pipeline. A composição dá, para cada quadro,
   a transformação até o primeiro quadro.
2. **Anotação simulada.** Nos quadros-chave, os marcos visíveis do campo são
   projetados com a homografia de referência e recebem ruído de 2 px, a
   imprecisão típica de um clique.
3. **Avaliação.** Em todos os quadros, a posição de cada atleta estimada pelo
   registro é comparada à anotada pelo SN-GSR.

Condições: intervalo entre chaves de 1, 2 e 5 s; com e sem reancoragem; e duas
linhas de base, uma única homografia para a sequência inteira e a chave mais
recente mantida sem propagação.

Uso:
    python -m experiments.e2_registro_real --dados data/SoccerNetGS/test --saida resultados/
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np

from experiments.e5_real import marcos_visiveis
from experiments.soccernet import carregar, homografia_referencia, listar
from pitch import RegistroPorChaves, estimar_homografia, projetar

ESCALA = 0.5          # o fluxo óptico roda em meia resolução
CLIQUE_PX = 2.0
INTERVALOS_S = (1, 2, 5)
FAIXA_GRAFISMO = (0.10, 0.08)   # fração da altura mascarada no topo e na base


def mascara(seq, q, largura, altura) -> np.ndarray:
    m = np.full((altura, largura), 255, np.uint8)
    topo, base = int(altura * FAIXA_GRAFISMO[0]), int(altura * FAIXA_GRAFISMO[1])
    m[:topo] = 0
    m[altura - base:] = 0
    for a in q.atletas:
        x, y, w, h = (v * ESCALA for v in a.caixa)
        cv2.rectangle(m, (int(x - 0.2 * w), int(y - 0.1 * h)), (int(x + 1.2 * w), int(y + 1.1 * h)), 0, -1)
    return m


def movimento_da_camera(seq) -> dict[int, np.ndarray]:
    """Quadro -> homografia (imagem do quadro -> imagem do 1º quadro), em pixels originais."""
    S = np.diag([ESCALA, ESCALA, 1.0])
    acum = {seq.quadros[0].indice: np.eye(3)}
    anterior, pts_ant = None, None
    largura, altura = int(seq.largura * ESCALA), int(seq.altura * ESCALA)
    for q in seq.quadros:
        img = cv2.imread(str(seq.imagem(q.indice)), cv2.IMREAD_GRAYSCALE)
        img = cv2.resize(img, (largura, altura), interpolation=cv2.INTER_AREA)
        if anterior is not None:
            M = np.eye(3)
            if pts_ant is not None and len(pts_ant) >= 8:
                pts, st, _ = cv2.calcOpticalFlowPyrLK(anterior, img, pts_ant, None,
                                                       winSize=(21, 21), maxLevel=3)
                ok = st.ravel() == 1
                if ok.sum() >= 8:
                    Hm, _ = cv2.findHomography(pts[ok], pts_ant[ok], cv2.RANSAC, 1.0)
                    if Hm is not None:
                        M = Hm  # imagem atual -> anterior (meia resolução)
            M = np.linalg.inv(S) @ M @ S
            acum[q.indice] = acum[ant_idx] @ M
        pts_ant = cv2.goodFeaturesToTrack(img, 400, 0.01, 8, mask=mascara(seq, q, largura, altura))
        anterior, ant_idx = img, q.indice
    return acum


def chave_anotada(seq, alvo: int, rng) -> tuple[int, np.ndarray] | None:
    """Quadro mais próximo do alvo com ao menos 6 marcos visíveis, anotado com ruído."""
    por_indice = {q.indice: q for q in seq.quadros}
    for d in range(0, 13):
        for f in (alvo - d, alvo + d):
            q = por_indice.get(f)
            if q is None:
                continue
            H = homografia_referencia(q)
            if H is None:
                continue
            uv_at = np.array([a.uv for a in q.atletas])
            m_uv, m_xy = marcos_visiveis(H, seq.largura, seq.altura, uv_at)
            if len(m_uv) >= 6:
                return f, estimar_homografia(m_uv + rng.normal(0, CLIQUE_PX, m_uv.shape), m_xy)
    return None


def erros_por_quadro(seq, homografia_de) -> list[float]:
    erros = []
    for q in seq.quadros:
        jog = [a for a in q.atletas if a.papel in ("player", "goalkeeper", "referee")]
        if not jog:
            continue
        H = homografia_de(q.indice)
        if H is None:
            continue
        uv = np.array([a.uv for a in jog])
        xy = np.array([a.xy for a in jog])
        p = projetar(H, uv)
        ok = np.isfinite(p).all(axis=1)
        if ok.any():
            erros.append(float(np.sqrt(((p[ok] - xy[ok]) ** 2).sum(axis=1)).mean()))
    return erros


def avaliar(seq, rng) -> dict:
    mov = movimento_da_camera(seq)
    n = len(seq.quadros)
    primeiro, ultimo = seq.quadros[0].indice, seq.quadros[-1].indice
    res = {}

    # Piso: o próprio gabarito, ajustado quadro a quadro.
    res["referencia_por_quadro"] = erros_por_quadro(seq, lambda f: homografia_referencia(
        next(q for q in seq.quadros if q.indice == f)))

    for s in INTERVALOS_S:
        passo = int(s * seq.fps)
        chaves = {}
        for alvo in list(range(primeiro, ultimo + 1, passo)) + [ultimo]:
            c = chave_anotada(seq, alvo, rng)
            if c:
                chaves[c[0]] = c[1]
        if not chaves:
            continue
        reg = RegistroPorChaves(chaves, lambda f: mov[f], seq.largura, seq.altura)
        res[f"chaves_{s}s_reancorado"] = erros_por_quadro(seq, lambda f: reg.homografia(f, True))
        res[f"chaves_{s}s_so_anterior"] = erros_por_quadro(seq, lambda f: reg.homografia(f, False))
        ordem = sorted(chaves)
        res[f"chaves_{s}s_sem_propagacao"] = erros_por_quadro(
            seq, lambda f: chaves[max([k for k in ordem if k <= f], default=ordem[0])])

    c0 = chave_anotada(seq, primeiro, rng)
    if c0:
        res["homografia_unica"] = erros_por_quadro(seq, lambda f: c0[1])
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description="E2 sobre o SN-GSR")
    ap.add_argument("--dados", type=Path, required=True)
    ap.add_argument("--saida", type=Path, default=Path("resultados"))
    ap.add_argument("--limite", type=int, default=None, help="Processa só as N primeiras sequências")
    ap.add_argument("--semente", type=int, default=20261109)
    args = ap.parse_args()

    rng = np.random.default_rng(args.semente)
    acumulado: dict[str, list[float]] = {}
    por_seq = []
    pastas = [p for p in listar(args.dados) if (p / "img1").exists()][: args.limite]
    for p in pastas:
        seq = carregar(p)
        res = avaliar(seq, rng)
        for k, v in res.items():
            acumulado.setdefault(k, []).extend(v)
        por_seq.append({"sequencia": seq.nome, **{k: round(float(np.median(v)), 3) for k, v in res.items() if v}})
        print(seq.nome, {k: round(float(np.median(v)), 2) for k, v in res.items() if v}, flush=True)

    linhas = []
    for k, v in acumulado.items():
        v = np.array(v)
        linhas.append({"condicao": k, "quadros": len(v), "media_m": round(float(v.mean()), 3),
                       "mediana_m": round(float(np.median(v)), 3),
                       "p90_m": round(float(np.percentile(v, 90)), 3),
                       "pct_abaixo_1m": round(float((v < 1.0).mean() * 100), 1),
                       "pct_abaixo_0_5m": round(float((v < 0.5).mean() * 100), 1)})
    args.saida.mkdir(parents=True, exist_ok=True)
    with (args.saida / "e2_registro_real.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)
    with (args.saida / "e2_registro_real_por_sequencia.csv").open("w", newline="", encoding="utf-8") as f:
        campos = sorted({k for l in por_seq for k in l}, key=lambda k: (k != "sequencia", k))
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(por_seq)
    print(f"\n{len(pastas)} sequências")
    for l in linhas:
        print(l)


if __name__ == "__main__":
    main()
