import cv2
import norfair
import numpy as np
from typing import List, Tuple
import PIL
from PIL import ImageDraw

from soccer.draw import Draw


class Ball:
    def __init__(self, detection: norfair.Detection):
        """
        Initialize Ball

        Parameters
        ----------
        detection : norfair.Detection
            norfair.Detection containing the ball
        """
        self.detection = detection
        self.color = None
        self.trail_points = []
        self.max_trail_length = 30
        self.trail_enabled = True

    def set_color(self, match: "Match"):
        """
        Sets the color of the ball to the team color with the ball possession in the match.

        Parameters
        ----------
        match : Match
            Match object
        """
        if match.team_possession is None:
            return

        self.color = match.team_possession.color

        if self.detection:
            self.detection.data["color"] = match.team_possession.color

    def get_center(self, points: np.array) -> tuple:
        """
        Returns the center of the points

        Parameters
        ----------
        points : np.array
            2D points

        Returns
        -------
        tuple
            (x, y) coordinates of the center
        """
        x1, y1 = points[0]
        x2, y2 = points[1]

        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        return (center_x, center_y)

    @property
    def center(self) -> tuple:
        """
        Returns the center of the ball

        Returns
        -------
        tuple
            Center of the ball (x, y)
        """
        if self.detection is None:
            return None

        center = self.get_center(self.detection.points)
        round_center = np.round_(center)

        return round_center

    @property
    def center_abs(self) -> tuple:
        """
        Returns the center of the ball in absolute coordinates

        Returns
        -------
        tuple
            Center of the ball (x, y)
        """
        if self.detection is None:
            return None

        center = self.get_center(self.detection.absolute_points)
        round_center = np.round_(center)

        return round_center

    def update_trail(self):
        """Atualiza o rastro da bola com a posição atual"""
        if self.detection is None or not self.trail_enabled:
            return

        current_center = self.center
        if current_center is not None:
            self.trail_points.append(tuple(current_center))
            
            # Limita o tamanho do rastro
            if len(self.trail_points) > self.max_trail_length:
                self.trail_points.pop(0)

    def draw_trail(self, frame: PIL.Image.Image, color: Tuple[int, int, int] = None) -> PIL.Image.Image:
        """
        Desenha o rastro da bola no frame

        Parameters
        ----------
        frame : PIL.Image.Image
            Frame para desenhar
        color : Tuple[int, int, int], optional
            Cor do rastro, by default None (usa cor do time)

        Returns
        -------
        PIL.Image.Image
            Frame com rastro da bola
        """
        if len(self.trail_points) < 2:
            return frame

        if color is None:
            color = self.color if self.color else (255, 255, 255)

        draw = ImageDraw.Draw(frame, "RGBA")

        # Desenha linha conectando os pontos do rastro
        for i in range(1, len(self.trail_points)):
            # Calcula fade effect (pontos mais antigos são mais transparentes)
            alpha = int(255 * (i / len(self.trail_points)))
            
            # Calcula espessura da linha (pontos mais recentes são mais espessos)
            width = max(1, int(8 * (i / len(self.trail_points))))
            
            color_with_alpha = color + (alpha,)
            
            start_point = tuple(map(int, self.trail_points[i-1]))
            end_point = tuple(map(int, self.trail_points[i]))
            
            draw.line([start_point, end_point], fill=color_with_alpha, width=width)

        # Desenha pontos nas posições para maior visibilidade
        for i, point in enumerate(self.trail_points[-5:]):  # Últimos 5 pontos
            alpha = int(255 * ((i + 1) / 5))
            radius = 2 + i
            color_with_alpha = color + (alpha,)
            
            x, y = map(int, point)
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                        fill=color_with_alpha, outline=color + (255,), width=1)

        return frame

    def draw(self, frame: PIL.Image.Image) -> PIL.Image.Image:
        """
        Draw the ball on the frame with trail

        Parameters
        ----------
        frame : PIL.Image.Image
            Frame to draw on

        Returns
        -------
        PIL.Image.Image
            Frame with ball drawn
        """
        if self.detection is None:
            return frame

        # Atualiza rastro
        self.update_trail()
        
        # Desenha rastro
        if self.trail_enabled:
            frame = self.draw_trail(frame)

        # Desenha a bola
        frame = Draw.draw_detection(self.detection, frame)

        return frame

    def clear_trail(self):
        """Limpa o rastro da bola"""
        self.trail_points.clear()

    def toggle_trail(self):
        """Liga/desliga o rastro da bola"""
        self.trail_enabled = not self.trail_enabled
        if not self.trail_enabled:
            self.clear_trail()

    def __str__(self):
        return f"Ball: {self.center}"