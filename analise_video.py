# analise_video.py
import argparse
import cv2
import numpy as np
import PIL
from norfair import Tracker, Video
from norfair.camera_motion import MotionEstimator
from norfair.distances import mean_euclidean

from config.filtros_cores import filtros
from inference import Converter, HSVClassifier, InertiaClassifier, Detector
from soccer.time import Time
from soccer.partida import Partida
from soccer.jogador import Jogador
from utils.funcoes_execucao import (
    obter_deteccoes_bola, obter_deteccoes_jogadores,
    obter_bola_principal, atualizar_estimador_movimento
)

parser = argparse.ArgumentParser(description="Análise Tática de Vídeos de Futebol")
parser.add_argument("--video", default="videos/Miami_X_Palmeiras.mp4", help="Caminho para o vídeo.")
parser.add_argument("--tatico", action="store_true", help="Habilita TODAS as visualizações táticas.")
args = parser.parse_args()
# Forçar todas as flags visuais se --tatico for usado
args.linhas_formacao = args.poligonos_formacao = args.rastro_bola = args.posse = args.tatico

print("⚽ INICIANDO ANÁLISE TÁTICA DE FUTEBOL ⚽")
video = Video(input_path=args.video)
fps = video.video_capture.get(cv2.CAP_PROP_FPS)

detector_jogadores = Detector("yolov8x.pt")
detector_bola = Detector("yolov8x.pt")
classificador_hsv = HSVClassifier(filters=filtros)
classificador_final = InertiaClassifier(classifier=classificador_hsv, inertia=30) # Aumentada a inércia

time_casa = Time(nome="Inter Miami", abreviacao="MIA", cor=(221, 160, 221))
time_visitante = Time(nome="Palmeiras", abreviacao="PAL", cor=(245, 245, 245))
partida = Partida(time_casa=time_casa, time_visitante=time_visitante, fps=fps)

rastreador_jogadores = Tracker(distance_function=mean_euclidean, distance_threshold=200)
rastreador_bola = Tracker(distance_function=mean_euclidean, distance_threshold=250)
estimador_movimento = MotionEstimator()

print("\n🚀 PROCESSANDO VÍDEO...")
total_frames = int(video.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))

for i, frame in enumerate(video):
    deteccoes_jogadores_raw = obter_deteccoes_jogadores(detector_jogadores, frame)
    deteccoes_bola_raw = obter_deteccoes_bola(detector_bola, frame, usar_bola_esportiva=True)
    
    transformacoes = atualizar_estimador_movimento(estimador_movimento, deteccoes_jogadores_raw + deteccoes_bola_raw, frame)
    
    objetos_rastreados_jogadores = rastreador_jogadores.update(detections=deteccoes_jogadores_raw, coord_transformations=transformacoes)
    objetos_rastreados_bola = rastreador_bola.update(detections=deteccoes_bola_raw, coord_transformations=transformacoes)

    deteccoes_rastreadas = Converter.TrackedObjects_to_Detections(objetos_rastreados_jogadores)
    deteccoes_classificadas = classificador_final.predict_from_detections(detections=deteccoes_rastreadas, img=frame)
    jogadores = Jogador.criar_lista_de_deteccoes(deteccoes_classificadas, partida.times)
    
    bola_deteccoes = Converter.TrackedObjects_to_Detections(objetos_rastreados_bola)
    bola_principal = obter_bola_principal(bola_deteccoes, partida)
    
    partida.atualizar(jogadores, bola_principal)

    frame_pil = PIL.Image.fromarray(frame)
    for jogador in jogadores:
        frame_pil = jogador.desenhar(frame_pil)
    frame_pil = partida.desenhar_elementos(frame_pil, jogadores, args)
    
    frame = np.array(frame_pil)
    video.write(frame)
    
    if i % 30 == 0:
        progresso = (i / total_frames) * 100 if total_frames > 0 else 0
        print(f"⏳ Processando: {progresso:.1f}%", end="\r")

print("\n" + "="*60 + "\n✅ PROCESSAMENTO CONCLUÍDO!\n" + f"🎬 Vídeo de saída: {video.output_path}\n" + "="*60)