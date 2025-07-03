from typing import List, Tuple, Optional
import numpy as np
import PIL
from PIL import ImageDraw
from scipy.spatial import ConvexHull
import math

from soccer.player import Player
from soccer.team import Team
from soccer.ball import Ball


class TacticalVisualization:
    """
    Classe responsável pela visualização tática completa conforme requisitos do PDF
    
    REQUISITOS IMPLEMENTADOS:
    - OBRIGATÓRIO: Percepção visual do aspecto tático (organização coletiva) dos dois times
    - DESEJÁVEL: Linhas de ligação entre jogadores do mesmo time
    - DESEJÁVEL: Polígonos entre jogadores do mesmo time
    """
    
    def __init__(self):
        # Configurações de visualização tática
        self.formation_lines_enabled = True
        self.formation_polygons_enabled = True
        self.ball_trail_enabled = True
        
        # Configurações do rastro da bola
        self.ball_trail_points = []
        self.max_trail_length = 30
        
        # Configurações de conectividade
        self.max_connections_per_player = 2  # Para evitar poluição visual
        self.max_connection_distance = 200   # Distância máxima para conexões
        
        # Configurações de transparência
        self.polygon_alpha = 80    # Transparência dos polígonos
        self.line_alpha = 150      # Transparência das linhas
        self.trail_alpha_base = 200 # Alpha base para o rastro
        
    def get_players_by_team(self, players: List[Player], team: Team) -> List[Player]:
        """
        Filtra jogadores por time com validação rigorosa
        
        Parameters
        ----------
        players : List[Player]
            Lista de todos os jogadores
        team : Team
            Time para filtrar
            
        Returns
        -------
        List[Player]
            Jogadores do time especificado com detecções válidas
        """
        valid_players = []
        for player in players:
            if (player.team == team and 
                player.detection is not None and 
                hasattr(player.detection, 'points') and
                player.detection.points is not None):
                valid_players.append(player)
        return valid_players
    
    def get_player_positions(self, players: List[Player]) -> List[Tuple[float, float]]:
        """
        Extrai posições centrais dos jogadores com validação rigorosa
        
        Parameters
        ----------
        players : List[Player]
            Lista de jogadores
            
        Returns
        -------
        List[Tuple[float, float]]
            Posições centrais dos bounding boxes
        """
        positions = []
        for player in players:
            try:
                if player.detection is not None and player.detection.points is not None:
                    x1, y1 = player.detection.points[0]
                    x2, y2 = player.detection.points[1]
                    
                    # Validação das coordenadas
                    if all(isinstance(coord, (int, float)) for coord in [x1, y1, x2, y2]):
                        center_x = (x1 + x2) / 2
                        center_y = (y1 + y2) / 2
                        positions.append((center_x, center_y))
            except (IndexError, TypeError, AttributeError):
                continue  # Pula jogadores com dados inválidos
                
        return positions
    
    def calculate_team_centroid(self, positions: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
        """
        Calcula o centroide da formação do time
        
        Parameters
        ----------
        positions : List[Tuple[float, float]]
            Posições dos jogadores
            
        Returns
        -------
        Optional[Tuple[float, float]]
            Coordenadas do centroide ou None se insuficientes dados
        """
        if len(positions) < 2:
            return None
        
        try:
            x_coords = [pos[0] for pos in positions]
            y_coords = [pos[1] for pos in positions]
            
            centroid_x = sum(x_coords) / len(x_coords)
            centroid_y = sum(y_coords) / len(y_coords)
            
            return (centroid_x, centroid_y)
        except (ZeroDivisionError, TypeError):
            return None
    
    def draw_connection_lines(self, img: PIL.Image.Image, positions: List[Tuple[float, float]], 
                            color: Tuple[int, int, int], alpha: int = None) -> PIL.Image.Image:
        """
        REQUISITO DESEJÁVEL: Desenha linhas de ligação entre jogadores do mesmo time
        
        Implementa conexões inteligentes para mostrar organização coletiva:
        - Cada jogador conecta com os N mais próximos
        - Evita sobrecarga visual limitando conexões
        - Respeita distância máxima para conexões realistas
        
        Parameters
        ----------
        img : PIL.Image.Image
            Imagem para desenhar
        positions : List[Tuple[float, float]]
            Posições dos jogadores
        color : Tuple[int, int, int]
            Cor das linhas
        alpha : int, optional
            Transparência das linhas
            
        Returns
        -------
        PIL.Image.Image
            Imagem com linhas de formação
        """
        if len(positions) < 2:
            return img
            
        if alpha is None:
            alpha = self.line_alpha
            
        try:
            draw = ImageDraw.Draw(img, "RGBA")
            color_with_alpha = color + (alpha,)
            
            # Conecta cada jogador com os mais próximos para mostrar organização
            for i, pos1 in enumerate(positions):
                distances = []
                
                # Calcula distâncias para todos os outros jogadores
                for j, pos2 in enumerate(positions):
                    if i != j:
                        distance = math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
                        if distance <= self.max_connection_distance:  # Filtra por distância máxima
                            distances.append((distance, j))
                
                # Conecta com os N mais próximos
                distances.sort()
                connections_made = 0
                
                for distance, closest_idx in distances:
                    if connections_made >= self.max_connections_per_player:
                        break
                        
                    pos2 = positions[closest_idx]
                    
                    # Desenha linha com espessura baseada na proximidade
                    line_width = max(1, 3 - int(distance / 100))
                    draw.line([pos1, pos2], fill=color_with_alpha, width=line_width)
                    connections_made += 1
            
        except Exception as e:
            print(f"⚠️ Erro ao desenhar linhas de formação: {e}")
            
        return img
    
    def draw_formation_polygon(self, img: PIL.Image.Image, positions: List[Tuple[float, float]], 
                             color: Tuple[int, int, int], alpha: int = None) -> PIL.Image.Image:
        """
        REQUISITO DESEJÁVEL: Desenha polígonos entre jogadores do mesmo time
        
        Implementa visualização da área ocupada pela formação:
        - Usa algoritmo de casco convexo (ConvexHull)
        - Mostra compactação e distribuição espacial
        - Transparência para não interferir com outros elementos
        
        Parameters
        ----------
        img : PIL.Image.Image
            Imagem para desenhar
        positions : List[Tuple[float, float]]
            Posições dos jogadores
        color : Tuple[int, int, int]
            Cor do polígono
        alpha : int, optional
            Transparência do polígono
            
        Returns
        -------
        PIL.Image.Image
            Imagem com polígono de formação
        """
        if len(positions) < 3:
            return img  # Precisa de pelo menos 3 pontos para polígono
            
        if alpha is None:
            alpha = self.polygon_alpha
            
        try:
            # Calcula o casco convexo para definir área da formação
            points = np.array(positions)
            hull = ConvexHull(points)
            hull_points = [tuple(points[vertex]) for vertex in hull.vertices]
            
            draw = ImageDraw.Draw(img, "RGBA")
            
            # Cores para polígono e contorno
            fill_color = color + (alpha,)
            outline_color = color + (alpha * 2,)  # Contorno mais opaco
            
            # Desenha polígono preenchido com contorno
            draw.polygon(hull_points, fill=fill_color, outline=outline_color, width=2)
            
            # Opcionalmente desenha centroide
            centroid = self.calculate_team_centroid(positions)
            if centroid:
                # Pequeno círculo no centroide
                c_x, c_y = centroid
                radius = 3
                draw.ellipse([c_x-radius, c_y-radius, c_x+radius, c_y+radius], 
                           fill=outline_color, outline=color + (255,))
            
        except Exception as e:
            # Fallback para caso o ConvexHull falhe (pontos colineares, etc.)
            print(f"⚠️ Fallback para polígono simples: {e}")
            try:
                # Desenha polígono simples conectando todos os pontos
                draw = ImageDraw.Draw(img, "RGBA")
                draw.polygon(positions, fill=color + (alpha//2,), outline=color + (alpha,))
            except:
                pass  # Se tudo falhar, apenas não desenha o polígono
                
        return img
    
    def update_ball_trail(self, ball: Ball):
        """
        REQUISITO DESEJÁVEL: Atualiza rastro visual da bola
        
        Mantém histórico de posições para mostrar movimento
        
        Parameters
        ----------
        ball : Ball
            Objeto da bola
        """
        if ball is None or ball.detection is None:
            return
            
        try:
            ball_center = ball.center
            if ball_center is not None and len(ball_center) >= 2:
                # Converte para tuple se necessário
                center_tuple = tuple(map(float, ball_center[:2]))
                self.ball_trail_points.append(center_tuple)
                
                # Limita tamanho do rastro para performance
                if len(self.ball_trail_points) > self.max_trail_length:
                    self.ball_trail_points.pop(0)
        except (TypeError, IndexError, AttributeError):
            pass  # Ignora erros de dados inválidos
    
    def draw_ball_trail(self, img: PIL.Image.Image, team_possession_color: Tuple[int, int, int]) -> PIL.Image.Image:
        """
        REQUISITO DESEJÁVEL: Desenha rastro visual da bola
        
        Implementa trail com fade effect para mostrar trajetória:
        - Pontos mais antigos ficam transparentes
        - Espessura varia com a idade do ponto
        - Cor baseada no time com posse de bola
        
        Parameters
        ----------
        img : PIL.Image.Image
            Imagem para desenhar
        team_possession_color : Tuple[int, int, int]
            Cor do time com posse de bola
            
        Returns
        -------
        PIL.Image.Image
            Imagem com rastro da bola
        """
        if len(self.ball_trail_points) < 2:
            return img
            
        try:
            draw = ImageDraw.Draw(img, "RGBA")
            
            # Desenha rastro com fade effect
            for i in range(1, len(self.ball_trail_points)):
                # Alpha baseado na posição no rastro (mais recente = mais opaco)
                alpha_ratio = i / len(self.ball_trail_points)
                alpha = int(self.trail_alpha_base * alpha_ratio)
                color_with_alpha = team_possession_color + (alpha,)
                
                # Espessura baseada na idade (mais recente = mais espesso)
                width = max(1, int(8 * alpha_ratio))
                
                try:
                    start_point = tuple(map(int, self.ball_trail_points[i-1]))
                    end_point = tuple(map(int, self.ball_trail_points[i]))
                    
                    # Valida coordenadas
                    if all(0 <= coord <= 10000 for coord in start_point + end_point):
                        draw.line([start_point, end_point], fill=color_with_alpha, width=width)
                except (ValueError, TypeError):
                    continue  # Pula pontos com coordenadas inválidas
                    
            # Desenha pontos nas posições mais recentes para destaque
            for i, point in enumerate(self.ball_trail_points[-5:]):
                try:
                    alpha = int(255 * ((i + 1) / 5))
                    radius = 2 + i
                    color_with_alpha = team_possession_color + (alpha,)
                    
                    x, y = map(int, point)
                    if 0 <= x <= img.size[0] and 0 <= y <= img.size[1]:
                        draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                                   fill=color_with_alpha, outline=team_possession_color + (255,), width=1)
                except (ValueError, TypeError):
                    continue
                    
        except Exception as e:
            print(f"⚠️ Erro ao desenhar rastro da bola: {e}")
            
        return img
    
    def draw_tactical_analysis(self, img: PIL.Image.Image, players: List[Player], 
                             ball: Ball, teams: List[Team], team_possession: Team) -> PIL.Image.Image:
        """
        REQUISITO OBRIGATÓRIO: Percepção visual do aspecto tático (organização coletiva)
        
        Desenha análise tática completa conforme especificação do PDF:
        - Visualiza organização coletiva dos dois times simultaneamente
        - Implementa todos os requisitos desejáveis quando habilitados
        - Mantém clareza visual e performance
        
        Parameters
        ----------
        img : PIL.Image.Image
            Imagem do frame
        players : List[Player]
            Lista de jogadores detectados
        ball : Ball
            Objeto da bola
        teams : List[Team]
            Lista de times
        team_possession : Team
            Time com posse de bola
            
        Returns
        -------
        PIL.Image.Image
            Imagem com análise tática completa
        """
        try:
            # REQUISITO DESEJÁVEL: Atualiza rastro da bola
            if self.ball_trail_enabled:
                self.update_ball_trail(ball)
                
                # Desenha rastro com cor do time com posse
                if team_possession:
                    img = self.draw_ball_trail(img, team_possession.color)
            
            # REQUISITO OBRIGATÓRIO: Visualização da organização coletiva dos dois times
            for team in teams:
                if team is None:
                    continue
                    
                # Filtra jogadores do time com validação rigorosa
                team_players = self.get_players_by_team(players, team)
                
                if len(team_players) < 2:
                    continue  # Precisa de pelo menos 2 jogadores para análise tática
                    
                # Extrai posições válidas
                positions = self.get_player_positions(team_players)
                
                if len(positions) < 2:
                    continue
                
                # REQUISITO DESEJÁVEL: Polígonos de formação
                if self.formation_polygons_enabled and len(positions) >= 3:
                    img = self.draw_formation_polygon(img, positions, team.color)
                
                # REQUISITO DESEJÁVEL: Linhas de formação
                if self.formation_lines_enabled:
                    img = self.draw_connection_lines(img, positions, team.color)
            
        except Exception as e:
            print(f"⚠️ Erro na análise tática: {e}")
            
        return img
    
    def get_formation_analysis(self, players: List[Player], teams: List[Team]) -> dict:
        """
        Análise detalhada da formação tática para relatórios
        
        Parameters
        ----------
        players : List[Player]
            Lista de jogadores
        teams : List[Team]
            Lista de times
            
        Returns
        -------
        dict
            Análise detalhada das formações
        """
        analysis = {}
        
        for team in teams:
            if team is None:
                continue
                
            team_players = self.get_players_by_team(players, team)
            positions = self.get_player_positions(team_players)
            
            team_analysis = {
                'player_count': len(team_players),
                'positions': positions,
                'centroid': self.calculate_team_centroid(positions),
                'formation_area': 0,
                'compactness': 0
            }
            
            # Calcula área da formação usando ConvexHull
            if len(positions) >= 3:
                try:
                    points = np.array(positions)
                    hull = ConvexHull(points)
                    team_analysis['formation_area'] = hull.volume  # Em 2D, volume = área
                except:
                    team_analysis['formation_area'] = 0
            
            # Calcula compactação (distância média entre jogadores)
            if len(positions) >= 2:
                total_distance = 0
                comparisons = 0
                
                for i, pos1 in enumerate(positions):
                    for pos2 in positions[i+1:]:
                        distance = math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
                        total_distance += distance
                        comparisons += 1
                
                team_analysis['compactness'] = total_distance / comparisons if comparisons > 0 else 0
            
            analysis[team.name] = team_analysis
            
        return analysis
    
    def toggle_formation_lines(self):
        """Liga/desliga linhas de formação"""
        self.formation_lines_enabled = not self.formation_lines_enabled
        print(f"📊 Linhas de formação: {'✅' if self.formation_lines_enabled else '❌'}")
    
    def toggle_formation_polygons(self):
        """Liga/desliga polígonos de formação"""
        self.formation_polygons_enabled = not self.formation_polygons_enabled
        print(f"🔷 Polígonos de formação: {'✅' if self.formation_polygons_enabled else '❌'}")
    
    def toggle_ball_trail(self):
        """Liga/desliga rastro da bola"""
        self.ball_trail_enabled = not self.ball_trail_enabled
        if not self.ball_trail_enabled:
            self.ball_trail_points.clear()
        print(f"🎯 Rastro da bola: {'✅' if self.ball_trail_enabled else '❌'}")
    
    def clear_ball_trail(self):
        """Limpa rastro da bola"""
        self.ball_trail_points.clear()
        
    def set_trail_length(self, length: int):
        """
        Configura comprimento do rastro da bola
        
        Parameters
        ----------
        length : int
            Novo comprimento máximo do rastro
        """
        if length > 0:
            self.max_trail_length = length
            # Ajusta trail atual se necessário
            if len(self.ball_trail_points) > length:
                self.ball_trail_points = self.ball_trail_points[-length:]
    
    def configure_visual_parameters(self, polygon_alpha: int = None, line_alpha: int = None, 
                                  trail_alpha: int = None, max_connections: int = None):
        """
        Configura parâmetros visuais da análise tática
        
        Parameters
        ----------
        polygon_alpha : int, optional
            Transparência dos polígonos (0-255)
        line_alpha : int, optional
            Transparência das linhas (0-255)
        trail_alpha : int, optional
            Transparência base do rastro (0-255)
        max_connections : int, optional
            Máximo de conexões por jogador
        """
        if polygon_alpha is not None:
            self.polygon_alpha = max(0, min(255, polygon_alpha))
        if line_alpha is not None:
            self.line_alpha = max(0, min(255, line_alpha))
        if trail_alpha is not None:
            self.trail_alpha_base = max(0, min(255, trail_alpha))
        if max_connections is not None:
            self.max_connections_per_player = max(1, max_connections)
    
    def get_tactical_summary(self, players: List[Player], teams: List[Team]) -> str:
        """
        Gera resumo textual da análise tática
        
        Parameters
        ----------
        players : List[Player]
            Lista de jogadores
        teams : List[Team]
            Lista de times
            
        Returns
        -------
        str
            Resumo da análise tática
        """
        analysis = self.get_formation_analysis(players, teams)
        
        summary_lines = ["📊 RESUMO TÁTICO:"]
        
        for team_name, data in analysis.items():
            summary_lines.append(f"\n{team_name}:")
            summary_lines.append(f"  • Jogadores detectados: {data['player_count']}")
            summary_lines.append(f"  • Área da formação: {data['formation_area']:.1f} px²")
            summary_lines.append(f"  • Compactação: {data['compactness']:.1f} px")
            
            if data['centroid']:
                summary_lines.append(f"  • Centro da formação: ({data['centroid'][0]:.1f}, {data['centroid'][1]:.1f})")
        
        return "\n".join(summary_lines)