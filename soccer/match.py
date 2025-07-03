from typing import List, Dict, Any, Optional
import cv2
import numpy as np
import PIL
from PIL import ImageDraw, ImageFont

from soccer.ball import Ball
from soccer.draw import Draw
from soccer.pass_event import Pass, PassEvent
from soccer.player import Player
from soccer.team import Team
from soccer.tactical_visualization import TacticalVisualization


class Match:
    """
    Classe principal para gerenciamento da partida com análise tática completa
    
    REQUISITOS IMPLEMENTADOS:
    - OBRIGATÓRIO: Percepção visual do aspecto tático dos dois times
    - OBRIGATÓRIO: Visualização contínua da detecção dos jogadores
    - OBRIGATÓRIO: Times com cores diferentes de marcações
    - DESEJÁVEL: Todos os recursos de visualização tática
    """
    
    def __init__(self, home: Team, away: Team, fps: int = 30):
        """
        Inicializa partida com análise tática aprimorada
        
        Parameters
        ----------
        home : Team
            Time da casa
        away : Team
            Time visitante
        fps : int, optional
            Frames por segundo, by default 30
        """
        # Dados básicos da partida
        self.duration = 0
        self.home = home
        self.away = away
        self.team_possession = self.home
        self.current_team = self.home
        self.possession_counter = 0
        self.closest_player = None
        self.ball = None
        self.fps = fps
        
        # Parâmetros de detecção
        self.possesion_counter_threshold = 20  # Frames para mudança de posse
        self.ball_distance_threshold = 45      # Distância em pixels para posse
        
        # Sistema de passes
        self.pass_event = PassEvent()
        
        # SISTEMA DE VISUALIZAÇÃO TÁTICA COMPLETA
        self.tactical_viz = TacticalVisualization()
        
        # CONFIGURAÇÕES DOS REQUISITOS (podem ser alteradas dinamicamente)
        self.show_formation_lines = True      # REQUISITO DESEJÁVEL
        self.show_formation_polygons = True   # REQUISITO DESEJÁVEL
        self.show_ball_trail = True           # REQUISITO DESEJÁVEL
        self.show_tactical_info = True        # Painel de informações
        
        # Métricas avançadas
        self.frame_stats = []                 # Histórico de estatísticas por frame
        self.tactical_moments = []            # Momentos táticos importantes
        
    def update(self, players: List[Player], ball: Ball):
        """
        REQUISITO OBRIGATÓRIO: Atualiza estado da partida com análise tática contínua
        
        Parameters
        ----------
        players : List[Player]
            Lista de jogadores detectados
        ball : Ball
            Objeto da bola
        """
        # Atualiza contadores básicos
        self.update_possession()
        
        if ball is None or ball.detection is None:
            self.closest_player = None
            return
        
        self.ball = ball
        
        # REQUISITO OBRIGATÓRIO: Processamento contínuo dos jogadores
        valid_players = [p for p in players if p.detection is not None]
        
        if not valid_players:
            self.closest_player = None
            return
        
        # Encontra jogador mais próximo da bola
        closest_player = min(valid_players, key=lambda player: player.distance_to_ball(ball))
        self.closest_player = closest_player
        
        ball_distance = closest_player.distance_to_ball(ball)
        
        # Lógica de posse de bola
        if ball_distance > self.ball_distance_threshold:
            self.closest_player = None
            return
        
        # Gerencia mudança de posse
        if closest_player.team != self.current_team:
            self.possession_counter = 0
            self.current_team = closest_player.team
        
        self.possession_counter += 1
        
        # Confirma mudança de posse após threshold
        if (self.possession_counter >= self.possesion_counter_threshold and 
            closest_player.team is not None):
            self.change_team(self.current_team)
        
        # Detecção de passes
        self.pass_event.update(closest_player=closest_player, ball=ball)
        self.pass_event.process_pass()
        
        # Coleta estatísticas do frame atual
        self.collect_frame_statistics(players)
        
    def change_team(self, team: Team):
        """
        Muda posse de bola para outro time
        
        Parameters
        ----------
        team : Team
            Novo time com posse
        """
        if self.team_possession != team:
            # Registra momento tático de mudança de posse
            self.tactical_moments.append({
                'frame': self.duration,
                'type': 'possession_change',
                'from_team': self.team_possession.name if self.team_possession else 'None',
                'to_team': team.name,
                'time': f"{self.duration//self.fps//60:02d}:{(self.duration//self.fps)%60:02d}"
            })
            
        self.team_possession = team
        
    def update_possession(self):
        """Atualiza duração da partida e contadores de posse"""
        if self.team_possession is None:
            return
        
        self.team_possession.possession += 1
        self.duration += 1
        
    def collect_frame_statistics(self, players: List[Player]):
        """
        Coleta estatísticas do frame atual para análise posterior
        
        Parameters
        ----------
        players : List[Player]
            Lista de jogadores do frame
        """
        try:
            frame_stat = {
                'frame': self.duration,
                'time_seconds': self.duration // self.fps,
                'players_detected': len(players),
                'home_players': len([p for p in players if p.team == self.home]),
                'away_players': len([p for p in players if p.team == self.away]),
                'ball_detected': self.ball is not None and self.ball.detection is not None,
                'team_possession': self.team_possession.name if self.team_possession else None
            }
            
            # Análise tática do frame
            if len(players) >= 4:  # Mínimo para análise tática
                tactical_analysis = self.tactical_viz.get_formation_analysis(players, [self.home, self.away])
                frame_stat['tactical_analysis'] = tactical_analysis
            
            self.frame_stats.append(frame_stat)
            
        except Exception as e:
            print(f"⚠️ Erro ao coletar estatísticas: {e}")
    
    def get_tactical_stats(self) -> Dict[str, Any]:
        """
        REQUISITO: Retorna estatísticas táticas completas da partida
        
        Returns
        -------
        Dict[str, Any]
            Estatísticas detalhadas da partida
        """
        base_stats = {
            'duration': self.duration,
            'duration_formatted': f"{self.duration//self.fps//60:02d}:{(self.duration//self.fps)%60:02d}",
            'home_possession': self.home.possession,
            'away_possession': self.away.possession,
            'home_passes': len(self.home.passes),
            'away_passes': len(self.away.passes),
            'total_passes': len(self.passes),
            'possession_ratio': {
                'home': self.home.get_percentage_possession(self.duration),
                'away': self.away.get_percentage_possession(self.duration)
            },
            'tactical_moments_count': len(self.tactical_moments),
            'frames_analyzed': len(self.frame_stats)
        }
        
        # Estatísticas avançadas se houver dados suficientes
        if len(self.frame_stats) > 10:
            ball_detection_rate = sum(1 for fs in self.frame_stats if fs['ball_detected']) / len(self.frame_stats)
            avg_players_detected = sum(fs['players_detected'] for fs in self.frame_stats) / len(self.frame_stats)
            
            base_stats.update({
                'ball_detection_rate': ball_detection_rate,
                'avg_players_detected': avg_players_detected,
                'possession_changes': len([tm for tm in self.tactical_moments if tm['type'] == 'possession_change'])
            })
        
        return base_stats
    
    def draw_tactical_visualization(self, frame: PIL.Image.Image, players: List[Player]) -> PIL.Image.Image:
        """
        REQUISITO OBRIGATÓRIO: Desenha visualização tática completa
        
        Implementa percepção visual do aspecto tático (organização coletiva) dos dois times
        
        Parameters
        ----------
        frame : PIL.Image.Image
            Frame do vídeo
        players : List[Player]
            Lista de jogadores detectados
            
        Returns
        -------
        PIL.Image.Image
            Frame com visualização tática completa
        """
        try:
            teams = [self.home, self.away]
            
            # Configura parâmetros da visualização tática
            self.tactical_viz.formation_lines_enabled = self.show_formation_lines
            self.tactical_viz.formation_polygons_enabled = self.show_formation_polygons
            self.tactical_viz.ball_trail_enabled = self.show_ball_trail
            
            # REQUISITO OBRIGATÓRIO: Aplica análise tática completa
            frame = self.tactical_viz.draw_tactical_analysis(
                img=frame,
                players=players,
                ball=self.ball,
                teams=teams,
                team_possession=self.team_possession
            )
            
        except Exception as e:
            print(f"⚠️ Erro na visualização tática: {e}")
            
        return frame
    
    def draw_enhanced_info_panel(self, frame: PIL.Image.Image) -> PIL.Image.Image:
        """
        Desenha painel de informações táticas aprimorado
        
        Parameters
        ----------
        frame : PIL.Image.Image
            Frame do vídeo
            
        Returns
        -------
        PIL.Image.Image
            Frame com painel de informações
        """
        if not self.show_tactical_info:
            return frame
            
        try:
            # Configuração do painel
            panel_width = 400
            panel_height = 280
            panel_x = frame.size[0] - panel_width - 20
            panel_y = frame.size[1] - panel_height - 20
            
            # Background do painel com bordas arredondadas
            draw = ImageDraw.Draw(frame, "RGBA")
            panel_bg = (0, 0, 0, 200)
            border_color = (255, 255, 255, 180)
            
            # Desenha painel com bordas arredondadas
            draw.rounded_rectangle(
                [panel_x, panel_y, panel_x + panel_width, panel_y + panel_height],
                radius=15,
                fill=panel_bg,
                outline=border_color,
                width=2
            )
            
            # Título do painel
            title_y = panel_y + 15
            frame = Draw.draw_text(
                img=frame,
                origin=(panel_x + 20, title_y),
                text="📊 ANÁLISE TÁTICA EM TEMPO REAL",
                color=(255, 255, 0)
            )
            
            # Linha separadora
            line_y = title_y + 25
            draw.line([panel_x + 20, line_y, panel_x + panel_width - 20, line_y], 
                     fill=(255, 255, 255, 150), width=1)
            
            # Informações táticas
            stats = self.get_tactical_stats()
            
            info_texts = [
                f"⏱️  Duração: {stats['duration_formatted']}",
                f"⚽ Posse {self.home.abbreviation}: {stats['possession_ratio']['home']*100:.1f}%",
                f"🔄 Posse {self.away.abbreviation}: {stats['possession_ratio']['away']*100:.1f}%",
                f"🏃 Passes {self.home.abbreviation}: {stats['home_passes']}",
                f"📈 Passes {self.away.abbreviation}: {stats['away_passes']}",
                f"🎯 Time na posse: {self.team_possession.name if self.team_possession else 'N/A'}",
                "",  # Linha vazia
                f"🔧 Recursos ativos:",
                f"   📊 Linhas: {'✅' if self.show_formation_lines else '❌'}",
                f"   🔷 Polígonos: {'✅' if self.show_formation_polygons else '❌'}",
                f"   🎯 Rastro: {'✅' if self.show_ball_trail else '❌'}"
            ]
            
            # Desenha informações
            text_start_y = line_y + 15
            line_height = 18
            
            for i, text in enumerate(info_texts):
                if text.strip():  # Não desenha linhas vazias
                    text_color = (255, 255, 255)
                    
                    # Destaca time com posse
                    if "Time na posse" in text and self.team_possession:
                        text_color = self.team_possession.color
                    
                    frame = Draw.draw_text(
                        img=frame,
                        origin=(panel_x + 20, text_start_y + i * line_height),
                        text=text,
                        color=text_color
                    )
            
            # Barra de progresso da posse de bola
            bar_y = panel_y + panel_height - 40
            bar_width = panel_width - 40
            bar_height = 20
            bar_x = panel_x + 20
            
            # Background da barra
            draw.rounded_rectangle(
                [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                radius=10,
                fill=(50, 50, 50, 200),
                outline=(255, 255, 255, 100),
                width=1
            )
            
            # Barra de posse
            if self.duration > 0:
                home_ratio = stats['possession_ratio']['home']
                home_width = int(bar_width * home_ratio)
                
                # Parte do time da casa
                if home_width > 0:
                    draw.rounded_rectangle(
                        [bar_x, bar_y, bar_x + home_width, bar_y + bar_height],
                        radius=10,
                        fill=self.home.color + (180,)
                    )
                
                # Parte do time visitante
                away_width = bar_width - home_width
                if away_width > 0:
                    draw.rounded_rectangle(
                        [bar_x + home_width, bar_y, bar_x + bar_width, bar_y + bar_height],
                        radius=10,
                        fill=self.away.color + (180,)
                    )
            
        except Exception as e:
            print(f"⚠️ Erro ao desenhar painel: {e}")
            
        return frame

    def possession_bar(self, frame: PIL.Image.Image, origin: tuple) -> PIL.Image.Image:
        """
        REQUISITO: Desenha barra de posse de bola com cores dos times
        
        Parameters
        ----------
        frame : PIL.Image.Image
            Frame
        origin : tuple
            Origem (x, y)
            
        Returns
        -------
        PIL.Image.Image
            Frame com barra de posse
        """
        bar_x = origin[0]
        bar_y = origin[1]
        bar_height = 29
        bar_width = 310
        
        ratio = self.home.get_percentage_possession(self.duration)
        
        # Proteção contra retângulos muito pequenos
        if ratio < 0.07:
            ratio = 0.07
        if ratio > 0.93:
            ratio = 0.93
        
        left_rectangle = (
            origin,
            [int(bar_x + ratio * bar_width), int(bar_y + bar_height)],
        )
        
        right_rectangle = (
            [int(bar_x + ratio * bar_width), bar_y],
            [int(bar_x + bar_width), int(bar_y + bar_height)],
        )
        
        left_color = self.home.board_color
        right_color = self.away.board_color
        
        frame = self.draw_counter_rectangle(
            frame=frame,
            ratio=ratio,
            left_rectangle=left_rectangle,
            left_color=left_color,
            right_rectangle=right_rectangle,
            right_color=right_color,
        )
        
        # Textos com percentuais
        if ratio > 0.15:
            home_text = f"{int(self.home.get_percentage_possession(self.duration) * 100)}%"
            frame = Draw.text_in_middle_rectangle(
                img=frame,
                origin=left_rectangle[0],
                width=left_rectangle[1][0] - left_rectangle[0][0],
                height=left_rectangle[1][1] - left_rectangle[0][1],
                text=home_text,
                color=self.home.text_color,
            )
        
        if ratio < 0.85:
            away_text = f"{int(self.away.get_percentage_possession(self.duration) * 100)}%"
            frame = Draw.text_in_middle_rectangle(
                img=frame,
                origin=right_rectangle[0],
                width=right_rectangle[1][0] - right_rectangle[0][0],
                height=right_rectangle[1][1] - right_rectangle[0][1],
                text=away_text,
                color=self.away.text_color,
            )
        
        return frame

    def draw_counter_rectangle(self, frame: PIL.Image.Image, ratio: float,
                             left_rectangle: tuple, left_color: tuple,
                             right_rectangle: tuple, right_color: tuple) -> PIL.Image.Image:
        """Desenha retângulos dos contadores com cores dos times"""
        
        if ratio < 0.15:
            left_rectangle[1][0] += 20
            frame = Draw.half_rounded_rectangle(
                frame, rectangle=left_rectangle, color=left_color, radius=15,
            )
            frame = Draw.half_rounded_rectangle(
                frame, rectangle=right_rectangle, color=right_color, left=True, radius=15,
            )
        else:
            right_rectangle[0][0] -= 20
            frame = Draw.half_rounded_rectangle(
                frame, rectangle=right_rectangle, color=right_color, left=True, radius=15,
            )
            frame = Draw.half_rounded_rectangle(
                frame, rectangle=left_rectangle, color=left_color, radius=15,
            )
        
        return frame

    def passes_bar(self, frame: PIL.Image.Image, origin: tuple) -> PIL.Image.Image:
        """Desenha barra de passes"""
        bar_x = origin[0]
        bar_y = origin[1]
        bar_height = 29
        bar_width = 310
        
        home_passes = len(self.home.passes)
        away_passes = len(self.away.passes)
        total_passes = home_passes + away_passes
        
        if total_passes == 0:
            ratio = 0.5
        else:
            ratio = home_passes / total_passes
        
        # Proteção contra retângulos muito pequenos
        if ratio < 0.07:
            ratio = 0.07
        if ratio > 0.93:
            ratio = 0.93
        
        left_rectangle = (
            origin,
            [int(bar_x + ratio * bar_width), int(bar_y + bar_height)],
        )
        
        right_rectangle = (
            [int(bar_x + ratio * bar_width), bar_y],
            [int(bar_x + bar_width), int(bar_y + bar_height)],
        )
        
        left_color = self.home.board_color
        right_color = self.away.board_color
        
        frame = self.draw_counter_rectangle(
            frame=frame,
            ratio=ratio,
            left_rectangle=left_rectangle,
            left_color=left_color,
            right_rectangle=right_rectangle,
            right_color=right_color,
        )
        
        # Textos com números de passes
        if ratio > 0.15:
            home_text = str(home_passes)
            frame = Draw.text_in_middle_rectangle(
                img=frame,
                origin=left_rectangle[0],
                width=left_rectangle[1][0] - left_rectangle[0][0],
                height=left_rectangle[1][1] - left_rectangle[0][1],
                text=home_text,
                color=self.home.text_color,
            )
        
        if ratio < 0.85:
            away_text = str(away_passes)
            frame = Draw.text_in_middle_rectangle(
                img=frame,
                origin=right_rectangle[0],
                width=right_rectangle[1][0] - right_rectangle[0][0],
                height=right_rectangle[1][1] - right_rectangle[0][1],
                text=away_text,
                color=self.away.text_color,
            )
        
        return frame

    @property
    def home_possession_str(self) -> str:
        return f"{self.home.abbreviation}: {self.home.get_time_possession(self.fps)}"

    @property
    def away_possession_str(self) -> str:
        return f"{self.away.abbreviation}: {self.away.get_time_possession(self.fps)}"

    @property
    def time_possessions(self) -> str:
        return f"{self.home.name}: {self.home.get_time_possession(self.fps)} | {self.away.name}: {self.away.get_time_possession(self.fps)}"

    @property
    def passes(self) -> List[Pass]:
        return self.home.passes + self.away.passes

    def get_possession_background(self) -> PIL.Image.Image:
        """Carrega background do contador de posse"""
        try:
            counter = PIL.Image.open("./images/possession_board.png").convert("RGBA")
            counter = Draw.add_alpha(counter, 210)
            counter = np.array(counter)
            red, green, blue, alpha = counter.T
            counter = np.array([blue, green, red, alpha])
            counter = counter.transpose()
            counter = PIL.Image.fromarray(counter)
            counter = counter.resize((int(315 * 1.2), int(210 * 1.2)))
            return counter
        except FileNotFoundError:
            # Cria background padrão se arquivo não existir
            return self.create_default_background(315 * 1.2, 210 * 1.2)

    def get_passes_background(self) -> PIL.Image.Image:
        """Carrega background do contador de passes"""
        try:
            counter = PIL.Image.open("./images/passes_board.png").convert("RGBA")
            counter = Draw.add_alpha(counter, 210)
            counter = np.array(counter)
            red, green, blue, alpha = counter.T
            counter = np.array([blue, green, red, alpha])
            counter = counter.transpose()
            counter = PIL.Image.fromarray(counter)
            counter = counter.resize((int(315 * 1.2), int(210 * 1.2)))
            return counter
        except FileNotFoundError:
            # Cria background padrão se arquivo não existir
            return self.create_default_background(315 * 1.2, 210 * 1.2)

    def create_default_background(self, width: int, height: int) -> PIL.Image.Image:
        """
        Cria background padrão quando imagens não estão disponíveis
        
        Parameters
        ----------
        width : int
            Largura do background
        height : int
            Altura do background
            
        Returns
        -------
        PIL.Image.Image
            Background padrão
        """
        # Cria imagem com fundo semi-transparente
        background = PIL.Image.new("RGBA", (int(width), int(height)), (0, 0, 0, 180))
        draw = ImageDraw.Draw(background)
        
        # Adiciona borda
        draw.rounded_rectangle(
            [5, 5, width-5, height-5],
            radius=15,
            outline=(255, 255, 255, 150),
            width=2
        )
        
        return background

    def draw_counter_background(self, frame: PIL.Image.Image, origin: tuple, 
                              counter_background: PIL.Image.Image) -> PIL.Image.Image:
        """Desenha background do contador"""
        frame.paste(counter_background, origin, counter_background)
        return frame

    def draw_counter(self, frame: PIL.Image.Image, text: str, counter_text: str,
                    origin: tuple, color: tuple, text_color: tuple,
                    height: int = 27, width: int = 120) -> PIL.Image.Image:
        """
        Desenha contador individual com cores do time
        
        Parameters
        ----------
        frame : PIL.Image.Image
            Frame para desenhar
        text : str
            Texto do time (sigla)
        counter_text : str
            Texto do contador
        origin : tuple
            Posição de origem
        color : tuple
            Cor do time
        text_color : tuple
            Cor do texto
        height : int, optional
            Altura do contador
        width : int, optional
            Largura do contador
            
        Returns
        -------
        PIL.Image.Image
            Frame com contador desenhado
        """
        team_begin = origin
        team_width_ratio = 0.417
        team_width = width * team_width_ratio

        team_rectangle = (
            team_begin,
            (team_begin[0] + team_width, team_begin[1] + height),
        )

        time_begin = (origin[0] + team_width, origin[1])
        time_width = width * (1 - team_width_ratio)

        time_rectangle = (
            time_begin,
            (time_begin[0] + time_width, time_begin[1] + height),
        )

        frame = Draw.half_rounded_rectangle(
            img=frame, rectangle=team_rectangle, color=color, radius=20,
        )

        frame = Draw.half_rounded_rectangle(
            img=frame, rectangle=time_rectangle, color=(239, 234, 229), radius=20, left=True,
        )

        frame = Draw.text_in_middle_rectangle(
            img=frame, origin=team_rectangle[0], height=height, width=team_width,
            text=text, color=text_color,
        )

        frame = Draw.text_in_middle_rectangle(
            img=frame, origin=time_rectangle[0], height=height, width=time_width,
            text=counter_text, color="black",
        )

        return frame

    def draw_debug(self, frame: PIL.Image.Image) -> PIL.Image.Image:
        """Desenha informações de debug (linha jogador-bola)"""
        if self.closest_player and self.ball:
            closest_foot = self.closest_player.closest_foot_to_ball(self.ball)

            color = (0, 255, 0)  # Verde para dentro do threshold
            distance = self.closest_player.distance_to_ball(self.ball)
            
            if distance > self.ball_distance_threshold:
                color = (255, 0, 0)  # Vermelho para fora do threshold

            draw = ImageDraw.Draw(frame, "RGBA")
            draw.line(
                [tuple(closest_foot), tuple(self.ball.center)],
                fill=color + (150,),
                width=3,
            )
            
            # Mostra distância
            mid_point = (
                (closest_foot[0] + self.ball.center[0]) / 2,
                (closest_foot[1] + self.ball.center[1]) / 2
            )
            
            frame = Draw.draw_text(
                img=frame,
                origin=(int(mid_point[0]), int(mid_point[1])),
                text=f"{distance:.1f}px",
                color=(255, 255, 255)
            )

        return frame

    def draw_possession_counter(self, frame: PIL.Image.Image, 
                              counter_background: PIL.Image.Image,
                              debug: bool = False) -> PIL.Image.Image:
        """
        REQUISITO OBRIGATÓRIO: Desenha elementos de posse com cores diferentes dos times
        
        Parameters
        ----------
        frame : PIL.Image.Image
            Frame
        counter_background : PIL.Image.Image
            Background do contador
        debug : bool, optional
            Modo debug, by default False
            
        Returns
        -------
        PIL.Image.Image
            Frame com elementos da partida
        """
        frame_width = frame.size[0]
        counter_origin = (frame_width - 540, 40)

        frame = self.draw_counter_background(
            frame, origin=counter_origin, counter_background=counter_background,
        )

        # Contadores dos times com suas cores específicas
        frame = self.draw_counter(
            frame,
            origin=(counter_origin[0] + 35, counter_origin[1] + 130),
            text=self.home.abbreviation,
            counter_text=self.home.get_time_possession(self.fps),
            color=self.home.board_color,  # REQUISITO: Cor específica do time
            text_color=self.home.text_color,
            height=31,
            width=150,
        )
        
        frame = self.draw_counter(
            frame,
            origin=(counter_origin[0] + 35 + 150 + 10, counter_origin[1] + 130),
            text=self.away.abbreviation,
            counter_text=self.away.get_time_possession(self.fps),
            color=self.away.board_color,  # REQUISITO: Cor específica do time
            text_color=self.away.text_color,
            height=31,
            width=150,
        )
        
        # Barra de posse proporcional
        frame = self.possession_bar(
            frame, origin=(counter_origin[0] + 35, counter_origin[1] + 195)
        )

        # Indicador do jogador mais próximo da bola
        if self.closest_player:
            frame = self.closest_player.draw_pointer(frame)

        # Informações de debug
        if debug:
            frame = self.draw_debug(frame=frame)

        return frame

    def draw_passes_counter(self, frame: PIL.Image.Image,
                          counter_background: PIL.Image.Image,
                          debug: bool = False) -> PIL.Image.Image:
        """
        Desenha contador de passes com cores dos times
        
        Parameters
        ----------
        frame : PIL.Image.Image
            Frame
        counter_background : PIL.Image.Image
            Background do contador
        debug : bool, optional
            Modo debug, by default False
            
        Returns
        -------
        PIL.Image.Image
            Frame com contador de passes
        """
        frame_width = frame.size[0]
        counter_origin = (frame_width - 540, 40)

        frame = self.draw_counter_background(
            frame, origin=counter_origin, counter_background=counter_background,
        )

        frame = self.draw_counter(
            frame,
            origin=(counter_origin[0] + 35, counter_origin[1] + 130),
            text=self.home.abbreviation,
            counter_text=str(len(self.home.passes)),
            color=self.home.board_color,
            text_color=self.home.text_color,
            height=31,
            width=150,
        )
        
        frame = self.draw_counter(
            frame,
            origin=(counter_origin[0] + 35 + 150 + 10, counter_origin[1] + 130),
            text=self.away.abbreviation,
            counter_text=str(len(self.away.passes)),
            color=self.away.board_color,
            text_color=self.away.text_color,
            height=31,
            width=150,
        )
        
        frame = self.passes_bar(
            frame, origin=(counter_origin[0] + 35, counter_origin[1] + 195)
        )

        if self.closest_player:
            frame = self.closest_player.draw_pointer(frame)

        if debug:
            frame = self.draw_debug(frame=frame)

        return frame

    # MÉTODOS DE CONTROLE DOS RECURSOS TÁTICOS
    
    def toggle_formation_lines(self):
        """Liga/desliga linhas de formação"""
        self.show_formation_lines = not self.show_formation_lines
        self.tactical_viz.formation_lines_enabled = self.show_formation_lines
        print(f"📊 Linhas de formação: {'✅' if self.show_formation_lines else '❌'}")

    def toggle_formation_polygons(self):
        """Liga/desliga polígonos de formação"""
        self.show_formation_polygons = not self.show_formation_polygons
        self.tactical_viz.formation_polygons_enabled = self.show_formation_polygons
        print(f"🔷 Polígonos de formação: {'✅' if self.show_formation_polygons else '❌'}")

    def toggle_ball_trail(self):
        """Liga/desliga rastro da bola"""
        self.show_ball_trail = not self.show_ball_trail
        self.tactical_viz.ball_trail_enabled = self.show_ball_trail
        if self.ball:
            self.ball.trail_enabled = self.show_ball_trail
        print(f"🎯 Rastro da bola: {'✅' if self.show_ball_trail else '❌'}")

    def toggle_tactical_info(self):
        """Liga/desliga painel de informações táticas"""
        self.show_tactical_info = not self.show_tactical_info
        print(f"📊 Painel tático: {'✅' if self.show_tactical_info else '❌'}")

    # MÉTODOS DE RELATÓRIO E ANÁLISE
    
    def generate_match_report(self) -> str:
        """
        Gera relatório completo da partida
        
        Returns
        -------
        str
            Relatório detalhado da partida
        """
        stats = self.get_tactical_stats()
        
        report_lines = [
            "=" * 60,
            "📊 RELATÓRIO FINAL DA PARTIDA",
            "=" * 60,
            "",
            f"🏟️  Partida: {self.home.name} vs {self.away.name}",
            f"⏱️  Duração: {stats['duration_formatted']}",
            f"📹 Frames analisados: {stats['frames_analyzed']}",
            "",
            "⚽ ANÁLISE DE POSSE DE BOLA:",
            f"   • {self.home.name}: {stats['possession_ratio']['home']*100:.1f}% ({self.home.get_time_possession(self.fps)})",
            f"   • {self.away.name}: {stats['possession_ratio']['away']*100:.1f}% ({self.away.get_time_possession(self.fps)})",
            "",
            "🏃 ANÁLISE DE PASSES:",
            f"   • Total de passes: {stats['total_passes']}",
            f"   • {self.home.name}: {stats['home_passes']} passes",
            f"   • {self.away.name}: {stats['away_passes']} passes",
            ""
        ]
        
        # Adiciona estatísticas avançadas se disponíveis
        if 'ball_detection_rate' in stats:
            report_lines.extend([
                "📈 ESTATÍSTICAS AVANÇADAS:",
                f"   • Taxa de detecção da bola: {stats['ball_detection_rate']*100:.1f}%",
                f"   • Média de jogadores detectados: {stats['avg_players_detected']:.1f}",
                f"   • Mudanças de posse: {stats.get('possession_changes', 0)}",
                ""
            ])
        
        # Adiciona momentos táticos importantes
        if self.tactical_moments:
            report_lines.extend([
                "⚡ MOMENTOS TÁTICOS IMPORTANTES:",
            ])
            
            for moment in self.tactical_moments[-5:]:  # Últimos 5 momentos
                if moment['type'] == 'possession_change':
                    report_lines.append(
                        f"   • {moment['time']}: Posse {moment['from_team']} → {moment['to_team']}"
                    )
            report_lines.append("")
        
        # Status dos recursos implementados
        report_lines.extend([
            "✅ RECURSOS IMPLEMENTADOS:",
            "   📊 REQUISITOS OBRIGATÓRIOS (DEVE):",
            "      ✅ Percepção visual do aspecto tático",
            "      ✅ Visualização contínua da detecção",
            "      ✅ Times com cores diferentes",
            "",
            "   🎯 REQUISITOS DESEJÁVEIS:",
            f"      {'✅' if self.show_ball_trail else '❌'} Rastreio visual da bola",
            f"      {'✅' if self.show_formation_lines else '❌'} Linhas entre jogadores",
            f"      {'✅' if self.show_formation_polygons else '❌'} Polígonos de formação",
            "",
            "=" * 60
        ])
        
        return "\n".join(report_lines)

    def export_tactical_data(self) -> Dict[str, Any]:
        """
        Exporta dados táticos para análise externa
        
        Returns
        -------
        Dict[str, Any]
            Dados táticos estruturados
        """
        return {
            'match_info': {
                'home_team': self.home.name,
                'away_team': self.away.name,
                'duration_frames': self.duration,
                'duration_seconds': self.duration // self.fps,
                'fps': self.fps
            },
            'final_stats': self.get_tactical_stats(),
            'frame_by_frame': self.frame_stats,
            'tactical_moments': self.tactical_moments,
            'team_data': {
                'home': {
                    'name': self.home.name,
                    'color': self.home.color,
                    'possession_frames': self.home.possession,
                    'passes': len(self.home.passes)
                },
                'away': {
                    'name': self.away.name,
                    'color': self.away.color,
                    'possession_frames': self.away.possession,
                    'passes': len(self.away.passes)
                }
            }
        }

    def __str__(self) -> str:
        return f"{self.home_possession_str} | {self.away_possession_str}"