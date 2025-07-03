# soccer/evento_passe.py

"""
Módulo para detecção de eventos de passe.
Funcionalidade futura a ser desenvolvida.
"""
from typing import List
import numpy as np
import PIL

class Pass:
    def __init__(self, start_ball_bbox: np.ndarray, end_ball_bbox: np.ndarray, team) -> None:
        self.start_ball_bbox = start_ball_bbox
        self.end_ball_bbox = end_ball_bbox
        self.team = team

    def __str__(self):
        return f"Passe do time {self.team.nome}"

class PassEvent:
    def __init__(self) -> None:
        self.ball = None
        self.closest_player = None
        self.init_player_with_ball = None
        self.last_player_with_ball = None
        self.player_with_ball_counter = 0
        self.player_with_ball_threshold = 3
        self.player_with_ball_threshold_dif_team = 4

    def update(self, closest_player, ball) -> None:
        pass  # Lógica a ser implementada

    def process_pass(self) -> None:
        pass  # Lógica a ser implementada