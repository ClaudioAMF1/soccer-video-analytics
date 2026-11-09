"""Posse de bola e estados narrativos sobre trajetórias reais do SN-GSR.

Duas perguntas:

1. **Estabilidade.** Com o ruído de medição de um pipeline real, quantas vezes
   por minuto a legenda exibida ao espectador muda? Compara-se a máquina de
   estados com histerese e confirmação temporal a uma versão ingênua, de corte
   único, sobre as mesmas trajetórias.
2. **Validade.** O estado "finalização" aparece nas sequências cujo evento
   anotado pelo SoccerNet é um chute, e não nas demais? O rótulo do evento é
   independente do sistema, o que torna a comparação uma verificação externa.

O ruído de registro é modelado como um deslocamento afim do campo que varia
suavemente no tempo (sorteado a cada 2 s e interpolado), mais uma oscilação
independente de cada atleta, que representa a oscilação da caixa detectada.

Uso:
    python -m experiments.narrativa_real --dados data/SoccerNetGS/test --saida resultados/
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import numpy as np

from experiments.soccernet import DIRECAO_ATAQUE, carregar, listar
from narrativa import EstadoNarrativo, MaquinaNarrativa, ParametrosNarrativa
from soccer.partida import Partida
from soccer.time import Time

ACOES_CHUTE = {"Shots on target", "Shots off target", "Goal", "Penalty"}
INTERVALO_RUIDO_S = 2.0
OSCILACAO_M = 0.2


class _Atleta:
    def __init__(self, time, distancia):
        self.time, self.detection, self._d = time, True, distancia

    def distancia_para_bola(self, bola, homografia=None):
        return self._d


class _Bola:
    def __init__(self, presente):
        self.detection = True if presente else None
        self.centro = (0.0, 0.0) if presente else None


def campo_de_ruido(n_quadros: int, fps: float, erro_m: float, rng) -> list:
    """Deslocamento afim suave por quadro: função xy -> xy + delta(xy)."""
    if erro_m <= 0:
        return [lambda p: p] * n_quadros
    passo = max(1, int(INTERVALO_RUIDO_S * fps))
    nos = np.arange(0, n_quadros + passo, passo)
    # Translação domina; a parte linear (rotação, escala) cresce longe do centro.
    t = rng.normal(0, erro_m * 0.8, (len(nos), 2))
    A = rng.normal(0, erro_m * 0.012, (len(nos), 2, 2))
    centro = np.array([52.5, 34.0])
    saida = []
    for f in range(n_quadros):
        k = min(f // passo, len(nos) - 2)
        a = (f - nos[k]) / passo
        tf = (1 - a) * t[k] + a * t[k + 1]
        Af = (1 - a) * A[k] + a * A[k + 1]
        saida.append(lambda p, tf=tf, Af=Af: p + tf + (p - centro) @ Af.T)
    return saida


def rodar(seq, ingenuo: bool, erro_m: float, rng) -> dict:
    fps = seq.fps
    if ingenuo:
        par = ParametrosNarrativa(raio_finalizacao_entrada=20, raio_finalizacao_saida=20,
                                  folga_entrada=5, folga_saida=5, quadros_confirmacao=1)
        conf_posse = 1
    else:
        par, conf_posse = ParametrosNarrativa(), 3
    times = [Time("Esquerda", "ESQ", (0, 0, 0)), Time("Direita", "DIR", (0, 0, 0))]
    partida = Partida(times[0], times[1], fps=fps, em_metros=True, quadros_confirmacao=conf_posse)
    maquina = MaquinaNarrativa(DIRECAO_ATAQUE, par)
    ruido = campo_de_ruido(len(seq.quadros), fps, erro_m, rng)

    estados, posses = [], []
    for i, q in enumerate(seq.quadros):
        jog = q.jogadores()
        pos = np.array([a.xy for a in jog]).reshape(-1, 2)
        if erro_m > 0 and len(pos):
            pos = ruido[i](pos) + rng.normal(0, OSCILACAO_M, pos.shape)
        bola = None
        if q.bola_xy is not None:
            bola = ruido[i](q.bola_xy[None, :])[0] if erro_m > 0 else q.bola_xy
        adaptados = [_Atleta(times[a.equipe], float(np.hypot(*(p - bola))) if bola is not None else np.inf)
                     for a, p in zip(jog, pos)]
        partida.atualizar(adaptados, _Bola(bola is not None))
        posse = times.index(partida.time_com_posse) if partida.time_com_posse else None
        adv = pos[np.array([a.equipe != posse for a in jog])] if posse is not None and len(jog) else None
        estados.append(maquina.atualizar(i / fps, posse, bola, adv))
        posses.append(posse)

    trocas = sum(1 for a, b in zip(estados, estados[1:]) if a != b)
    # Estados que duram menos de meio segundo: o espectador mal consegue lê-los.
    curtos, dur = 0, 1
    for a, b in zip(estados, estados[1:]):
        if a == b:
            dur += 1
        else:
            curtos += dur < fps / 2
            dur = 1
    minutos = len(estados) / fps / 60
    return {
        "trocas_min": trocas / minutos,
        "curtos_min": curtos / minutos,
        "finalizacao": EstadoNarrativo.FINALIZACAO in estados,
        "dist": Counter(e.value for e in estados),
        "trocas_posse_min": sum(1 for a, b in zip(posses, posses[1:]) if a != b and a is not None and b is not None) / minutos,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Posse e narrativa sobre o SN-GSR")
    ap.add_argument("--dados", type=Path, required=True)
    ap.add_argument("--saida", type=Path, default=Path("resultados"))
    ap.add_argument("--erros", default="0,0.5,1.0,2.0", help="Erros de registro simulados, em metros")
    ap.add_argument("--semente", type=int, default=20261109)
    args = ap.parse_args()

    seqs = [carregar(p) for p in listar(args.dados)]
    linhas = []
    for erro in [float(x) for x in args.erros.split(",")]:
        for ingenuo in (True, False):
            rng = np.random.default_rng(args.semente)
            res = [(s, rodar(s, ingenuo, erro, rng)) for s in seqs]
            chute = [r["finalizacao"] for s, r in res if s.acao in ACOES_CHUTE]
            outros = [r["finalizacao"] for s, r in res if s.acao not in ACOES_CHUTE]
            dist = sum((r["dist"] for _, r in res), Counter())
            total = sum(dist.values())
            linha = {
                "erro_m": erro, "versao": "ingenua" if ingenuo else "histerese",
                "trocas_por_min": round(np.mean([r["trocas_min"] for _, r in res]), 1),
                "estados_curtos_por_min": round(np.mean([r["curtos_min"] for _, r in res]), 1),
                "trocas_posse_por_min": round(np.mean([r["trocas_posse_min"] for _, r in res]), 1),
                "finalizacao_em_chutes": f"{sum(chute)}/{len(chute)}",
                "finalizacao_em_outros": f"{sum(outros)}/{len(outros)}",
            }
            for e in EstadoNarrativo:
                linha[f"pct_{e.value}"] = round(100 * dist[e.value] / total, 1)
            linhas.append(linha)
            print(linha, flush=True)

    args.saida.mkdir(parents=True, exist_ok=True)
    with (args.saida / "narrativa_real.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)


if __name__ == "__main__":
    main()
