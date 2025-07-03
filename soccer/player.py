from array import array
from typing import List, Dict, Any, Optional, Tuple
import math

import numpy as np
import PIL
from PIL import ImageDraw
from norfair import Detection

from soccer.ball import Ball
from soccer.draw import Draw
from soccer.team import Team


class Player:
    """
    Classe para representação e análise de jogadores com capacidades táticas avançadas
    
    REQUISITOS IMPLEMENTADOS:
    - OBRIGATÓRIO: Visualização contínua da detecção dos jogadores
    - OBRIGATÓRIO: Times destacados com cores diferentes
    - Análise tática de posição e formação
    - Métricas de desempenho e movimento
    """
    
    def __init__(self, detection: Detection):
        """
        Inicializa Player com capacidades táticas aprimoradas
        
        Parameters
        ----------
        detection : Detection
            Detecção contendo o jogador
        """
        self.detection = detection
        self.team = None
        
        # Análise tática
        self.tactical_position = None     # Posição tática atual
        self.formation_role = None        # Papel na formação
        self.zone_history = []           # Histórico de zonas ocupadas
        
        # Métricas de movimento
        self.position_history = []       # Histórico de posições
        self.velocity = None             # Velocidade atual
        self.acceleration = None         # Aceleração atual
        self.distance_covered = 0        # Distância total percorrida
        
        # Análise de proximidade
        self.ball_distances = []         # Histórico de distâncias à bola
        self.teammate_distances = {}     # Distâncias aos companheiros
        
        # Configurações de visualização
        self.show_tactical_info = False
        self.show_movement_trail = False

        # Extrai team da detecção se disponível
        if detection and "team" in detection.data:
            self.team = detection.data["team"]

    def get_left_foot(self, points: np.array) -> List[float]:
        """Calcula posição do pé esquerdo"""
        try:
            x1, y1 = points[0]
            x2, y2 = points[1]
            return [float(x1), float(y2)]
        except (IndexError, TypeError):
            return [0.0, 0.0]

    def get_right_foot(self, points: np.array) -> List[float]:
        """Calcula posição do pé direito"""
        try:
            return [float(coord) for coord in points[1]]
        except (IndexError, TypeError):
            return [0.0, 0.0]

    @property
    def center(self) -> Optional[np.array]:
        """
        Retorna centro do bounding box do jogador
        
        Returns
        -------
        Optional[np.array]
            Centro do jogador [x, y] ou None se inválido
        """
        if self.detection is None or self.detection.points is None:
            return None
        
        try:
            x1, y1 = self.detection.points[0]
            x2, y2 = self.detection.points[1]
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            return np.array([center_x, center_y])
        except (IndexError, TypeError, ValueError):
            return None

    @property
    def left_foot(self) -> List[float]:
        """Posição do pé esquerdo em coordenadas relativas"""
        if self.detection is None or self.detection.points is None:
            return [0.0, 0.0]
        return self.get_left_foot(self.detection.points)

    @property
    def right_foot(self) -> List[float]:
        """Posição do pé direito em coordenadas relativas"""
        if self.detection is None or self.detection.points is None:
            return [0.0, 0.0]
        return self.get_right_foot(self.detection.points)

    @property
    def left_foot_abs(self) -> List[float]:
        """Posição do pé esquerdo em coordenadas absolutas"""
        if (self.detection is None or 
            not hasattr(self.detection, 'absolute_points') or 
            self.detection.absolute_points is None):
            return [0.0, 0.0]
        return self.get_left_foot(self.detection.absolute_points)

    @property
    def right_foot_abs(self) -> List[float]:
        """Posição do pé direito em coordenadas absolutas"""
        if (self.detection is None or 
            not hasattr(self.detection, 'absolute_points') or 
            self.detection.absolute_points is None):
            return [0.0, 0.0]
        return self.get_right_foot(self.detection.absolute_points)

    @property
    def feet(self) -> np.ndarray:
        """Array com posições dos dois pés"""
        return np.array([self.left_foot, self.right_foot])

    def update_position_history(self):
        """Atualiza histórico de posições e calcula métricas de movimento"""
        current_center = self.center
        if current_center is None:
            return
            
        # Adiciona posição atual ao histórico
        position_data = {
            'position': current_center.copy(),
            'timestamp': len(self.position_history),
            'tactical_zone': self.get_tactical_zone()
        }
        
        self.position_history.append(position_data)
        
        # Limita tamanho do histórico
        max_history = 100
        if len(self.position_history) > max_history:
            self.position_history.pop(0)
        
        # Calcula métricas de movimento
        self.calculate_movement_metrics()
        
        # Atualiza histórico de zonas
        current_zone = self.get_tactical_zone()
        if not self.zone_history or self.zone_history[-1] != current_zone:
            self.zone_history.append(current_zone)
            
        # Limita histórico de zonas
        if len(self.zone_history) > 20:
            self.zone_history.pop(0)

    def calculate_movement_metrics(self):
        """Calcula velocidade, aceleração e distância percorrida"""
        if len(self.position_history) < 2:
            return
            
        try:
            current_pos = self.position_history[-1]['position']
            previous_pos = self.position_history[-2]['position']
            
            # Calcula velocidade
            self.velocity = current_pos - previous_pos
            
            # Calcula distância percorrida
            distance = np.linalg.norm(self.velocity)
            self.distance_covered += distance
            
            # Calcula aceleração se possível
            if len(self.position_history) >= 3:
                prev_prev_pos = self.position_history[-3]['position']
                previous_velocity = previous_pos - prev_prev_pos
                self.acceleration = self.velocity - previous_velocity
                
        except (IndexError, TypeError, ValueError):
            pass

    def distance_to_ball(self, ball: Ball) -> float:
        """
        Calcula distância do jogador à bola (pé mais próximo)
        
        Parameters
        ----------
        ball : Ball
            Objeto da bola
            
        Returns
        -------
        float
            Distância mínima à bola
        """
        if self.detection is None or ball.center is None:
            return float('inf')

        try:
            ball_center = np.array(ball.center)
            left_foot = np.array(self.left_foot)
            right_foot = np.array(self.right_foot)
            
            left_distance = np.linalg.norm(ball_center - left_foot)
            right_distance = np.linalg.norm(ball_center - right_foot)
            
            distance = min(left_distance, right_distance)
            
            # Armazena no histórico
            self.ball_distances.append(distance)
            if len(self.ball_distances) > 50:  # Limita histórico
                self.ball_distances.pop(0)
                
            return distance
            
        except (TypeError, ValueError):
            return float('inf')

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
            Distância entre jogadores
        """
        if self.center is None or other_player.center is None:
            return float('inf')
        
        try:
            return float(np.linalg.norm(self.center - other_player.center))
        except (TypeError, ValueError):
            return float('inf')

    def get_nearest_teammates(self, players: List["Player"], n: int = 2) -> List["Player"]:
        """
        Retorna companheiros de time mais próximos
        
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

        # Filtra companheiros de time (excluindo o próprio jogador)
        teammates = []
        for player in players:
            if (player.team == self.team and 
                player != self and 
                player.center is not None):
                teammates.append(player)
        
        # Ordena por distância
        teammates.sort(key=lambda p: self.distance_to_player(p))
        
        return teammates[:n]

    def get_tactical_zone(self, field_width: int = 1920, field_height: int = 1080) -> str:
        """
        Determina zona tática do jogador no campo
        
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

        try:
            x, y = self.center
            
            # Divide campo em 3x3 zonas
            zone_width = field_width / 3   # defesa, meio, ataque
            zone_height = field_height / 3  # esquerda, centro, direita
            
            # Determina zona vertical (defesa/meio/ataque)
            if x < zone_width:
                vertical_zone = "defense"
            elif x < 2 * zone_width:
                vertical_zone = "midfield"
            else:
                vertical_zone = "attack"
            
            # Determina zona horizontal (esquerda/centro/direita)
            if y < zone_height:
                horizontal_zone = "left"
            elif y < 2 * zone_height:
                horizontal_zone = "center"
            else:
                horizontal_zone = "right"
            
            return f"{vertical_zone}_{horizontal_zone}"
            
        except (TypeError, ValueError):
            return "unknown"

    def is_in_formation_line(self, teammates: List["Player"], tolerance: float = 50.0) -> bool:
        """
        Verifica se jogador está em linha com companheiros
        
        Parameters
        ----------
        teammates : List[Player]
            Lista de companheiros de time
        tolerance : float
            Tolerância para considerar "em linha"
            
        Returns
        -------
        bool
            True se está em formação de linha
        """
        if len(teammates) < 2 or self.center is None:
            return False

        try:
            my_x, my_y = self.center
            
            # Conta alinhamentos horizontais e verticais
            horizontal_aligned = 0
            vertical_aligned = 0
            
            for teammate in teammates:
                if teammate.center is not None:
                    t_x, t_y = teammate.center
                    if abs(t_y - my_y) < tolerance:
                        horizontal_aligned += 1
                    if abs(t_x - my_x) < tolerance:
                        vertical_aligned += 1
            
            return horizontal_aligned >= 1 or vertical_aligned >= 1
            
        except (TypeError, ValueError):
            return False

    def get_formation_analysis(self, players: List["Player"]) -> Dict[str, Any]:
        """
        Análise da formação individual do jogador
        
        Parameters
        ----------
        players : List[Player]
            Lista de todos os jogadores
            
        Returns
        -------
        Dict[str, Any]
            Análise da posição na formação
        """
        if self.team is None:
            return {}
            
        teammates = [p for p in players if p.team == self.team and p != self]
        nearest_teammates = self.get_nearest_teammates(players, 3)
        
        analysis = {
            'tactical_zone': self.get_tactical_zone(),
            'teammates_count': len(teammates),
            'nearest_teammates_count': len(nearest_teammates),
            'in_formation_line': self.is_in_formation_line(nearest_teammates),
            'isolation_level': self.calculate_isolation_level(nearest_teammates),
            'zone_stability': self.calculate_zone_stability()
        }
        
        # Adiciona distâncias aos companheiros mais próximos
        if nearest_teammates:
            analysis['distances_to_nearest'] = [
                self.distance_to_player(teammate) for teammate in nearest_teammates
            ]
            analysis['avg_distance_to_teammates'] = sum(analysis['distances_to_nearest']) / len(analysis['distances_to_nearest'])
        
        return analysis

    def calculate_isolation_level(self, nearest_teammates: List["Player"]) -> float:
        """
        Calcula nível de isolamento do jogador
        
        Parameters
        ----------
        nearest_teammates : List[Player]
            Companheiros mais próximos
            
        Returns
        -------
        float
            Nível de isolamento (0 = bem conectado, 1 = isolado)
        """
        if not nearest_teammates:
            return 1.0  # Completamente isolado
            
        try:
            distances = [self.distance_to_player(teammate) for teammate in nearest_teammates]
            avg_distance = sum(distances) / len(distances)
            
            # Normaliza distância (100px = isolamento moderado)
            isolation = min(1.0, avg_distance / 100.0)
            return isolation
            
        except (ZeroDivisionError, TypeError):
            return 1.0

    def calculate_zone_stability(self) -> float:
        """
        Calcula estabilidade da zona tática
        
        Returns
        -------
        float
            Estabilidade (0 = muito instável, 1 = muito estável)
        """
        if len(self.zone_history) < 5:
            return 0.5  # Dados insuficientes
            
        try:
            # Conta mudanças de zona
            changes = 0
            for i in range(1, len(self.zone_history)):
                if self.zone_history[i] != self.zone_history[i-1]:
                    changes += 1
            
            # Calcula estabilidade
            stability = 1.0 - (changes / len(self.zone_history))
            return max(0.0, stability)
            
        except (ZeroDivisionError, TypeError):
            return 0.5

    def closest_foot_to_ball(self, ball: Ball) -> Optional[np.ndarray]:
        """
        Retorna pé mais próximo da bola
        
        Parameters
        ----------
        ball : Ball
            Objeto da bola
            
        Returns
        -------
        Optional[np.ndarray]
            Coordenadas do pé mais próximo
        """
        if self.detection is None or ball.center is None:
            return None

        try:
            ball_center = np.array(ball.center)
            left_foot = np.array(self.left_foot)
            right_foot = np.array(self.right_foot)
            
            left_distance = np.linalg.norm(ball_center - left_foot)
            right_distance = np.linalg.norm(ball_center - right_foot)

            return left_foot if left_distance < right_distance else right_foot
            
        except (TypeError, ValueError):
            return None

    def closest_foot_to_ball_abs(self, ball: Ball) -> Optional[np.ndarray]:
        """
        Retorna pé mais próximo da bola em coordenadas absolutas
        
        Parameters
        ----------
        ball : Ball
            Objeto da bola
            
        Returns
        -------
        Optional[np.ndarray]
            Coordenadas absolutas do pé mais próximo
        """
        if self.detection is None or ball.center_abs is None:
            return None

        try:
            ball_center = np.array(ball.center_abs)
            left_foot = np.array(self.left_foot_abs)
            right_foot = np.array(self.right_foot_abs)
            
            left_distance = np.linalg.norm(ball_center - left_foot)
            right_distance = np.linalg.norm(ball_center - right_foot)

            return left_foot if left_distance < right_distance else right_foot
            
        except (TypeError, ValueError):
            return None

    def draw(self, frame: PIL.Image.Image, confidence: bool = False, id: bool = False,
            show_tactical_info: bool = False) -> PIL.Image.Image:
        """
        REQUISITO OBRIGATÓRIO: Desenha jogador com cor do time
        
        Parameters
        ----------
        frame : PIL.Image.Image
            Frame para desenhar
        confidence : bool, optional
            Mostrar confiança da detecção
        id : bool, optional
            Mostrar ID do jogador
        show_tactical_info : bool, optional
            Mostrar informações táticas
            
        Returns
        -------
        PIL.Image.Image
            Frame com jogador desenhado
        """
        if self.detection is None:
            return frame

        try:
            # REQUISITO OBRIGATÓRIO: Define cor do time
            if self.team is not None:
                self.detection.data["color"] = self.team.color

            # Desenha bounding box do jogador
            frame = Draw.draw_detection(
                self.detection, 
                frame, 
                confidence=confidence, 
                id=id
            )
            
            # Informações táticas se solicitado
            if show_tactical_info and self.center is not None:
                self.draw_tactical_info(frame)
                
        except Exception as e:
            print(f"⚠️ Erro ao desenhar jogador: {e}")

        return frame

    def draw_tactical_info(self, frame: PIL.Image.Image):
        """
        Desenha informações táticas do jogador
        
        Parameters
        ----------
        frame : PIL.Image.Image
            Frame para desenhar
        """
        try:
            if self.detection is None:
                return
                
            x1, y1 = self.detection.points[0]
            
            # Zona tática
            tactical_zone = self.get_tactical_zone()
            frame = Draw.draw_text(
                img=frame,
                origin=(x1, y1 - 40),
                text=tactical_zone,
                color=(255, 255, 0) if self.team else (255, 255, 255)
            )
            
            # Velocidade se disponível
            if self.velocity is not None:
                speed = float(np.linalg.norm(self.velocity))
                frame = Draw.draw_text(
                    img=frame,
                    origin=(x1, y1 - 60),
                    text=f"v: {speed:.1f}",
                    color=(255, 255, 255)
                )
                
        except Exception as e:
            print(f"⚠️ Erro ao desenhar info tática: {e}")

    def draw_pointer(self, frame: PIL.Image.Image) -> PIL.Image.Image:
        """
        Desenha indicador acima do jogador
        
        Parameters
        ----------
        frame : PIL.Image.Image
            Frame para desenhar
            
        Returns
        -------
        PIL.Image.Image
            Frame com indicador
        """
        if self.detection is None:
            return frame

        color = self.team.color if self.team else (255, 255, 255)
        return Draw.draw_pointer(detection=self.detection, img=frame, color=color)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas de performance do jogador
        
        Returns
        -------
        Dict[str, Any]
            Métricas detalhadas
        """
        metrics = {
            'distance_covered': self.distance_covered,
            'position_samples': len(self.position_history),
            'zones_visited': len(set(self.zone_history)) if self.zone_history else 0,
            'current_zone': self.get_tactical_zone(),
            'zone_stability': self.calculate_zone_stability()
        }
        
        # Métricas de velocidade
        if self.velocity is not None:
            speed = float(np.linalg.norm(self.velocity))
            metrics.update({
                'current_speed': speed,
                'velocity_x': float(self.velocity[0]),
                'velocity_y': float(self.velocity[1])
            })
        
        # Métricas de aceleração
        if self.acceleration is not None:
            acc_magnitude = float(np.linalg.norm(self.acceleration))
            metrics.update({
                'current_acceleration': acc_magnitude,
                'acceleration_x': float(self.acceleration[0]),
                'acceleration_y': float(self.acceleration[1])
            })
        
        # Métricas de proximidade à bola
        if self.ball_distances:
            metrics.update({
                'avg_ball_distance': sum(self.ball_distances) / len(self.ball_distances),
                'min_ball_distance': min(self.ball_distances),
                'ball_proximity_samples': len(self.ball_distances)
            })
        
        return metrics

    def __str__(self):
        """Representação textual do jogador"""
        team_str = self.team.name if self.team else "No Team"
        position_str = f"({self.center[0]:.1f}, {self.center[1]:.1f})" if self.center is not None else "N/A"
        zone_str = self.get_tactical_zone()
        
        return f"Player: {team_str}, pos={position_str}, zone={zone_str}"

    def __eq__(self, other: "Player") -> bool:
        """Verifica igualdade entre jogadores baseada no ID"""
        if not isinstance(other, Player):
            return False
            
        try:
            if (self.detection is None or other.detection is None or
                "id" not in self.detection.data or "id" not in other.detection.data):
                return False
                
            return self.detection.data["id"] == other.detection.data["id"]
        except (KeyError, AttributeError):
            return False

    @staticmethod
    def have_same_id(player1: "Player", player2: "Player") -> bool:
        """
        Verifica se dois jogadores têm o mesmo ID
        
        Parameters
        ----------
        player1 : Player
            Primeiro jogador
        player2 : Player
            Segundo jogador
            
        Returns
        -------
        bool
            True se têm o mesmo ID
        """
        if not player1 or not player2:
            return False
            
        return player1 == player2

    @staticmethod
    def get_team_formation_analysis(players: List["Player"], team: Team) -> Dict[str, Any]:
        """
        Análise da formação tática de um time
        
        Parameters
        ----------
        players : List[Player]
            Lista de todos os jogadores
        team : Team
            Time para análise
            
        Returns
        -------
        Dict[str, Any]
            Análise detalhada da formação
        """
        team_players = [p for p in players if p.team == team and p.center is not None]
        
        if len(team_players) < 3:
            return {
                "formation": "insufficient_players",
                "zones": {},
                "player_count": len(team_players)
            }

        # Análise por zonas táticas
        zones = {}
        for player in team_players:
            zone = player.get_tactical_zone()
            zones[zone] = zones.get(zone, 0) + 1

        # Determina formação baseada nas zonas
        defense_count = sum(count for zone, count in zones.items() if "defense" in zone)
        midfield_count = sum(count for zone, count in zones.items() if "midfield" in zone)
        attack_count = sum(count for zone, count in zones.items() if "attack" in zone)

        formation = f"{defense_count}-{midfield_count}-{attack_count}"

        # Métricas avançadas
        compactness = Player.calculate_team_compactness(players, team)
        centroid = Player.get_team_centroid(players, team)
        
        # Análise de conectividade
        connectivity = Player.calculate_team_connectivity(team_players)

        return {
            "formation": formation,
            "zones": zones,
            "defense_players": defense_count,
            "midfield_players": midfield_count,
            "attack_players": attack_count,
            "total_players": len(team_players),
            "compactness": compactness,
            "centroid": centroid.tolist() if centroid is not None else None,
            "connectivity": connectivity,
            "zone_distribution": {
                "left": sum(1 for zone in zones.keys() if "left" in zone),
                "center": sum(1 for zone in zones.keys() if "center" in zone),
                "right": sum(1 for zone in zones.keys() if "right" in zone)
            }
        }

    @staticmethod
    def calculate_team_compactness(players: List["Player"], team: Team) -> float:
        """
        Calcula compactação do time (distância média entre jogadores)
        
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

        try:
            total_distance = 0
            comparisons = 0

            for i, player1 in enumerate(team_players):
                for player2 in team_players[i+1:]:
                    distance = player1.distance_to_player(player2)
                    if distance != float('inf'):
                        total_distance += distance
                        comparisons += 1

            return total_distance / comparisons if comparisons > 0 else 0.0
            
        except (ZeroDivisionError, TypeError):
            return 0.0

    @staticmethod
    def calculate_team_connectivity(team_players: List["Player"]) -> float:
        """
        Calcula conectividade da formação do time
        
        Parameters
        ----------
        team_players : List[Player]
            Jogadores do time
            
        Returns
        -------
        float
            Índice de conectividade (0-1, maior = mais conectado)
        """
        if len(team_players) < 3:
            return 0.0
            
        try:
            connection_threshold = 150  # Distância máxima para considerar "conectado"
            total_possible_connections = len(team_players) * (len(team_players) - 1) / 2
            actual_connections = 0
            
            for i, player1 in enumerate(team_players):
                for player2 in team_players[i+1:]:
                    distance = player1.distance_to_player(player2)
                    if distance <= connection_threshold:
                        actual_connections += 1
            
            return actual_connections / total_possible_connections
            
        except (ZeroDivisionError, TypeError):
            return 0.0

    @staticmethod
    def get_team_centroid(players: List["Player"], team: Team) -> Optional[np.array]:
        """
        Calcula centroide (centro de massa) do time
        
        Parameters
        ----------
        players : List[Player]
            Lista de jogadores
        team : Team
            Time para análise
            
        Returns
        -------
        Optional[np.array]
            Coordenadas do centroide [x, y]
        """
        team_players = [p for p in players if p.team == team and p.center is not None]
        
        if not team_players:
            return None

        try:
            positions = np.array([p.center for p in team_players])
            return np.mean(positions, axis=0)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def draw_players(players: List["Player"], frame: PIL.Image.Image,
                    confidence: bool = False, id: bool = False,
                    show_tactical_info: bool = False) -> PIL.Image.Image:
        """
        REQUISITO OBRIGATÓRIO: Desenha todos os jogadores com cores dos times
        
        Parameters
        ----------
        players : List[Player]
            Lista de jogadores
        frame : PIL.Image.Image
            Frame para desenhar
        confidence : bool, optional
            Mostrar confiança das detecções
        id : bool, optional
            Mostrar IDs dos jogadores
        show_tactical_info : bool, optional
            Mostrar informações táticas
            
        Returns
        -------
        PIL.Image.Image
            Frame com jogadores desenhados
        """
        try:
            for player in players:
                if player is not None:
                    # Atualiza histórico de posição do jogador
                    player.update_position_history()
                    
                    # Desenha o jogador
                    frame = player.draw(
                        frame, 
                        confidence=confidence, 
                        id=id, 
                        show_tactical_info=show_tactical_info
                    )
        except Exception as e:
            print(f"⚠️ Erro ao desenhar jogadores: {e}")

        return frame

    @staticmethod
    def draw_tactical_analysis(players: List["Player"], frame: PIL.Image.Image, 
                             teams: List[Team]) -> PIL.Image.Image:
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
        try:
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
                    f"Conectividade: {formation_analysis.get('connectivity', 0):.2f}",
                ]
                
                if centroid is not None:
                    info_texts.append(f"Centro: ({centroid[0]:.0f}, {centroid[1]:.0f})")
                
                # Desenha informações
                for j, text in enumerate(info_texts):
                    color = team.color if j == 0 else (255, 255, 255)
                    frame = Draw.draw_text(
                        img=frame,
                        origin=(x_pos, y_offset + j * 20),
                        text=text,
                        color=color
                    )
        except Exception as e:
            print(f"⚠️ Erro na análise tática: {e}")
        
        return frame

    @staticmethod
    def generate_team_report(players: List["Player"], team: Team) -> str:
        """
        Gera relatório detalhado do time
        
        Parameters
        ----------
        players : List[Player]
            Lista de jogadores
        team : Team
            Time para análise
            
        Returns
        -------
        str
            Relatório detalhado do time
        """
        analysis = Player.get_team_formation_analysis(players, team)
        team_players = [p for p in players if p.team == team and p.center is not None]
        
        report_lines = [
            f"📊 RELATÓRIO DO TIME: {team.name}",
            "=" * 50,
            "",
            f"⚽ FORMAÇÃO: {analysis['formation']}",
            f"👥 Jogadores detectados: {analysis['total_players']}",
            f"🏃 Distribuição por setor:",
            f"   • Defesa: {analysis['defense_players']} jogadores",
            f"   • Meio: {analysis['midfield_players']} jogadores", 
            f"   • Ataque: {analysis['attack_players']} jogadores",
            "",
            f"📈 MÉTRICAS TÁTICAS:",
            f"   • Compactação: {analysis['compactness']:.1f} pixels",
            f"   • Conectividade: {analysis.get('connectivity', 0)*100:.1f}%",
            f"   • Distribuição lateral:",
            f"     - Esquerda: {analysis['zone_distribution']['left']} zonas",
            f"     - Centro: {analysis['zone_distribution']['center']} zonas",
            f"     - Direita: {analysis['zone_distribution']['right']} zonas",
            ""
        ]
        
        # Adiciona métricas individuais dos jogadores
        if team_players:
            report_lines.extend([
                "👤 ANÁLISE INDIVIDUAL DOS JOGADORES:",
                ""
            ])
            
            for i, player in enumerate(team_players[:5]):  # Primeiros 5 jogadores
                metrics = player.get_performance_metrics()
                player_id = player.detection.data.get("id", f"Player_{i+1}")
                
                report_lines.extend([
                    f"Jogador {player_id}:",
                    f"   • Zona atual: {metrics['current_zone']}",
                    f"   • Distância percorrida: {metrics['distance_covered']:.1f}px",
                    f"   • Estabilidade de zona: {metrics['zone_stability']*100:.1f}%",
                ])
                
                if 'current_speed' in metrics:
                    report_lines.append(f"   • Velocidade atual: {metrics['current_speed']:.1f}px/frame")
                
                report_lines.append("")
        
        return "\n".join(report_lines)

    @staticmethod
    def from_detections(detections: List[Detection], teams: List[Team] = None) -> List["Player"]:
        """
        Cria lista de Player objects a partir de detecções
        
        REQUISITO OBRIGATÓRIO: Associa jogadores aos times com cores diferentes
        
        Parameters
        ----------
        detections : List[Detection]
            Lista de detecções
        teams : List[Team], optional
            Lista de times
            
        Returns
        -------
        List[Player]
            Lista de Player objects
        """
        players = []

        try:
            for detection in detections:
                if detection is None:
                    continue

                # Associa jogador ao time baseado na classificação
                if "classification" in detection.data and teams:
                    team_name = detection.data["classification"]
                    team = Team.from_name(teams=teams, name=team_name)
                    detection.data["team"] = team

                # Cria jogador
                player = Player(detection=detection)
                players.append(player)
                
        except Exception as e:
            print(f"⚠️ Erro ao criar jogadores: {e}")

        return players

    @staticmethod
    def export_players_data(players: List["Player"]) -> Dict[str, Any]:
        """
        Exporta dados dos jogadores para análise externa
        
        Parameters
        ----------
        players : List[Player]
            Lista de jogadores
            
        Returns
        -------
        Dict[str, Any]
            Dados estruturados dos jogadores
        """
        export_data = {
            'total_players': len(players),
            'players_by_team': {},
            'individual_metrics': []
        }
        
        # Agrupa por time
        for player in players:
            if player.team:
                team_name = player.team.name
                if team_name not in export_data['players_by_team']:
                    export_data['players_by_team'][team_name] = []
                
                player_data = {
                    'id': player.detection.data.get("id") if player.detection else None,
                    'position': player.center.tolist() if player.center is not None else None,
                    'tactical_zone': player.get_tactical_zone(),
                    'metrics': player.get_performance_metrics()
                }
                
                export_data['players_by_team'][team_name].append(player_data)
                export_data['individual_metrics'].append(player_data)
        
        return export_data