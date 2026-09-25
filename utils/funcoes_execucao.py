# utils/funcoes_execucao.py
from typing import List
import numpy as np
import cv2
from norfair import Detection
from norfair.camera_motion import MotionEstimator
from inference import Converter, Detector
from soccer.bola import Bola
from soccer.partida import Partida

# Limiares de confianca; o da bola e baixo porque o detector COCO tem
# dificuldade com objetos pequenos. O experimento E1 questiona esse paliativo.
LIMIAR_BOLA = 0.15
LIMIAR_PESSOA = 0.40

def _filtrar(df, nome_classe: str, id_classe: int, limiar: float) -> List[Detection]:
    """Filtra por classe e confiança, tolerando o caso sem nenhuma detecção.

    `Detector.predict` devolve um DataFrame vazio e *sem colunas* quando o
    modelo não encontra nada no quadro; indexar por "confidence" nesse caso
    levantava KeyError e derrubava a execução em qualquer corte de câmera,
    replay ou tela de placar.
    """
    if df is None or df.empty:
        return []
    if "name" in df.columns:
        df = df[df["name"] == nome_classe]
    elif "class" in df.columns:
        df = df[df["class"] == id_classe]
    if df.empty or "confidence" not in df.columns:
        return []
    return Converter.DataFrame_to_Detections(df[df["confidence"] > limiar])


def obter_deteccoes_bola(detector_bola: Detector, frame: np.ndarray,
                         usar_bola_esportiva: bool = False,
                         limiar: float = LIMIAR_BOLA) -> List[Detection]:
    df = detector_bola.predict(frame)
    if not usar_bola_esportiva:
        if df is None or df.empty or "confidence" not in df.columns:
            return []
        return Converter.DataFrame_to_Detections(df[df["confidence"] > limiar])
    return _filtrar(df, "sports ball", 32, limiar)


def obter_deteccoes_jogadores(detector_pessoas: Detector, frame: np.ndarray,
                              limiar: float = LIMIAR_PESSOA) -> List[Detection]:
    return _filtrar(detector_pessoas.predict(frame), "person", 0, limiar)

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