"""Etapa 1: extrai de um jogo gravado os dados estruturados, sem desenhar nada.

Primeira passada: detector, rastreador, classificador de equipes e estimador de
movimento de câmera percorrem o vídeo e guardam, para cada quadro, apenas
medições em pixels. Segunda passada (`exportacao.pipeline`): registro por
quadros-chave, projeção para o campo, velocidades, posse, controle de espaço e
estado narrativo, gravados num único JSON lido pelo player em `web/`.

Uso:
    python anotar.py --video jogo.mp4 --quadros 0,250,500 --saida anotacoes.json
    python extrair.py --video jogo.mp4 --anotacoes anotacoes.json \\
        --equipes "Palmeiras,Inter Miami" --saida web/dados/jogo.json

Limitações conhecidas, discutidas no artigo:
- o detector COCO não distingue goleiros, que por isso não são excluídos do
  casco convexo (o modelo ajustado do experimento E1 resolve);
- a bola é projetada supondo contato com o gramado; bolas altas ficam fora de
  posição enquanto estão no ar;
- atletas fora do enquadramento não são medidos.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from norfair import Tracker
from norfair.camera_motion import MotionEstimator
from norfair.distances import mean_euclidean

from config.filtros_cores import filtros
from exportacao import QuadroBruto, montar_exportacao, salvar
from exportacao.demo import CURVAS_E5
from inference import Converter, Detector, HSVClassifier, InertiaClassifier
from narrativa.confiabilidade import carregar_curvas_e5, decidir_exibicao
from pitch import estimar_homografia
from pitch.propagacao import grade_imagem
from utils.funcoes_execucao import (
    atualizar_estimador_movimento,
    obter_bola_principal,
    obter_deteccoes_bola,
    obter_deteccoes_jogadores,
)

CORES_PADRAO = ["#2F6FDE", "#E8871E"]  # azul e laranja: distinguíveis por daltônicos


class _Fixo:
    """Reaproveita a inferência única do quadro nas duas filtragens de classe."""

    def __init__(self, df):
        self._df = df

    def predict(self, _frame):
        return self._df


def _movimento(transformacao, largura: int, altura: int, anterior: np.ndarray) -> np.ndarray:
    """Matriz imagem do quadro -> referência absoluta, a partir do Norfair.

    Usa apenas `rel_to_abs`, o método que o próprio rastreador do Norfair
    emprega, e ajusta a matriz por amostragem. Evita depender do nome interno
    do atributo que guarda a homografia, que variou entre versões.
    """
    if transformacao is None:
        return anterior
    pts = grade_imagem(largura, altura)
    try:
        return estimar_homografia(pts, np.asarray(transformacao.rel_to_abs(pts.copy()), dtype=float))
    except (ValueError, np.linalg.LinAlgError):
        return anterior


def primeira_passada(video: str, modelo: str, nomes_equipes: list[str],
                     inicio: int, fim: int | None) -> tuple[list[QuadroBruto], float, int, int]:
    captura = cv2.VideoCapture(video)
    if not captura.isOpened():
        raise FileNotFoundError(f"não foi possível abrir {video}")
    fps = captura.get(cv2.CAP_PROP_FPS) or 25.0
    largura = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))

    detector = Detector(modelo)
    classificador = InertiaClassifier(classifier=HSVClassifier(filters=filtros), inertia=30)
    rastreador_jog = Tracker(distance_function=mean_euclidean, distance_threshold=200)
    rastreador_bola = Tracker(distance_function=mean_euclidean, distance_threshold=250)
    estimador = MotionEstimator()
    equipe_de = {nome: i for i, nome in enumerate(nomes_equipes)}

    captura.set(cv2.CAP_PROP_POS_FRAMES, inicio)
    brutos, movimento, f = [], np.eye(3), inicio
    while True:
        if fim is not None and f > fim:
            break
        ok, bgr = captura.read()
        if not ok:
            break
        # O detector e o classificador HSV foram escritos para a ordem de canais
        # que o Norfair entrega (a mesma do OpenCV); nada é convertido aqui.
        deteccoes = detector.predict(bgr)
        det_j = obter_deteccoes_jogadores(_Fixo(deteccoes), bgr)
        det_b = obter_deteccoes_bola(_Fixo(deteccoes), bgr, usar_bola_esportiva=True)

        transf = atualizar_estimador_movimento(estimador, det_j + det_b, bgr)
        movimento = _movimento(transf, largura, altura, movimento)

        rastreados = rastreador_jog.update(detections=det_j, coord_transformations=transf)
        classificadas = classificador.predict_from_detections(
            detections=Converter.TrackedObjects_to_Detections(rastreados), img=bgr
        )
        atletas = []
        for det in classificadas:
            (x1, _), (x2, y2) = det.points
            eq = equipe_de.get(det.data.get("classification"))
            atletas.append((int(det.data["id"]), eq, float((x1 + x2) / 2.0), float(y2), False))

        bola = obter_bola_principal(
            Converter.TrackedObjects_to_Detections(
                rastreador_bola.update(detections=det_b, coord_transformations=transf)
            )
        )
        bola_uv = None if bola.centro is None else (float(bola.centro[0]), float(bola.centro[1]))

        brutos.append(QuadroBruto(f, atletas, bola_uv, movimento.copy()))
        if f % 50 == 0:
            print(f"  quadro {f}", end="\r")
        f += 1

    captura.release()
    return brutos, fps, largura, altura


def main() -> None:
    p = argparse.ArgumentParser(description="Etapa 1: jogo gravado -> JSON estruturado")
    p.add_argument("--video", required=True)
    p.add_argument("--anotacoes", required=True, type=Path,
                   help="JSON de quadros-chave produzido por anotar.py")
    p.add_argument("--saida", required=True, type=Path)
    p.add_argument("--modelo", default="yolov8x.pt")
    p.add_argument("--equipes", required=True,
                   help="Nomes das equipes separados por vírgula, iguais aos de config/filtros_cores.py")
    p.add_argument("--direcao", default="1,-1",
                   help="Sentido de ataque de cada equipe no trecho: +1 para x crescente")
    p.add_argument("--cores", default=",".join(CORES_PADRAO))
    p.add_argument("--e5", type=Path, default=None, help="CSV do experimento E5")
    p.add_argument("--erro-registro", type=float, default=1.5,
                   help="Erro de registro medido no E2, em metros; decide o que exibir")
    p.add_argument("--inicio", type=int, default=0)
    p.add_argument("--fim", type=int, default=None)
    args = p.parse_args()

    nomes = [n.strip() for n in args.equipes.split(",")]
    direcoes = [int(d) for d in args.direcao.split(",")]
    cores = [c.strip() for c in args.cores.split(",")]
    if len(nomes) != 2 or len(direcoes) != 2 or len(cores) != 2:
        raise SystemExit("--equipes, --direcao e --cores exigem exatamente dois valores")
    equipes = [{"id": i, "nome": nomes[i], "cor": cores[i], "direcao": direcoes[i]} for i in range(2)]

    print("Primeira passada: detecção, rastreamento e movimento de câmera")
    brutos, fps, largura, altura = primeira_passada(args.video, args.modelo, nomes, args.inicio, args.fim)
    print(f"\n{len(brutos)} quadros medidos")

    if args.e5 is not None:
        curvas = carregar_curvas_e5(args.e5)
    else:
        print("AVISO: sem --e5, a regra de exibição usa a tabela de referência do E5 sintético.")
        curvas = {k: (np.array(x), np.array(y)) for k, (x, y) in CURVAS_E5.items()}
    exibicao = decidir_exibicao(curvas, args.erro_registro)

    print("Segunda passada: registro, projeção, posse, controle e narrativa")
    anotacoes = json.loads(args.anotacoes.read_text(encoding="utf-8"))
    doc = montar_exportacao(
        brutos, anotacoes, fps=fps, largura_img=largura, altura_img=altura,
        equipes=equipes, exibicao=exibicao, origem=str(args.video),
    )
    destino = salvar(doc, args.saida)
    print(f"Gravado: {destino}")


if __name__ == "__main__":
    main()
