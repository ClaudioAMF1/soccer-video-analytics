from typing import List

import norfair
import numpy as np
from norfair import Detection
from norfair.camera_motion import MotionEstimator

from inference import Converter, YoloV5
from soccer import Ball, Match


def get_ball_detections(
    ball_detector: YoloV5, frame: np.ndarray, use_sports_ball: bool = False
) -> List[norfair.Detection]:
    """
    Uses custom Yolov5 detector in order
    to get the predictions of the ball and converts it to
    Norfair.Detection list.

    Parameters
    ----------
    ball_detector : YoloV5
        YoloV5 detector for balls
    frame : np.ndarray
        Frame to get the ball detections from
    use_sports_ball : bool
        Whether to use 'sports ball' class from COCO instead of custom model

    Returns
    -------
    List[norfair.Detection]
        List of ball detections
    """
    ball_df = ball_detector.predict(frame)
    
    if use_sports_ball:
        # Filtrar apenas objetos da classe 'sports ball' (classe 32 no COCO)
        # Primeiro tentar por nome da classe
        if 'name' in ball_df.columns:
            ball_df = ball_df[ball_df["name"].str.contains("ball", case=False, na=False)]
        # Se não funcionar, tentar por ID da classe (32 = sports ball no COCO)
        elif 'class' in ball_df.columns:
            ball_df = ball_df[ball_df["class"] == 32]
        
        print(f"🔍 Detectadas {len(ball_df)} bolas esportivas no frame")
    
    # Filtrar por confiança
    confidence_threshold = 0.3 if use_sports_ball else 0.5
    ball_df = ball_df[ball_df["confidence"] > confidence_threshold]
    
    # Se não encontrou bola com o threshold padrão, tentar com threshold menor
    if len(ball_df) == 0 and use_sports_ball:
        ball_df = ball_detector.predict(frame)
        if 'name' in ball_df.columns:
            ball_df = ball_df[ball_df["name"].str.contains("ball", case=False, na=False)]
        elif 'class' in ball_df.columns:
            ball_df = ball_df[ball_df["class"] == 32]
        ball_df = ball_df[ball_df["confidence"] > 0.1]  # Threshold muito baixo
        print(f"🔍 Com threshold baixo: {len(ball_df)} bolas detectadas")
    
    return Converter.DataFrame_to_Detections(ball_df)


def get_player_detections(
    person_detector: YoloV5, frame: np.ndarray
) -> List[norfair.Detection]:
    """
    Uses YoloV5 Detector in order to detect the players
    in a match and filter out the detections that are not players
    and have confidence lower than 0.35.

    Parameters
    ----------
    person_detector : YoloV5
        YoloV5 detector
    frame : np.ndarray
        Frame to process

    Returns
    -------
    List[norfair.Detection]
        List of player detections
    """

    person_df = person_detector.predict(frame)
    
    # Filtrar apenas pessoas
    if 'name' in person_df.columns:
        person_df = person_df[person_df["name"] == "person"]
    # Se não tem coluna 'name', tentar por classe (0 = person no COCO)
    elif 'class' in person_df.columns:
        person_df = person_df[person_df["class"] == 0]
    
    person_df = person_df[person_df["confidence"] > 0.35]
    person_detections = Converter.DataFrame_to_Detections(person_df)
    
    print(f"👥 Detectadas {len(person_detections)} pessoas no frame")
    return person_detections


def create_mask(frame: np.ndarray, detections: List[norfair.Detection]) -> np.ndarray:
    """
    Creates mask in order to hide detections and goal counter for motion estimation

    Parameters
    ----------
    frame : np.ndarray
        Frame to create mask for.
    detections : List[norfair.Detection]
        Detections to hide.

    Returns
    -------
    np.ndarray
        Mask.
    """

    if not detections:
        mask = np.ones(frame.shape[:2], dtype=frame.dtype)
    else:
        detections_df = Converter.Detections_to_DataFrame(detections)
        mask = YoloV5.generate_predictions_mask(detections_df, frame, margin=40)

    # remove goal counter
    mask[69:200, 160:510] = 0

    return mask


def apply_mask(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """
    Applies a mask to an img

    Parameters
    ----------
    img : np.ndarray
        Image to apply the mask to
    mask : np.ndarray
        Mask to apply

    Returns
    -------
    np.ndarray
        img with mask applied
    """
    masked_img = img.copy()
    masked_img[mask == 0] = 0
    return masked_img


def update_motion_estimator(
    motion_estimator: MotionEstimator,
    detections: List[Detection],
    frame: np.ndarray,
) -> "CoordinatesTransformation":
    """
    Update coordinate transformations every frame

    Parameters
    ----------
    motion_estimator : MotionEstimator
        Norfair motion estimator class
    detections : List[Detection]
        List of detections to hide in the mask
    frame : np.ndarray
        Current frame

    Returns
    -------
    CoordinatesTransformation
        Coordinate transformation for the current frame
    """

    mask = create_mask(frame=frame, detections=detections)
    coord_transformations = motion_estimator.update(frame, mask=mask)
    return coord_transformations


def get_main_ball(detections: List[Detection], match: Match = None) -> Ball:
    """
    Gets the main ball from a list of balls detection

    The match is used in order to set the color of the ball to
    the color of the team in possession of the ball.

    Parameters
    ----------
    detections : List[Detection]
        List of detections
    match : Match, optional
        Match object, by default None

    Returns
    -------
    Ball
        Main ball
    """
    ball = Ball(detection=None)

    if match:
        ball.set_color(match)

    if detections:
        # Pegar a detecção com maior confiança
        best_detection = max(detections, key=lambda d: d.data.get("p", 0))
        ball.detection = best_detection
        print(f"⚽ Bola detectada com confiança: {best_detection.data.get('p', 0):.2f}")

    return ball