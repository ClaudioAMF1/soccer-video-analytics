"""Análise do estudo com usuários (experimento E6).

Compara, por participante, a condição estática e a dinâmica em três medidas:
acurácia, tempo de resposta e carga de trabalho (RTLX). Teste de postos
sinalizados de Wilcoxon, correção de Holm e correlação rank-biserial pareada
como tamanho de efeito. Ver estudo/PROTOCOLO.md.

Uso:
    python -m estudo.analise --respostas respostas.csv --carga carga.csv
    python -m estudo.analise --simular 24
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.stats import rankdata

CONDICOES = ("estatica", "dinamica")
DIMENSOES_TLX = ("mental", "fisica", "temporal", "desempenho", "esforco", "frustracao")


def rank_biserial_pareado(diferencas: np.ndarray) -> float:
    """Correlação rank-biserial pareada, em [-1, 1].

    Proporção da soma de postos favorável menos a desfavorável; diferenças nulas
    são descartadas, como no próprio teste de Wilcoxon. Vale 1 quando todos os
    participantes melhoram, e 0 quando melhoras e pioras se equilibram.
    """
    d = np.asarray(diferencas, dtype=float)
    d = d[d != 0]
    if len(d) == 0:
        return 0.0
    postos = rankdata(np.abs(d))
    positivos = postos[d > 0].sum()
    negativos = postos[d < 0].sum()
    return float((positivos - negativos) / (positivos + negativos))


def holm(valores_p: list[float]) -> list[float]:
    """Correção de Holm-Bonferroni; devolve os valores-p ajustados na ordem original."""
    p = np.asarray(valores_p, dtype=float)
    m = len(p)
    ordem = np.argsort(p)
    ajustados = np.empty(m)
    acumulado = 0.0
    for posicao, i in enumerate(ordem):
        acumulado = max(acumulado, min(1.0, (m - posicao) * p[i]))
        ajustados[i] = acumulado
    return ajustados.tolist()


def agregar(respostas: list[dict], carga: list[dict]) -> dict:
    """participante -> condição -> {acuracia, tempo_mediano, rtlx}."""
    por_participante: dict = {}
    for r in respostas:
        c = por_participante.setdefault(r["participante"], {}).setdefault(
            r["condicao"], {"acertos": [], "tempos": []}
        )
        c["acertos"].append(float(r["acerto"]))
        c["tempos"].append(float(r["tempo_s"]))

    saida: dict = {}
    for part, conds in por_participante.items():
        for cond, v in conds.items():
            saida.setdefault(part, {})[cond] = {
                "acuracia": float(np.mean(v["acertos"])),
                "tempo_mediano": float(np.median(v["tempos"])),
            }
    for linha in carga:
        cond = saida.setdefault(linha["participante"], {}).setdefault(linha["condicao"], {})
        cond["rtlx"] = float(np.mean([float(linha[d]) for d in DIMENSOES_TLX]))
    return saida


def comparar(agregado: dict, medida: str, maior_e_melhor: bool) -> dict:
    """Wilcoxon pareado entre as condições, só com participantes completos."""
    pares = [
        (v["estatica"][medida], v["dinamica"][medida])
        for v in agregado.values()
        if all(c in v and medida in v[c] for c in CONDICOES)
    ]
    if len(pares) < 2:
        raise ValueError(f"{medida}: participantes com as duas condições insuficientes")
    a = np.array([p[0] for p in pares])
    b = np.array([p[1] for p in pares])
    # Diferença orientada para que positivo signifique vantagem da dinâmica.
    dif = (b - a) if maior_e_melhor else (a - b)

    if np.all(dif == 0):
        estatistica, p = 0.0, 1.0
    else:
        res = stats.wilcoxon(dif, zero_method="wilcox", alternative="two-sided")
        estatistica, p = float(res.statistic), float(res.pvalue)

    q = lambda x: (float(np.percentile(x, 25)), float(np.percentile(x, 75)))
    return {
        "medida": medida, "n": len(pares),
        "mediana_estatica": float(np.median(a)), "iqr_estatica": q(a),
        "mediana_dinamica": float(np.median(b)), "iqr_dinamica": q(b),
        "W": estatistica, "p": p,
        "r_rb": rank_biserial_pareado(dif),
    }


def analisar(respostas: list[dict], carga: list[dict]) -> list[dict]:
    agregado = agregar(respostas, carga)
    resultados = [
        comparar(agregado, "acuracia", maior_e_melhor=True),
        comparar(agregado, "tempo_mediano", maior_e_melhor=False),
        comparar(agregado, "rtlx", maior_e_melhor=False),
    ]
    for r, p_aj in zip(resultados, holm([r["p"] for r in resultados])):
        r["p_holm"] = p_aj
    return resultados


def simular(n: int = 24, efeito: float = 0.12, semente: int = 7) -> tuple[list[dict], list[dict]]:
    """Dados sintéticos com vantagem moderada da condição dinâmica.

    Servem apenas para demonstrar e testar a análise. Não são resultado.
    """
    rng = np.random.default_rng(semente)
    respostas, carga = [], []
    for i in range(n):
        part = f"P{i + 1:02d}"
        habilidade = rng.normal(0.0, 0.08)
        for cond in CONDICOES:
            bonus = efeito if cond == "dinamica" else 0.0
            p_acerto = np.clip(0.55 + habilidade + bonus, 0.05, 0.95)
            for clipe in range(6):  # 6 clipes x 3 perguntas = 18 por condição
                for questao in "ABC":
                    respostas.append({
                        "participante": part, "condicao": cond, "clipe": f"c{clipe}",
                        "questao": questao, "acerto": int(rng.random() < p_acerto),
                        "tempo_s": round(float(rng.lognormal(np.log(12 - 20 * bonus), 0.3)), 2),
                    })
            base = 55 - 60 * bonus
            linha = {"participante": part, "condicao": cond}
            for d in DIMENSOES_TLX:
                linha[d] = float(np.clip(rng.normal(base if d != "fisica" else 10, 12), 0, 100))
            carga.append(linha)
    return respostas, carga


def _ler(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tabela_markdown(resultados: list[dict]) -> str:
    nomes = {"acuracia": "Acurácia", "tempo_mediano": "Tempo (s)", "rtlx": "RTLX"}
    linhas = [
        "| Medida | n | Estática: mediana [IQR] | Dinâmica: mediana [IQR] | W | p | p (Holm) | r_rb |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in resultados:
        fmt = lambda m, iqr: f"{m:.2f} [{iqr[0]:.2f}; {iqr[1]:.2f}]"
        linhas.append(
            f"| {nomes[r['medida']]} | {r['n']} | {fmt(r['mediana_estatica'], r['iqr_estatica'])} | "
            f"{fmt(r['mediana_dinamica'], r['iqr_dinamica'])} | {r['W']:.1f} | {r['p']:.4f} | "
            f"{r['p_holm']:.4f} | {r['r_rb']:+.2f} |"
        )
    return "\n".join(linhas)


def main() -> None:
    ap = argparse.ArgumentParser(description="Análise do estudo com usuários (E6)")
    ap.add_argument("--respostas", type=Path)
    ap.add_argument("--carga", type=Path)
    ap.add_argument("--simular", type=int, default=None, metavar="N",
                    help="Gera N participantes sintéticos para demonstrar a análise")
    args = ap.parse_args()

    if args.simular:
        respostas, carga = simular(args.simular)
        print(f"DADOS SINTÉTICOS ({args.simular} participantes): demonstração, não resultado.\n")
    elif args.respostas and args.carga:
        respostas, carga = _ler(args.respostas), _ler(args.carga)
    else:
        raise SystemExit("informe --respostas e --carga, ou --simular N")

    print(tabela_markdown(analisar(respostas, carga)))
    print("\nr_rb > 0 indica vantagem da condição dinâmica.")


if __name__ == "__main__":
    main()
