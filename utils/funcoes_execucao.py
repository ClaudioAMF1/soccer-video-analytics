# utils/funcoes_execucao.py
from typing import List
import numpy as np
import cv2
from norfair import Detection
from norfair.camera_motion import MotionEstimator
from inference import Converter, Detector
from soccer.bola import Bola
from soccer.partida import Partida

def obter_deteccoes_bola(detector_bola: Detector, frame: np.ndarray, usar_bola_esportiva: bool = False) -> List[Detection]:
    df_bola = detector_bola.predict(frame)
    if usar_bola_esportiva and not df_bola.empty:
        if 'name' in df_bola.columns:
            df_bola = df_bola[df_bola["name"] == "sports ball"]
        elif 'class' in df_bola.columns:
            df_bola = df_bola[df_bola["class"] == 32]
    # Limiar de confiança da bola REDUZIDO para aumentar a detecção
    return Converter.DataFrame_to_Detections(df_bola[df_bola["confidence"] > 0.15])

def obter_deteccoes_jogadores(detector_pessoas: Detector, frame: np.ndarray) -> List[Detection]:
    df_pessoas = detector_pessoas.predict(frame)
    if not df_pessoas.empty:
        if 'name' in df_pessoas.columns:
            df_pessoas = df_pessoas[df_pessoas["name"] == "person"]
        elif 'class' in df_pessoas.columns:
            df_pessoas = df_pessoas[df_pessoas["class"] == 0]
    return Converter.DataFrame_to_Detections(df_pessoas[df_pessoas["confidence"] > 0.4])

def criar_mascara(frame: np.ndarray, deteccoes: List[Detection]) -> np.ndarray:
    mascara = np.ones(frame.shape[:2], dtype=frame.dtype)
    for det in deteccoes:
        pontos = det.points.astype(int)
        cv2.rectangle(mascara, tuple(pontos[0]), tuple(pontos[1]), 0, -1)
    return mascara

def atualizar_estimador_movimento(estimador_movimento: MotionEstimator, deteccoes: List[Detection], frame: np.ndarray) -> "CoordinatesTransformation":
    mascara = criar_mascara(frame=frame, deteccoes=deteccoes)
    return estimador_movimento.update(frame, mask=mascara)

def obter_bola_principal(deteccoes: List[Detection], partida: Partida = None) -> Bola:
    bola = Bola(detection=None)
    if partida:
        bola.definir_cor(partida)
    if deteccoes:
        bola.detection = max(deteccoes, key=lambda d: d.data.get("p", 0))
    return bola