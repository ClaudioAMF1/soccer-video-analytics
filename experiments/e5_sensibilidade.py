"""E5 — Propagação do erro de registro para métricas táticas.

Responde à pergunta: *qual erro de reprojeção, em metros, cada métrica tática
tolera antes de deixar de ser confiável?*

O experimento não depende de detector, de rastreador nem de vídeo: parte de uma
configuração de jogadores em coordenadas conhecidas, projeta-a para a imagem
por uma homografia de transmissão, perturba o registro com magnitude calibrada
e mede o desvio induzido em cada métrica. Por isso é o único experimento do
protocolo executável sem o SoccerNet, e o de menor custo computacional.

Uso:
    python -m experiments.e5_sensibilidade --repeticoes 200 --saida resultados/
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from controle import ParametrosMovimento, fracao_campo_controlada, regiao_dominante
from metrics.registro import estatisticas_erro
from pitch import ModeloCampo, calibrar_sigma, erro_reprojecao, perturbar_homografia, projetar
from soccer import metricas_taticas as mt

# Homografia campo -> imagem representativa de um enquadramento de transmissão
# (câmera lateral elevada, com o eixo longitudinal do campo na horizontal).
H_CAMPO_IMAGEM = np.array([
    [12.0, 1.5, 300.0],
    [0.8, -9.0, 820.0],
    [0.0002, -0.0035, 1.0],
])

ERROS_ALVO_M = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]


def formacao_exemplo() -> tuple[np.ndarray, np.ndarray]:
    """Duas equipes em organização defensiva/ofensiva típica.

    Returns:
        (posicoes (N, 2) em metros, equipes (N,) com 0 ou 1).
    """
    equipe_a = np.array([
        [30, 20], [28, 38], [34, 52], [44, 14],
        [46, 32], [48, 48], [58, 24], [56, 42], [40, 34], [52, 34],
    ], dtype=float)
    equipe_b = np.array([
        [62, 18], [64, 34], [66, 50], [74, 26],
        [76, 42], [80, 34], [70, 12], [72, 56], [84, 30], [86, 38],
    ], dtype=float)
    posicoes = np.vstack([equipe_a, equipe_b])
    equipes = np.array([0] * len(equipe_a) + [1] * len(equipe_b))
    return posicoes, equipes


def para_imagem(pontos_campo: np.ndarray) -> np.ndarray:
    """Projeta pontos do campo para a imagem pela homografia de referência."""
    h = np.column_stack([pontos_campo, np.ones(len(pontos_campo))])
    p = h @ H_CAMPO_IMAGEM.T
    return p[:, :2] / p[:, 2:3]


def metricas(posicoes: np.ndarray, equipes: np.ndarray, grade: np.ndarray,
             par: ParametrosMovimento, dominante_ref: np.ndarray | None = None) -> dict:
    """Métricas táticas avaliadas neste experimento.

    As cinco primeiras são agregadas de **nível de equipe**. As duas últimas são
    de **nível de jogador**, e existem para testar a hipótese de que a
    identidade individual é muito mais frágil ao erro de registro do que
    qualquer agregado: numa média sobre 22 atletas e milhares de células, os
    deslocamentos se cancelam parcialmente; na atribuição de uma célula a *um*
    atleta específico, não há o que cancelar.

    Args:
        dominante_ref: atribuição de célula -> atleta obtida com as posições
            verdadeiras. Quando fornecida, mede-se a concordância com ela.
    """
    pos_a, pos_b = posicoes[equipes == 0], posicoes[equipes == 1]
    dominante = regiao_dominante(posicoes, None, grade, par)

    saida = {
        "largura_a_m": mt.largura(pos_a),
        "profundidade_a_m": mt.profundidade(pos_a),
        "area_ocupacao_a_m2": mt.area_ocupacao(pos_a),
        "dispersao_a_m": mt.dispersao(pos_a),
        "dist_centroides_m": mt.distancia_entre_centroides(pos_a, pos_b),
        "controle_a": fracao_campo_controlada(posicoes, None, equipes, grade, 0, par),
    }
    # Concordância vale 1 quando a atribuição individual é idêntica à de
    # referência; o erro relativo calculado a jusante é, então, a discordância.
    saida["concordancia_dominante"] = (
        1.0 if dominante_ref is None else float((dominante == dominante_ref).mean())
    )
    saida["area_maior_dominio_m2"] = float(
        np.bincount(dominante, minlength=len(posicoes)).max()
    ) * (grade_passo_global[0] ** 2)
    return saida


# O passo da grade entra no cálculo de área dominada; guardado em escopo de
# módulo para não alterar a assinatura de `metricas` em todos os pontos de uso.
grade_passo_global = [2.0]


def executar(repeticoes: int, semente: int, passo_grade: float) -> list[dict]:
    rng = np.random.default_rng(semente)
    campo = ModeloCampo()
    par = ParametrosMovimento()
    grade = campo.grade(passo_grade)

    grade_passo_global[0] = passo_grade
    posicoes, equipes = formacao_exemplo()
    pts_img_jog = para_imagem(posicoes)

    # Marcos do campo: são eles que o registro usa, e é neles que o ruído entra.
    _, marcos_campo = campo.marcos_array()
    marcos_img = para_imagem(marcos_campo)

    # A condição de referência é o registro ajustado sobre correspondências
    # sem ruído — e não as coordenadas verdadeiras diretamente. Comparar o
    # estimado com o verdadeiro misturaria, no mesmo número, o efeito da
    # perturbação (que é o objeto do experimento) e o resíduo numérico do
    # próprio ajuste, que aparece como um piso espúrio nas métricas de
    # identidade, sensíveis a empates na fronteira entre regiões.
    H_ref = perturbar_homografia(marcos_img, marcos_campo, 0.0, rng)
    pos_ref = projetar(H_ref, pts_img_jog)
    dominante_ref = regiao_dominante(pos_ref, None, grade, par)

    verdade = metricas(pos_ref, equipes, grade, par, dominante_ref)
    linhas = []

    for alvo in ERROS_ALVO_M:
        sigma = 0.0 if alvo == 0 else calibrar_sigma(
            marcos_img, marcos_campo, alvo, repeticoes=40, rng=rng
        )

        acumulado = {k: [] for k in verdade}
        erros_registro = []

        for _ in range(repeticoes):
            try:
                H = perturbar_homografia(marcos_img, marcos_campo, sigma, rng)
            except (ValueError, np.linalg.LinAlgError):
                continue

            e = erro_reprojecao(H, marcos_img, marcos_campo)
            e = e[np.isfinite(e)]
            if len(e):
                erros_registro.append(e.mean())

            pos_est = projetar(H, pts_img_jog)
            if np.isnan(pos_est).any():
                continue

            obtido = metricas(pos_est, equipes, grade, par, dominante_ref)
            for k, v in obtido.items():
                acumulado[k].append(v)

        registro = estatisticas_erro(np.array(erros_registro))
        linha = {
            "erro_alvo_m": alvo,
            "sigma_px": round(sigma, 3),
            "erro_registro_medio_m": round(registro["media_m"], 4),
            "n_validas": len(acumulado["controle_a"]),
        }
        for k, valores in acumulado.items():
            v = np.array(valores, dtype=float)
            ref = verdade[k]
            linha[f"{k}__verdade"] = round(float(ref), 4)
            linha[f"{k}__media"] = round(float(v.mean()), 4)
            linha[f"{k}__desvio"] = round(float(v.std()), 4)
            linha[f"{k}__vies"] = round(float(v.mean() - ref), 4)
            # Erro relativo: torna métricas de unidades diferentes comparáveis.
            denom = abs(ref) if abs(ref) > 1e-9 else 1.0
            linha[f"{k}__erro_rel_pct"] = round(
                float(np.abs(v - ref).mean() / denom * 100.0), 3
            )
        linhas.append(linha)
        print(f"  erro alvo {alvo:.2f} m -> sigma {sigma:7.2f} px -> "
              f"registro medido {registro['media_m']:.3f} m ({linha['n_validas']} amostras)")

    return linhas


def salvar_csv(linhas: list[dict], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        escritor.writeheader()
        escritor.writerows(linhas)


def salvar_figura(linhas: list[dict], destino: Path) -> bool:
    """Curvas de degradação. Retorna False se matplotlib não estiver instalado."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    equipe = ["largura_a_m", "profundidade_a_m", "area_ocupacao_a_m2",
              "dispersao_a_m", "dist_centroides_m", "controle_a"]
    rot_equipe = ["Largura", "Profundidade", "Área de ocupação",
                  "Dispersão", "Distância entre centroides", "Controle de espaço"]
    jogador = ["concordancia_dominante", "area_maior_dominio_m2"]
    rot_jogador = ["Identidade do dominante (nível de jogador)",
                   "Maior domínio individual (nível de jogador)"]

    x = [l["erro_registro_medio_m"] for l in linhas]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    marcadores = ["o", "s", "^", "D", "v", "P"]
    for k, rot, m in zip(equipe, rot_equipe, marcadores):
        ax.plot(x, [l[f"{k}__erro_rel_pct"] for l in linhas],
                marker=m, linewidth=1.4, markersize=4, alpha=0.75, label=rot)
    for k, rot, m in zip(jogador, rot_jogador, ["X", "*"]):
        ax.plot(x, [l[f"{k}__erro_rel_pct"] for l in linhas],
                marker=m, linewidth=2.4, markersize=8, color=None,
                linestyle="--", label=rot)

    ax.set_xlabel("Erro médio de reprojeção (m)")
    ax.set_ylabel("Erro relativo da métrica (%)")
    ax.grid(True, alpha=0.3, linewidth=0.6)
    ax.legend(fontsize=8, framealpha=0.9)
    fig.tight_layout()
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=200)
    plt.close(fig)
    return True


def main() -> None:
    p = argparse.ArgumentParser(description="E5 — sensibilidade ao erro de registro")
    p.add_argument("--repeticoes", type=int, default=200)
    p.add_argument("--semente", type=int, default=20260925)
    p.add_argument("--passo-grade", type=float, default=2.0,
                   help="Resolução da grade de controle de espaço, em metros.")
    p.add_argument("--saida", type=Path, default=Path("resultados"))
    args = p.parse_args()

    print(f"E5 — {args.repeticoes} repeticoes por nivel de erro (semente {args.semente})")
    linhas = executar(args.repeticoes, args.semente, args.passo_grade)

    csv_path = args.saida / "e5_sensibilidade.csv"
    salvar_csv(linhas, csv_path)
    print(f"\nTabela: {csv_path}")

    fig_path = args.saida / "e5_sensibilidade.png"
    if salvar_figura(linhas, fig_path):
        print(f"Figura: {fig_path}")
    else:
        print("Figura nao gerada (matplotlib ausente); o CSV foi salvo.")


if __name__ == "__main__":
    main()
