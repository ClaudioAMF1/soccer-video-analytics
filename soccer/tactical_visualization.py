from typing import List, Tuple
import numpy as np
import PIL
from PIL import ImageDraw
from scipy.spatial import ConvexHull
import math

from soccer.player import Player
from soccer.team import Team
from soccer.ball import Ball


class TacticalVisualization:
    """Classe responsável pela visualização tática completa dos times"""
    
    def __init__(self):
        self.formation_lines_enabled = True
        self.formation_polygons_enabled = True
        self.ball_trail_enabled = True
        self.ball_trail_points = []
        self.max_trail_length = 30
        
    def get_players_by_team(self, players: List[Player], team: Team) -> List[Player]:
        """Filtra jogadores por time"""
        return [player for player in players if player.team == team]
    
    def get_player_positions(self, players: List[Player]) -> List[Tuple[float, float]]:
        """Extrai posições dos jogadores (centro dos bounding boxes)"""
        positions = []
        for player in players:
            if player.detection is not None:
                x1, y1 = player.detection.points[0]
                x2, y2 = player.detection.points[1]
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                positions.append((center_x, center_y))
        return positions
    
    def calculate_team_centroid(self, positions: List[Tuple[float, float]]) -> Tuple[float, float]:
        """Calcula o centroide do time"""
        if not positions:
            return None
        
        x_coords = [pos[0] for pos in positions]
        y_coords = [pos[1] for pos in positions]
        
        centroid_x = sum(x_coords) / len(x_coords)
        centroid_y = sum(y_coords) / len(y_coords)
        
        return (centroid_x, centroid_y)
    
    def draw_connection_lines(self, img: PIL.Image.Image, positions: List[Tuple[float, float]], 
                            color: Tuple[int, int, int], alpha: int = 128) -> PIL.Image.Image:
        """Desenha linhas de conexão entre jogadores do mesmo time"""
        if len(positions) < 2:
            return img
            
        draw = ImageDraw.Draw(img, "RGBA")
        color_with_alpha = color + (alpha,)
        
        # Conecta cada jogador com os 2 mais próximos para evitar sobrecarga visual
        for i, pos1 in enumerate(positions):
            distances = []
            for j, pos2 in enumerate(positions):
                if i != j:
                    dist = math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
                    distances.append((dist, j))
            
            # Conecta com os 2 mais próximos
            distances.sort()
            for k in range(min(2, len(distances))):
                _, closest_idx = distances[k]
                pos2 = positions[closest_idx]
                
                draw.line([pos1, pos2], fill=color_with_alpha, width=2)
        
        return img
    
    def draw_formation_polygon(self, img: PIL.Image.Image, positions: List[Tuple[float, float]], 
                             color: Tuple[int, int, int], alpha: int = 60) -> PIL.Image.Image:
        """Desenha polígono convexo entre jogadores do mesmo time"""
        if len(positions) < 3:
            return img
            
        try:
            # Calcula o casco convexo
            points = np.array(positions)
            hull = ConvexHull(points)
            hull_points = [tuple(points[vertex]) for vertex in hull.vertices]
            
            draw = ImageDraw.Draw(img, "RGBA")
            color_with_alpha = color + (alpha,)
            
            # Desenha o polígono preenchido
            draw.polygon(hull_points, fill=color_with_alpha, outline=color + (128,), width=2)
            
        except Exception as e:
            # Em caso de erro (pontos colineares, etc.), desenha linhas simples
            pass
            
        return img
    
    def update_ball_trail(self, ball: Ball):
        """Atualiza o rastro da bola"""
        if ball is None or ball.detection is None:
            return
            
        ball_center = ball.center
        if ball_center is not None:
            self.ball_trail_points.append(ball_center)
            
            # Limita o tamanho do rastro
            if len(self.ball_trail_points) > self.max_trail_length:
                self.ball_trail_points.pop(0)
    
    def draw_ball_trail(self, img: PIL.Image.Image, team_possession_color: Tuple[int, int, int]) -> PIL.Image.Image:
        """Desenha o rastro visual da bola"""
        if len(self.ball_trail_points) < 2:
            return img
            
        draw = ImageDraw.Draw(img, "RGBA")
        
        # Desenha o rastro com fade effect
        for i in range(1, len(self.ball_trail_points)):
            # Calcula alpha baseado na posição no rastro (mais recente = mais opaco)
            alpha = int(255 * (i / len(self.ball_trail_points)))
            color_with_alpha = team_possession_color + (alpha,)
            
            # Calcula espessura da linha (mais recente = mais espesso)
            width = max(1, int(6 * (i / len(self.ball_trail_points))))
            
            start_point = tuple(map(int, self.ball_trail_points[i-1]))
            end_point = tuple(map(int, self.ball_trail_points[i]))
            
            draw.line([start_point, end_point], fill=color_with_alpha, width=width)
        
        return img
    
    def draw_tactical_analysis(self, img: PIL.Image.Image, players: List[Player], 
                             ball: Ball, teams: List[Team], team_possession: Team) -> PIL.Image.Image:
        """Desenha análise tática completa"""
        
        # Atualiza rastro da bola
        self.update_ball_trail(ball)
        
        # Desenha rastro da bola
        if team_possession and self.ball_trail_enabled:
            img = self.draw_ball_trail(img, team_possession.color)
        
        # Processa cada time
        for team in teams:
            team_players = self.get_players_by_team(players, team)
            if len(team_players) < 2:  # Precisa de pelo menos 2 jogadores
                continue
                
            positions = self.get_player_positions(team_players)
            
            # Desenha polígono da formação (se habilitado)
            if self.formation_polygons_enabled:
                img = self.draw_formation_polygon(img, positions, team.color)
            
            # Desenha linhas de conexão (se habilitado)
            if self.formation_lines_enabled:
                img = self.draw_connection_lines(img, positions, team.color)
        
        return img
    
    def toggle_formation_lines(self):
        """Liga/desliga linhas de formação"""
        self.formation_lines_enabled = not self.formation_lines_enabled
    
    def toggle_formation_polygons(self):
        """Liga/desliga polígonos de formação"""
        self.formation_polygons_enabled = not self.formation_polygons_enabled
    
    def toggle_ball_trail(self):
        """Liga/desliga rastro da bola"""
        self.ball_trail_enabled = not self.ball_trail_enabled
        if not self.ball_trail_enabled:
            self.ball_trail_points.clear()
    
    def clear_ball_trail(self):
        """Limpa o rastro da bola"""
        self.ball_trail_points.clear()