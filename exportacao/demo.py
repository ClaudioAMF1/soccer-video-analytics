"""Jogada sintética para demonstrar o player sem vídeo nem SoccerNet.

Gera uma jogada de 12 segundos entre duas equipes (4-3-3 contra 4-4-2), filmada
por uma câmera de transmissão virtual que acompanha a bola com panorâmica e
zoom. As medições resultantes, em pixels, passam pela mesma segunda passada
usada com vídeos reais (`exportacao.pipeline`), incluindo o registro por
quadros-chave. A demonstração, portanto, exercita o pipeline de verdade.

A jogada percorre todos os estados narrativos: construção, ataque, perda da
bola (transição do adversário), recuperação (transição) e um passe em
profundidade que termina em situação de finalização.

Diferença em relação a um vídeo real: aqui os 22 atletas existem em todos os
quadros, e os que saem do enquadramento vêm marcados com `vis = false`. Num
vídeo real, atletas fora do quadro simplesmente não são medidos.

Uso:
    python -m exportacao.demo --saida web/dados/demo.json
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from narrativa.confiabilidade import decidir_exibicao
from pitch import ModeloCampo

from .esquema import salvar
from .pipeline import QuadroBruto, montar_exportacao

FPS = 25.0
LARG, ALT = 1280, 720
MIN_MARCOS = 6

EQUIPES = [
    {"id": 0, "nome": "Azul", "cor": "#2F6FDE", "direcao": 1},
    {"id": 1, "nome": "Laranja", "cor": "#E8871E", "direcao": -1},
]

# Formações de base, em metros. Equipe 0 ataca para x = 105.
BASE_0 = np.array([
    [5, 34],
    [25, 10], [22, 26], [22, 42], [25, 58],
    [38, 20], [35, 34], [38, 48],
    [52, 14], [55, 34], [52, 54],
], dtype=float)
BASE_1 = np.array([
    [100, 34],
    [82, 12], [85, 27], [85, 41], [82, 56],
    [70, 12], [72, 27], [72, 41], [70, 56],
    [62, 22], [62, 40],
], dtype=float)

# Roteiro da bola: (instante em s, x, y, equipe com a bola).
ROTEIRO = [
    (0.0, 22, 34, 0), (2.0, 30, 18, 0), (4.0, 45, 30, 0), (6.0, 60, 50, 0),
    (7.0, 66, 44, 0), (7.3, 64, 42, 1), (9.0, 48, 38, 1), (9.4, 46, 36, 0),
    (10.6, 70, 30, 0), (11.6, 93, 36, 0), (12.4, 95, 35, 0),
]

# Tabela de referência do E5 (200 repetições). Com um vídeo real, a decisão de
# exibição usa o CSV produzido pelo próprio E5 e o erro de registro medido no E2.
CURVAS_E5 = {
    "largura_a_m": ([0.0, 0.52, 1.07, 1.92, 2.89], [0.0, 1.07, 2.31, 4.22, 6.23]),
    "profundidade_a_m": ([0.0, 0.52, 1.07, 1.92, 2.89], [0.0, 0.57, 1.03, 1.87, 3.05]),
    "area_ocupacao_a_m2": ([0.0, 0.52, 1.07, 1.92, 2.89], [0.0, 1.24, 2.46, 4.67, 6.9]),
    "dist_centroides_m": ([0.0, 0.52, 1.07, 1.92, 2.89], [0.0, 0.43, 0.86, 1.62, 2.49]),
    "controle_a": ([0.0, 0.52, 1.07, 1.92, 2.89], [0.0, 0.4, 0.82, 1.63, 2.36]),
    "concordancia_dominante": ([0.0, 0.52, 1.07, 1.92, 2.89], [0.0, 2.58, 4.54, 8.0, 11.92]),
    "area_maior_dominio_m2": ([0.0, 0.52, 1.07, 1.92, 2.89], [0.0, 0.88, 1.52, 2.48, 3.77]),
}


def camera(x_alvo: float, focal: float) -> np.ndarray:
    """Homografia campo -> imagem de uma câmera elevada atrás da linha lateral.

    Modelo pinhole: câmera 32 m atrás da lateral e 20 m acima do gramado,
    apontada para (x_alvo, meio do campo). Para pontos no plano z = 0, a projeção
    reduz-se a H = K [r1 r2 t].
    """
    C = np.array([x_alvo, -32.0, 20.0])
    alvo = np.array([x_alvo, 34.0, 0.0])
    frente = (alvo - C) / np.linalg.norm(alvo - C)
    direita = np.cross(frente, [0.0, 0.0, 1.0])
    direita /= np.linalg.norm(direita)
    baixo = np.cross(frente, direita)
    R = np.vstack([direita, baixo, frente])
    t = -R @ C
    K = np.array([[focal, 0, LARG / 2], [0, focal, ALT / 2], [0, 0, 1.0]])
    H = K @ np.column_stack([R[:, 0], R[:, 1], t])
    return H / H[2, 2]


def _bola(t: float) -> tuple[np.ndarray, int]:
    for (t0, x0, y0, e0), (t1, x1, y1, _) in zip(ROTEIRO, ROTEIRO[1:]):
        if t0 <= t <= t1:
            a = (t - t0) / (t1 - t0)
            return np.array([x0 + a * (x1 - x0), y0 + a * (y1 - y0)]), e0
    t_, x_, y_, e_ = ROTEIRO[-1]
    return np.array([x_, y_], dtype=float), e_


def _segmento(t: float) -> int:
    for k, ((t0, *_), (t1, *_)) in enumerate(zip(ROTEIRO, ROTEIRO[1:])):
        if t0 <= t < t1:
            return k
    return len(ROTEIRO) - 2


def _alvos(base: np.ndarray, bola: np.ndarray, equipe: int, com_bola: bool) -> np.ndarray:
    """Posição-alvo de cada atleta: o bloco acompanha a bola e se compacta."""
    alvo = base.copy()
    if equipe == 0:
        dx = np.clip(bola[0] - 45.0, -15.0, 30.0) * (0.8 if com_bola else 0.5)
    else:
        dx = np.clip(bola[0] - 60.0, -30.0, 6.0) * 0.5
    alvo[1:, 0] += dx
    alvo[1:, 1] += (bola[1] - 34.0) * 0.3
    alvo[0, 1] = 34.0 + (bola[1] - 34.0) * 0.15  # goleiro acompanha pouco
    return alvo


def simular(duracao: float = 12.4) -> tuple[list[np.ndarray], list[np.ndarray], list[int]]:
    """Posições verdadeiras (22, 2) e da bola a cada quadro, e o dono do roteiro."""
    n = int(round(duracao * FPS))
    pos = np.vstack([BASE_0, BASE_1])

    # Quem começa com a bola já está sobre ela no primeiro quadro.
    _, x0, y0, dono0 = ROTEIRO[0]
    base0 = BASE_0 if dono0 == 0 else BASE_1
    inicial = 1 + int(np.argmin(np.linalg.norm(base0[1:] - [x0, y0], axis=1))) + (0 if dono0 == 0 else 11)
    pos[inicial] = [x0 - 0.8 * EQUIPES[dono0]["direcao"], y0]
    posicoes, bolas, donos = [], [], []

    # Receptor de cada passe: o atleta de linha da equipe mais próximo do destino.
    receptores = {}
    for k, (_, x1, y1, _) in enumerate(ROTEIRO[1:]):
        dono = ROTEIRO[k + 1][3]
        base = BASE_0 if dono == 0 else BASE_1
        destino = np.array([x1, y1])
        idx = 1 + int(np.argmin(np.linalg.norm(base[1:] - destino, axis=1)))
        receptores[k] = idx + (0 if dono == 0 else 11)

    for q in range(n):
        t = q / FPS
        bola, dono = _bola(t)
        alvo = np.vstack([
            _alvos(BASE_0, bola, 0, dono == 0),
            _alvos(BASE_1, bola, 1, dono == 1),
        ])
        k = _segmento(t)
        receptor = receptores[k]
        t1, x1, y1, _ = ROTEIRO[k + 1]
        alvo[receptor] = [x1, y1]

        tau = np.full(22, 0.7)
        tau[receptor] = 0.25
        pos = pos + (alvo - pos) * (1.0 - np.exp(-(1.0 / FPS) / tau))[:, None]

        # Quem está com a bola a conduz.
        t0 = ROTEIRO[k][0]
        if t - t0 < 0.3:
            anterior = receptores[k - 1] if k > 0 else inicial
            pos[anterior] = bola - np.array([0.8 * EQUIPES[ROTEIRO[k][3]]["direcao"], 0.0])

        posicoes.append(pos.copy())
        bolas.append(bola.copy())
        donos.append(dono)
    return posicoes, bolas, donos


def gerar(passo_grade: float = 3.0, erro_registro_m: float = 1.5) -> dict:
    posicoes, bolas, _ = simular()
    n = len(posicoes)

    # Câmera virtual: panorâmica suave atrás da bola, zoom no terço final.
    x_cam, homografias = 40.0, []
    for q in range(n):
        alvo = float(np.clip(bolas[q][0], 30.0, 75.0))
        x_cam += (alvo - x_cam) * (1.0 - np.exp(-(1.0 / FPS) / 1.0))
        focal = 1500.0 + 150.0 * np.clip((bolas[q][0] - 60.0) / 35.0, 0.0, 1.0)
        homografias.append(camera(x_cam, focal))

    def para_img(H, pts):
        h = np.column_stack([pts, np.ones(len(pts))]) @ H.T
        return h[:, :2] / h[:, 2:3]

    brutos = []
    for q in range(n):
        H = homografias[q]
        img = para_img(H, posicoes[q])
        bola_img = para_img(H, bolas[q][None, :])[0]
        # Movimento de câmera: imagem deste quadro -> imagem do primeiro quadro.
        movimento = homografias[0] @ np.linalg.inv(H)
        atletas = [(i, 0 if i < 11 else 1, float(u), float(v), i in (0, 11))
                   for i, (u, v) in enumerate(img)]
        brutos.append(QuadroBruto(q, atletas, (float(bola_img[0]), float(bola_img[1])), movimento))

    # Anotação de quadros-chave: os marcos visíveis são projetados com a câmera
    # verdadeira, como faria uma pessoa clicando sobre eles.
    modelo = ModeloCampo()

    def visiveis(q):
        pontos = {}
        for nome, xy in modelo.marcos().items():
            u, v = para_img(homografias[q], xy[None, :])[0]
            if 0 <= u <= LARG and 0 <= v <= ALT:
                pontos[nome] = [float(u), float(v)]
        return pontos

    # Quem anota escolhe, perto de cada instante desejado, um quadro com marcos
    # suficientes; seis pontos bem espalhados tornam a estimativa estável.
    anotacoes = {}
    for desejado in (0, n // 2, n - 1):
        candidatos = sorted(range(n), key=lambda q: abs(q - desejado))
        escolhido = next((q for q in candidatos if len(visiveis(q)) >= MIN_MARCOS), None)
        if escolhido is None:
            raise RuntimeError(f"nenhum quadro com {MIN_MARCOS} marcos visíveis")
        anotacoes[str(escolhido)] = visiveis(escolhido)

    curvas = {k: (np.array(x), np.array(y)) for k, (x, y) in CURVAS_E5.items()}
    exibicao = decidir_exibicao(curvas, erro_registro_m)

    return montar_exportacao(
        brutos, anotacoes, fps=FPS, largura_img=LARG, altura_img=ALT,
        equipes=EQUIPES, exibicao=exibicao,
        origem=f"demo sintética (erro de registro assumido: {erro_registro_m} m)",
        passo_grade=passo_grade,
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Gera a jogada sintética de demonstração")
    p.add_argument("--saida", type=Path, default=Path("web/dados/demo.json"))
    p.add_argument("--erro-registro", type=float, default=1.5,
                   help="Erro de registro assumido, em metros, para a regra de exibição.")
    args = p.parse_args()
    doc = gerar(erro_registro_m=args.erro_registro)
    destino = salvar(doc, args.saida)
    estados = [q["estado"] for q in doc["quadros"]]
    ordem = [e for i, e in enumerate(estados) if i == 0 or estados[i - 1] != e]
    print(f"{len(doc['quadros'])} quadros -> {destino} ({destino.stat().st_size / 1024:.0f} KB)")
    print("sequência narrativa:", " -> ".join(ordem))
    print("exibição:", {k: v["exibir"] for k, v in doc["exibicao"].items()})


if __name__ == "__main__":
    main()
