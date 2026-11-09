"""E5 sobre transmissões reais: sensibilidade das métricas ao erro de registro.

Repete a análise de `e5_sensibilidade.py`, mas sobre configurações reais de
jogo e câmeras reais do SN-GSR, em vez de uma formação sintética. Para cada
quadro amostrado:

1. a homografia de referência é ajustada às posições anotadas (gabarito);
2. os marcos do campo visíveis no quadro são projetados na imagem: são os
   pontos que uma pessoa clicaria para registrar o campo;
3. esses pontos recebem ruído gaussiano de sigma pixels e a homografia é
   reajustada, como se a anotação tivesse sido imprecisa;
4. mede-se o erro de registro induzido (deslocamento médio dos atletas, em
   metros) e o desvio de cada métrica tática em relação à referência.

Como o efeito de um mesmo sigma depende do enquadramento, os resultados são
agrupados pelo erro de registro efetivamente induzido.

Uso:
    python -m experiments.e5_real --dados data/SoccerNetGS/test --saida resultados/
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from controle import ParametrosMovimento, fracao_campo_controlada, regiao_dominante
from experiments.soccernet import carregar, homografia_referencia, listar
from pitch import ModeloCampo, estimar_homografia, projetar
from soccer import metricas_taticas as mt

SIGMAS_PX = [0.0, 2.0, 4.0, 8.0, 12.0, 16.0, 24.0, 32.0]
FAIXAS_M = [(0.0, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0)]
RAIO_CELULAS = 15.0   # só células a até 15 m de algum atleta visível entram na identidade
MIN_MARCOS = 4


def marcos_visiveis(H_img_campo: np.ndarray, largura: int, altura: int,
                    uv_atletas: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Marcos do campo que aparecem dentro do quadro: (pontos na imagem, no campo)."""
    _, campo = ModeloCampo().marcos_array()
    G = np.linalg.inv(H_img_campo)
    h = np.column_stack([campo, np.ones(len(campo))]) @ G.T
    # Pontos atrás da câmera têm w com sinal oposto ao dos atletas visíveis.
    sinal = np.sign((np.column_stack([projetar(H_img_campo, uv_atletas), np.ones(len(uv_atletas))]) @ G.T)[:, 2].mean())
    frente = np.sign(h[:, 2]) == sinal
    uv = h[:, :2] / h[:, 2:3]
    dentro = frente & (uv[:, 0] >= 0) & (uv[:, 0] <= largura) & (uv[:, 1] >= 0) & (uv[:, 1] <= altura)
    return uv[dentro], campo[dentro]


def metricas(pos: np.ndarray, equipes: np.ndarray, goleiro: np.ndarray, grade: np.ndarray,
             perto: np.ndarray, par: ParametrosMovimento, dom_ref: np.ndarray | None) -> dict:
    saida = {}
    for e in (0, 1):
        linha = pos[(equipes == e) & ~goleiro]
        if len(linha) >= 3:
            saida[f"largura_{e}"] = mt.largura(linha)
            saida[f"profundidade_{e}"] = mt.profundidade(linha)
            saida[f"area_{e}"] = mt.area_ocupacao(linha)
    saida["controle_0"] = fracao_campo_controlada(pos, None, equipes, grade, 0, par)
    dom = regiao_dominante(pos, None, grade[perto], par)
    saida["_dom"] = dom
    saida["identidade"] = 1.0 if dom_ref is None else float((dom == dom_ref).mean())
    return saida


GRUPOS = {
    "largura": ["largura_0", "largura_1"],
    "profundidade": ["profundidade_0", "profundidade_1"],
    "area_ocupacao": ["area_0", "area_1"],
    "controle_equipe": ["controle_0"],
    "identidade_dominante": ["identidade"],
}


