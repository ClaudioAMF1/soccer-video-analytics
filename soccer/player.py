from array import array
from typing import List
import math

import numpy as np
import PIL
from norfair import Detection

from soccer.ball import Ball
from soccer.draw import Draw
from soccer.team import Team


class Player:
    def __init__(self, detection: Detection):
        """
        Initialize Player with enhanced tactical capabilities

        Parameters
        ----------
        detection : Detection
            Detection containing the player
        """
        self.detection = detection
        self.team = None
        self.tactical_position = None  # Para análise de posição tática
        self.formation_role = None     # Para análise de formação

        if detection:
            if "team" in detection.data:
                self.team = detection.data["team"]

    def get_left_foot(self, points: np.array):
        x1, y1 = points[0]
        x2, y2 = points[1]
        return [x1, y2]

    def get_right_foot(self, points: np.array):
        return points[1]

    @property
    def center(self) -> np.array:
        """Retorna o centro do bounding box do jogador"""
        if self.detection is None:
            return None
        
        x1, y1 = self.detection.points[0]
        x2, y2 = self.detection.points[1]
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        return np.array([center_x, center_y])

    @property
    def left_foot(self):
        points = self.detection.points
        left_foot = self.get_left_foot(points)
        return left_foot

    @property
    def right_foot(self):
        points = self.detection.points
        right_foot = self.get_right_foot(points)
        return right_foot

    @property
    def left_foot_abs(self):
        points = self.detection.absolute_points
        left_foot_abs = self.get_left_foot(points)
        return left_foot_abs

    @property
    def right_foot_abs(self):
        points = self.detection.absolute_points
        right_foot_abs = self.get_right_foot(points)
        return right_foot_abs

    @property
    def feet(self) -> np.ndarray:
        return np.array([self.left_foot, self.right_foot])

    def distance_to_ball(self, ball: Ball) -> float:
        """
        Returns the distance between the player closest foot and the ball

        Parameters
        ----------
        ball : Ball
            Ball object

        Returns
        -------
        float
            Distance between the player closest foot and the ball
        """
        if self.detection is None or ball.center is None:
            return float('inf')

        left_foot_distance = np.linalg.norm(ball.center - self.left_foot)
        right_foot_distance = np.linalg.norm(ball.center - self.right_foot)

        return min(left_foot_distance, right_foot_distance)

    def distance_to_player(self, other_player: "Player") -> float:
        """
        Calcula distância entre dois jogadores

        Parameters
        ----------
        other_player : Player
            Outro jogador

        Returns
        -------
        float
            Distância entre os jogadores
        """
        if self.center is None or other_player.center is None:
            return float('inf')
        
        return np.linalg.norm(self.center - other_player.center)

    def get_nearest_teammates(self, players: List["Player"], n: int = 2) -> List["Player"]:
        """
        Retorna os N companheiros de time mais próximos

        Parameters
        ----------
        players : List[Player]
            Lista de todos os jogadores
        n : int
            Número de companheiros mais próximos

        Returns
        -------
        List[Player]
            Lista dos companheiros mais próximos
        """
        if self.team is None:
            return []

        teammates = [p for p in players if p.team == self.team and p != self]
        teammates.sort(key=lambda p: self.distance_to_player(p))
        
        return teammates[:n]

    def get_tactical_zone(self, field_width: int = 1920, field_height: int = 1080) -> str:
        """
        Determina a zona tática do jogador no campo

        Parameters
        ----------
        field_width : int
            Largura do campo em pixels
        field_height : int
            Altura do campo em pixels

        Returns
        -------
        str
            Zona tática (ex: "defense_left", "midfield_center", "attack_right")
        """
        if self.center is None:
            return "unknown"

        x, y = self.center
        
        # Dividir campo em zonas
        zone_width = field_width / 3  # defesa, meio, ataque
        zone_height = field_height / 3  # esquerda, centro, direita
        
        # Determinar zona vertical (defesa/meio/ataque)
        if x < zone_width:
            vertical_zone = "defense"
        elif x < 2 * zone_width:
            vertical_zone = "midfield"
        else:
            vertical_zone = "attack"
        
        # Determinar zona horizontal (esquerda/centro/direita)
        if y < zone_height:
            horizontal_zone = "left"
        elif y < 2 * zone_height:
            horizontal_zone = "center"
        else:
            horizontal_zone = "right"
        
        return f"{vertical_zone}_{horizontal_zone}"

    def is_in_formation_line(self, teammates: List["Player"], tolerance: float = 50.0) -> bool:
        """
        Verifica se o jogador está em linha com companheiros de time

        Parameters
        ----------
        teammates : List[Player]
            Lista de companheiros de time
        tolerance : float
            Tolerância para considerar "em linha" (pixels)

        Returns
        -------
        bool
            True se está em formação de linha
        """
        if len(teammates) < 2 or self.center is None:
            return False

        my_x, my_y = self.center
        
        # Verifica alinhamento horizontal (mesma linha y)
        horizontal_aligned = sum(1 for p in teammates 
                               if p.center is not None and abs(p.center[1] - my_y) < tolerance)
        
        # Verifica alinhamento vertical (mesma linha x)  
        vertical_aligned = sum(1 for p in teammates
                             if p.center is not None and abs(p.center[0] - my_x) < tolerance)
        
        return horizontal_aligned >= 1 or vertical_aligned >= 1

    def closest_foot_to_ball(self, ball: Ball) -> np.ndarray:
        """
        Returns the closest foot to the ball

        Parameters
        ----------
        ball : Ball
            Ball object

        Returns
        -------
        np.ndarray
            Closest foot to the ball (x, y)
        """
        if self.detection is None or ball.center is None:
            return None

        left_foot_distance = np.linalg.norm(ball.center - self.left_foot)
        right_foot_distance = np.linalg.norm(ball.center - self.right_foot)

        if left_foot_distance < right_foot_distance:
            return self.left_foot

        return self.right_foot

    def closest_foot_to_ball_abs(self, ball: Ball) -> np.ndarray:
        """
        Returns the closest foot to the ball in absolute coordinates

        Parameters
        ----------
        ball : Ball
            Ball object

        Returns
        -------
        np.ndarray
            Closest foot to the ball (x, y)
        """
        if self.detection is None or ball.center_abs is None:
            return None

        left_foot_distance = np.linalg.norm(ball.center_abs - self.left_foot_abs)
        right_foot_distance = np.linalg.norm(ball.center_abs - self.right_foot_abs)

        if left_foot_distance < right_foot_distance:
            return self.left_foot_abs

        return self.right_foot_abs

    def draw(
        self, frame: PIL.Image.Image, confidence: bool = False, id: bool = False,
        show_tactical_info: bool = False
    ) -> PIL.Image.Image:
        """
        Draw the player on the frame with optional tactical information

        Parameters
        ----------
        frame : PIL.Image.Image
            Frame to draw on
        confidence : bool, optional
            Whether to draw confidence text in bounding box, by default False
        id : bool, optional
            Whether to draw id text in bounding box, by default False
        show_tactical_info : bool, optional
            Whether to show tactical zone information, by default False

        Returns
        -------
        PIL.Image.Image
            Frame with player drawn
        """
        if self.detection is None:
            return frame

        if self.team is not None:
            self.detection.data["color"] = self.team.color

        frame = Draw.draw_detection(self.detection, frame, confidence=confidence, id=id)
        
        # Adicionar informações táticas se solicitado
        if show_tactical_info and self.center is not None:
            tactical_zone = self.get_tactical_zone()
            x1, y1 = self.detection.points[0]
            
            frame = Draw.draw_text(
                img=frame,
                origin=(x1, y1 - 40),
                text=tactical_zone,
                color=(255, 255, 0) if self.team else (255, 255, 255)
            )

        return frame

    def draw_pointer(self, frame: PIL.Image.Image) -> PIL.Image.Image:
        """
        Draw a pointer above the player

        Parameters
        ----------
        frame : PIL.Image.Image
            Frame to draw on

        Returns
        -------
        PIL.Image.Image
            Frame with pointer drawn
        """
        if self.detection is None:
            return frame

        color = None

        if self.team:
            color = self.team.color

        return Draw.draw_pointer(detection=self.detection, img=frame, color=color)

    def __str__(self):
        tactical_info = f", zone: {self.get_tactical_zone()}" if self.center is not None else ""
        return f"Player: {self.feet}, team: {self.team}{tactical_info}"

    def __eq__(self, other: "Player") -> bool:
        if not isinstance(self, Player) or not isinstance(other, Player):
            return False

        self_id = self.detection.data["id"]
        other_id = other.detection.data["id"]

        return self_id == other_id

    @staticmethod
    def have_same_id(player1: "Player", player2: "Player") -> bool:
        """
        Check if player1 and player2 have the same ids

        Parameters
        ----------
        player1 : Player
            One player
        player2 : Player
            Another player

        Returns
        -------
        bool
            True if they have the same id
        """
        if not player1 or not player2:
            return False
        if "id" not in player1.detection.data or "id" not in player2.detection.data:
            return False
        return player1 == player2

    @staticmethod
    def get_team_formation_analysis(players: List["Player"], team: Team) -> dict:
        """
        Analisa a formação tática de um time

        Parameters
        ----------
        players : List[Player]
            Lista de todos os jogadores
        team : Team
            Time para análise

        Returns
        -------
        dict
            Análise da formação do time
        """
        team_players = [p for p in players if p.team == team and p.center is not None]
        
        if len(team_players) < 3:
            return {"formation": "insufficient_players", "zones": {}}

        # Análise por zonas
        zones = {}
        for player in team_players:
            zone = player.get_tactical_zone()
            if zone not in zones:
                zones[zone] = 0
            zones[zone] += 1

        # Determinar formação aproximada baseada nas zonas
        defense_count = sum(count for zone, count in zones.items() if "defense" in zone)
        midfield_count = sum(count for zone, count in zones.items() if "midfield" in zone)
        attack_count = sum(count for zone, count in zones.items() if "attack" in zone)

        formation = f"{defense_count}-{midfield_count}-{attack_count}"

        return {
            "formation": formation,
            "zones": zones,
            "defense_players": defense_count,
            "midfield_players": midfield_count,
            "attack_players": attack_count,
            "total_players": len(team_players)
        }

    @staticmethod
    def calculate_team_compactness(players: List["Player"], team: Team) -> float:
        """
        Calcula a compactação do time (distância média entre jogadores)

        Parameters
        ----------
        players : List[Player]
            Lista de jogadores
        team : Team
            Time para análise

        Returns
        -------
        float
            Índice de compactação (menor = mais compacto)
        """
        team_players = [p for p in players if p.team == team and p.center is not None]
        
        if len(team_players) < 2:
            return 0.0

        total_distance = 0
        comparisons = 0

        for i, player1 in enumerate(team_players):
            for player2 in team_players[i+1:]:
                distance = player1.distance_to_player(player2)
                total_distance += distance
                comparisons += 1

        return total_distance / comparisons if comparisons > 0 else 0.0

    @staticmethod
    def get_team_centroid(players: List["Player"], team: Team) -> np.array:
        """
        Calcula o centroide (centro de massa) do time

        Parameters
        ----------
        players : List[Player]
            Lista de jogadores
        team : Team
            Time para análise

        Returns
        -------
        np.array
            Coordenadas do centroide [x, y]
        """
        team_players = [p for p in players if p.team == team and p.center is not None]
        
        if not team_players:
            return None

        positions = np.array([p.center for p in team_players])
        return np.mean(positions, axis=0)

    @staticmethod
    def draw_players(
        players: List["Player"],
        frame: PIL.Image.Image,
        confidence: bool = False,
        id: bool = False,
        show_tactical_info: bool = False,
    ) -> PIL.Image.Image:
        """
        Draw all players on the frame with enhanced tactical information

        Parameters
        ----------
        players : List[Player]
            List of Player objects
        frame : PIL.Image.Image
            Frame to draw on
        confidence : bool, optional
            Whether to draw confidence text in bounding box, by default False
        id : bool, optional
            Whether to draw id text in bounding box, by default False
        show_tactical_info : bool, optional
            Whether to show tactical information, by default False

        Returns
        -------
        PIL.Image.Image
            Frame with players drawn
        """
        for player in players:
            frame = player.draw(
                frame, 
                confidence=confidence, 
                id=id, 
                show_tactical_info=show_tactical_info
            )

        return frame

    @staticmethod
    def draw_tactical_analysis(
        players: List["Player"], 
        frame: PIL.Image.Image, 
        teams: List[Team]
    ) -> PIL.Image.Image:
        """
        Desenha análise tática completa na tela

        Parameters
        ----------
        players : List[Player]
            Lista de jogadores
        frame : PIL.Image.Image
            Frame do vídeo
        teams : List[Team]
            Lista de times

        Returns
        -------
        PIL.Image.Image
            Frame com análise tática
        """
        y_offset = 50
        
        for i, team in enumerate(teams):
            if team is None:
                continue
                
            # Análise de formação
            formation_analysis = Player.get_team_formation_analysis(players, team)
            compactness = Player.calculate_team_compactness(players, team)
            centroid = Player.get_team_centroid(players, team)
            
            # Posição do texto
            x_pos = 50 if i == 0 else frame.size[0] - 300
            
            # Informações do time
            info_texts = [
                f"{team.name}",
                f"Formação: {formation_analysis['formation']}",
                f"Jogadores: {formation_analysis['total_players']}",
                f"Compactação: {compactness:.1f}px",
            ]
            
            if centroid is not None:
                info_texts.append(f"Centro: ({centroid[0]:.0f}, {centroid[1]:.0f})")
            
            # Desenhar informações
            for j, text in enumerate(info_texts):
                frame = Draw.draw_text(
                    img=frame,
                    origin=(x_pos, y_offset + j * 20),
                    text=text,
                    color=team.color if j == 0 else (255, 255, 255)
                )
        
        return frame

    @staticmethod
    def from_detections(
        detections: List[Detection], teams: List[Team] = None
    ) -> List["Player"]:
        """
        Create a list of Player objects from a list of detections and a list of teams.

        It reads the classification string field of the detection, converts it to a
        Team object and assigns it to the player.

        Parameters
        ----------
        detections : List[Detection]
            List of detections
        teams : List[Team], optional
            List of teams, by default None

        Returns
        -------
        List[Player]
            List of Player objects
        """
        players = []

        for detection in detections:
            if detection is None:
                continue

            if "classification" in detection.data and teams:
                team_name = detection.data["classification"]
                team = Team.from_name(teams=teams, name=team_name)
                detection.data["team"] = team

            player = Player(detection=detection)
            players.append(player)

        return players