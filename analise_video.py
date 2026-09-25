"""Pipeline de análise tática sobre vídeo de transmissão.

Gera o vídeo anotado usado como figura qualitativa do artigo. Os números
reportados no texto **não** saem daqui: vêm de `experiments/`, executados sobre
o SoccerNet com anotação de referência.
"""
from __future__ import annotations

import argparse

import cv2
import numpy as np
import PIL
from norfair import Tracker, Video
from norfair.camera_motion import MotionEstimator
from norfair.distances import mean_euclidean

from config.filtros_cores import filtros
from inference import Converter, Detector, HSVClassifier, InertiaClassifier
from soccer.jogador import Jogador
from soccer.partida import Partida
from soccer.time import Time
from utils.funcoes_execucao import (
    atualizar_estimador_movimento,
    obter_bola_principal,
    obter_deteccoes_bola,
    obter_deteccoes_jogadores,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Análise tática de vídeos de futebol")
    p.add_argument("--video", default="videos/Miami_X_Palmeiras.mp4", help="Caminho do vídeo.")
    p.add_argument("--modelo", default="yolov8x.pt", help="Pesos do detector.")
    p.add_argument("--homografia", default=None,
                   help="Arquivo .npy com a homografia imagem->campo. Sem ela, "
                        "a posse é decidida em pixels (modo degradado).")
    p.add_argument("--tatico", action="store_true", help="Habilita todas as sobreposições.")
    args = p.parse_args()
    args.linhas_formacao = args.poligonos_formacao = args.rastro_bola = args.posse = args.tatico
    return args


def main() -> None:
    args = parse_args()
    print("Iniciando análise tática")

    video = Video(input_path=args.video)
    fps = video.video_capture.get(cv2.CAP_PROP_FPS)
    total_frames = int(video.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))

    # Um único detector: a versão anterior instanciava dois modelos idênticos e
    # executava ambos por quadro sobre a mesma imagem, dobrando o custo de
    # inferência para obter exatamente o mesmo resultado.
    detector = Detector(args.modelo)

    classificador = InertiaClassifier(classifier=HSVClassifier(filters=filtros), inertia=30)

    homografia = np.load(args.homografia) if args.homografia else None
    if homografia is None:
        print("AVISO: sem homografia, a posse usa limiar em pixels, que não é "
              "invariante à escala. Use --homografia para medir em metros.")

    time_casa = Time(nome="Inter Miami", abreviacao="MIA", cor=(221, 160, 221))
    time_visitante = Time(nome="Palmeiras", abreviacao="PAL", cor=(245, 245, 245))
    partida = Partida(time_casa, time_visitante, fps=fps, homografia=homografia)

    rastreador_jogadores = Tracker(distance_function=mean_euclidean, distance_threshold=200)
    rastreador_bola = Tracker(distance_function=mean_euclidean, distance_threshold=250)
    estimador_movimento = MotionEstimator()

    for i, frame in enumerate(video):
        # Uma inferência por quadro, reaproveitada pelos dois filtros de classe.
        deteccoes = detector.predict(frame)
        det_jogadores = obter_deteccoes_jogadores(_Fixo(deteccoes), frame)
        det_bola = obter_deteccoes_bola(_Fixo(deteccoes), frame, usar_bola_esportiva=True)

        transformacoes = atualizar_estimador_movimento(
            estimador_movimento, det_jogadores + det_bola, frame
        )
        rastreados_jog = rastreador_jogadores.update(
            detections=det_jogadores, coord_transformations=transformacoes
        )
        rastreados_bola = rastreador_bola.update(
            detections=det_bola, coord_transformations=transformacoes
        )

        classificadas = classificador.predict_from_detections(
            detections=Converter.TrackedObjects_to_Detections(rastreados_jog), img=frame
        )
        jogadores = Jogador.criar_lista_de_deteccoes(classificadas, partida.times)
        bola = obter_bola_principal(
            Converter.TrackedObjects_to_Detections(rastreados_bola), partida
        )

        partida.atualizar(jogadores, bola)

        frame_pil = PIL.Image.fromarray(frame)
        for jogador in jogadores:
            frame_pil = jogador.desenhar(frame_pil)
        frame_pil = partida.desenhar_elementos(frame_pil, jogadores, args)
        video.write(np.array(frame_pil))

        if i % 30 == 0 and total_frames > 0:
            print(f"Processando: {i / total_frames * 100:.1f}%", end="\r")

    print(f"\nConcluído. Vídeo de saída: {video.output_path}")


class _Fixo:
    """Adaptador que devolve um resultado de detecção já calculado.

    Permite que as funções de filtragem, que esperam um detector, reutilizem a
    inferência única do quadro em vez de executá-la novamente.
    """

    def __init__(self, df):
        self._df = df

    def predict(self, _frame):
        return self._df


if __name__ == "__main__":
    main()