def executar(raiz: Path, passo: int, repeticoes: int, semente: int) -> tuple[list[dict], dict]:
    rng = np.random.default_rng(semente)
    par = ParametrosMovimento()
    grade = ModeloCampo().grade(2.0)
    amostras = []            # (erro_induzido_m, grupo, erro_relativo)
    contagem = {"quadros": 0, "sem_referencia": 0, "poucos_marcos": 0, "usados": 0, "marcos": []}

    for pasta in listar(raiz):
        seq = carregar(pasta)
        for q in seq.quadros[::passo]:
            contagem["quadros"] += 1
            jog = q.jogadores()
            H = homografia_referencia(q)
            if H is None or len(jog) < 6 or len({a.equipe for a in jog}) < 2:
                contagem["sem_referencia"] += 1
                continue
            uv = np.array([a.uv for a in jog])
            m_uv, m_xy = marcos_visiveis(H, seq.largura, seq.altura, uv)
            contagem["marcos"].append(len(m_uv))
            if len(m_uv) < MIN_MARCOS:
                contagem["poucos_marcos"] += 1
                continue
            contagem["usados"] += 1

            equipes = np.array([a.equipe for a in jog])
            goleiro = np.array([a.papel == "goalkeeper" for a in jog])
            pos_ref = projetar(H, uv)
            dist = np.sqrt(((grade[:, None, :] - pos_ref[None, :, :]) ** 2).sum(axis=2)).min(axis=1)
            perto = dist <= RAIO_CELULAS
            ref = metricas(pos_ref, equipes, goleiro, grade, perto, par, None)

            for sigma in SIGMAS_PX[1:]:
                for _ in range(repeticoes):
                    try:
                        Hp = estimar_homografia(m_uv + rng.normal(0, sigma, m_uv.shape), m_xy)
                    except (ValueError, np.linalg.LinAlgError):
                        continue
                    pos = projetar(Hp, uv)
                    if not np.isfinite(pos).all():
                        continue
                    erro_m = float(np.sqrt(((pos - pos_ref) ** 2).sum(axis=1)).mean())
                    obt = metricas(pos, equipes, goleiro, grade, perto, par, ref["_dom"])
                    for grupo, chaves in GRUPOS.items():
                        rel = []
                        for k in chaves:
                            if k in ref and k in obt:
                                base = 1.0 if k == "identidade" else abs(ref[k])
                                if base > 1e-9:
                                    rel.append(abs(obt[k] - ref[k]) / base * 100.0)
                        if rel:
                            amostras.append((erro_m, grupo, float(np.mean(rel))))
        print(f"  {seq.nome}: {contagem['usados']} quadros usados até aqui", flush=True)

    linhas = []
    arr_e = np.array([a[0] for a in amostras])
    arr_g = np.array([a[1] for a in amostras])
    arr_v = np.array([a[2] for a in amostras])
    for lo, hi in FAIXAS_M:
        linha = {"faixa_m": f"{lo}-{hi}"}
        sel = (arr_e >= lo) & (arr_e < hi)
        linha["n"] = int((sel & (arr_g == "controle_equipe")).sum())
        linha["erro_medio_m"] = round(float(arr_e[sel].mean()), 3) if sel.any() else None
        for g in GRUPOS:
            v = arr_v[sel & (arr_g == g)]
            linha[g] = round(float(v.mean()), 2) if len(v) else None
        linhas.append(linha)
    return linhas, contagem


def main() -> None:
    ap = argparse.ArgumentParser(description="E5 sobre o SN-GSR")
    ap.add_argument("--dados", type=Path, required=True)
    ap.add_argument("--saida", type=Path, default=Path("resultados"))
    ap.add_argument("--passo", type=int, default=25, help="1 quadro a cada N (25 = 1 por segundo)")
    ap.add_argument("--repeticoes", type=int, default=4)
    ap.add_argument("--semente", type=int, default=20261109)
    args = ap.parse_args()

    linhas, c = executar(args.dados, args.passo, args.repeticoes, args.semente)
    args.saida.mkdir(parents=True, exist_ok=True)
    with (args.saida / "e5_real.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]))
        w.writeheader()
        w.writerows(linhas)

    marcos = np.array(c["marcos"])
    (args.saida / "e5_real_info.txt").write_text(
        f"quadros={c['usados']} marcos_mediana={np.median(marcos):.0f} "
        f"pct_4={100 * (marcos >= 4).mean():.1f} pct_6={100 * (marcos >= 6).mean():.1f}\n",
        encoding="utf-8")
    print(f"\nquadros amostrados: {c['quadros']} | sem referência: {c['sem_referencia']} | "
          f"com menos de {MIN_MARCOS} marcos visíveis: {c['poucos_marcos']} | usados: {c['usados']}")
    print(f"marcos visíveis por quadro: mediana {np.median(marcos):.0f}, "
          f">=4 em {100 * (marcos >= 4).mean():.0f}%, >=6 em {100 * (marcos >= 6).mean():.0f}%")
    print("\nerro relativo médio (%) por faixa de erro de registro:")
    for l in linhas:
        print(l)


if __name__ == "__main__":
    main()
