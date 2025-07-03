from typing import List

import cv2
import numpy as np
import PIL

from soccer.ball import Ball
from soccer.draw import Draw
from soccer.pass_event import Pass, PassEvent
from soccer.player import Player
from soccer.team import Team
from soccer.tactical_visualization import TacticalVisualization


class Match:
    def __init__(self, home: Team, away: Team, fps: int = 30):
        """
        Initialize Match with enhanced tactical analysis

        Parameters
        ----------
        home : Team
            Home team
        away : Team
            Away team
        fps : int, optional
            Fps, by default 30
        """
        self.duration = 0
        self.home = home
        self.away = away
        self.team_possession = self.home
        self.current_team = self.home
        self.possession_counter = 0
        self.closest_player = None
        self.ball = None
        # Amount of consecutive frames new team has to have the ball in order to change possession
        self.possesion_counter_threshold = 20
        # Distance in pixels from player to ball in order to consider a player has the ball
        self.ball_distance_threshold = 45
        self.fps = fps
        # Pass detection
        self.pass_event = PassEvent()
        
        # Tactical visualization
        self.tactical_viz = TacticalVisualization()
        
        # Configurações de visualização tática
        self.show_formation_lines = True
        self.show_formation_polygons = True
        self.show_ball_trail = True
        self.show_tactical_info = True

    def update(self, players: List[Player], ball: Ball):
        """
        Update match possession and closest player with enhanced tactical analysis

        Parameters
        ----------
        players : List[Player]
            List of players
        ball : Ball
            Ball
        """
        self.update_possession()

        if ball is None or ball.detection is None:
            self.closest_player = None
            return

        self.ball = ball

        # Filtra jogadores válidos (com detecção)
        valid_players = [p for p in players if p.detection is not None]
        
        if not valid_players:
            self.closest_player = None
            return

        closest_player = min(valid_players, key=lambda player: player.distance_to_ball(ball))
        self.closest_player = closest_player

        ball_distance = closest_player.distance_to_ball(ball)

        if ball_distance > self.ball_distance_threshold:
            self.closest_player = None
            return

        # Reset counter if team changed
        if closest_player.team != self.current_team:
            self.possession_counter = 0
            self.current_team = closest_player.team

        self.possession_counter += 1

        if (
            self.possession_counter >= self.possesion_counter_threshold
            and closest_player.team is not None
        ):
            self.change_team(self.current_team)

        # Pass detection
        self.pass_event.update(closest_player=closest_player, ball=ball)
        self.pass_event.process_pass()

    def change_team(self, team: Team):
        """
        Change team possession

        Parameters
        ----------
        team : Team, optional
            New team in possession
        """
        self.team_possession = team

    def update_possession(self):
        """
        Updates match duration and possession counter of team in possession
        """
        if self.team_possession is None:
            return

        self.team_possession.possession += 1
        self.duration += 1

    def get_tactical_stats(self) -> dict:
        """
        Retorna estatísticas táticas do jogo
        
        Returns
        -------
        dict
            Dicionário com estatísticas táticas
        """
        stats = {
            'duration': self.duration,
            'home_possession': self.home.possession,
            'away_possession': self.away.possession,
            'home_passes': len(self.home.passes),
            'away_passes': len(self.away.passes),
            'total_passes': len(self.passes),
            'possession_ratio': {
                'home': self.home.get_percentage_possession(self.duration),
                'away': self.away.get_percentage_possession(self.duration)
            }
        }
        return stats

    @property
    def home_possession_str(self) -> str:
        return f"{self.home.abbreviation}: {self.home.get_time_possession(self.fps)}"

    @property
    def away_possession_str(self) -> str:
        return f"{self.away.abbreviation}: {self.away.get_time_possession(self.fps)}"

    def __str__(self) -> str:
        return f"{self.home_possession_str} | {self.away_possession_str}"

    @property
    def time_possessions(self) -> str:
        return f"{self.home.name}: {self.home.get_time_possession(self.fps)} | {self.away.name}: {self.away.get_time_possession(self.fps)}"

    @property
    def passes(self) -> List["Pass"]:
        home_passes = self.home.passes
        away_passes = self.away.passes
        return home_passes + away_passes

    def draw_tactical_visualization(self, frame: PIL.Image.Image, players: List[Player]) -> PIL.Image.Image:
        """
        Desenha visualização tática completa
        
        Parameters
        ----------
        frame : PIL.Image.Image
            Frame do vídeo
        players : List[Player]
            Lista de jogadores
            
        Returns
        -------
        PIL.Image.Image
            Frame com visualização tática
        """
        teams = [self.home, self.away]
        
        # Aplica visualização tática usando a classe especializada
        frame = self.tactical_viz.draw_tactical_analysis(
            img=frame,
            players=players,
            ball=self.ball,
            teams=teams,
            team_possession=self.team_possession
        )
        
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
            
        # Painel de informações táticas
        panel_width = 300
        panel_height = 200
        panel_x = frame.size[0] - panel_width - 20
        panel_y = frame.size[1] - panel_height - 20
        
        # Background do painel
        draw = PIL.ImageDraw.Draw(frame, "RGBA")
        panel_bg = (0, 0, 0, 180)
        draw.rectangle([panel_x, panel_y, panel_x + panel_width, panel_y + panel_height], 
                      fill=panel_bg, outline=(255, 255, 255, 200), width=2)
        
        # Informações táticas
        stats = self.get_tactical_stats()
        
        info_texts = [
            f"Duração: {stats['duration']//self.fps//60:02d}:{(stats['duration']//self.fps)%60:02d}",
            f"Posse {self.home.abbreviation}: {stats['possession_ratio']['home']*100:.1f}%",
            f"Posse {self.away.abbreviation}: {stats['possession_ratio']['away']*100:.1f}%",
            f"Passes {self.home.abbreviation}: {stats['home_passes']}",
            f"Passes {self.away.abbreviation}: {stats['away_passes']}",
            f"Time na posse: {self.team_possession.name if self.team_possession else 'N/A'}",
        ]
        
        # Desenha textos
        y_offset = 15
        for i, text in enumerate(info_texts):
            frame = Draw.draw_text(
                img=frame,
                origin=(panel_x + 10, panel_y + 10 + i * y_offset),
                text=text,
                color=(255, 255, 255)
            )
        
        return frame

    def possession_bar(self, frame: PIL.Image.Image, origin: tuple) -> PIL.Image.Image:
        """
        Draw possession bar

        Parameters
        ----------
        frame : PIL.Image.Image
            Frame
        origin : tuple
            Origin (x, y)

        Returns
        -------
        PIL.Image.Image
            Frame with possession bar
        """
        bar_x = origin[0]
        bar_y = origin[1]
        bar_height = 29
        bar_width = 310

        ratio = self.home.get_percentage_possession(self.duration)

        # Protect against too small rectangles
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

        # Draw home text
        if ratio > 0.15:
            home_text = (
                f"{int(self.home.get_percentage_possession(self.duration) * 100)}%"
            )

            frame = Draw.text_in_middle_rectangle(
                img=frame,
                origin=left_rectangle[0],
                width=left_rectangle[1][0] - left_rectangle[0][0],
                height=left_rectangle[1][1] - left_rectangle[0][1],
                text=home_text,
                color=self.home.text_color,
            )

        # Draw away text
        if ratio < 0.85:
            away_text = (
                f"{int(self.away.get_percentage_possession(self.duration) * 100)}%"
            )

            frame = Draw.text_in_middle_rectangle(
                img=frame,
                origin=right_rectangle[0],
                width=right_rectangle[1][0] - right_rectangle[0][0],
                height=right_rectangle[1][1] - right_rectangle[0][1],
                text=away_text,
                color=self.away.text_color,
            )

        return frame

    def draw_counter_rectangle(
        self,
        frame: PIL.Image.Image,
        ratio: float,
        left_rectangle: tuple,
        left_color: tuple,
        right_rectangle: tuple,
        right_color: tuple,
    ) -> PIL.Image.Image:
        """Draw counter rectangle for both teams"""
        # [Previous implementation remains the same]
        if ratio < 0.15:
            left_rectangle[1][0] += 20

            frame = Draw.half_rounded_rectangle(
                frame,
                rectangle=left_rectangle,
                color=left_color,
                radius=15,
            )

            frame = Draw.half_rounded_rectangle(
                frame,
                rectangle=right_rectangle,
                color=right_color,
                left=True,
                radius=15,
            )
        else:
            right_rectangle[0][0] -= 20

            frame = Draw.half_rounded_rectangle(
                frame,
                rectangle=right_rectangle,
                color=right_color,
                left=True,
                radius=15,
            )

            frame = Draw.half_rounded_rectangle(
                frame,
                rectangle=left_rectangle,
                color=left_color,
                radius=15,
            )

        return frame

    def passes_bar(self, frame: PIL.Image.Image, origin: tuple) -> PIL.Image.Image:
        """Draw passes bar"""
        # [Previous implementation remains the same]
        bar_x = origin[0]
        bar_y = origin[1]
        bar_height = 29
        bar_width = 310

        home_passes = len(self.home.passes)
        away_passes = len(self.away.passes)
        total_passes = home_passes + away_passes

        if total_passes == 0:
            home_ratio = 0
            away_ratio = 0
        else:
            home_ratio = home_passes / total_passes
            away_ratio = away_passes / total_passes

        ratio = home_ratio

        # Protect against too small rectangles
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

        # Draw home text
        if ratio > 0.15:
            home_text = f"{int(home_ratio * 100)}%"

            frame = Draw.text_in_middle_rectangle(
                img=frame,
                origin=left_rectangle[0],
                width=left_rectangle[1][0] - left_rectangle[0][0],
                height=left_rectangle[1][1] - left_rectangle[0][1],
                text=home_text,
                color=self.home.text_color,
            )

        # Draw away text
        if ratio < 0.85:
            away_text = f"{int(away_ratio * 100)}%"

            frame = Draw.text_in_middle_rectangle(
                img=frame,
                origin=right_rectangle[0],
                width=right_rectangle[1][0] - right_rectangle[0][0],
                height=right_rectangle[1][1] - right_rectangle[0][1],
                text=away_text,
                color=self.away.text_color,
            )

        return frame

    def get_possession_background(self) -> PIL.Image.Image:
        """Get possession counter background"""
        # [Previous implementation remains the same]
        counter = PIL.Image.open("./images/possession_board.png").convert("RGBA")
        counter = Draw.add_alpha(counter, 210)
        counter = np.array(counter)
        red, green, blue, alpha = counter.T
        counter = np.array([blue, green, red, alpha])
        counter = counter.transpose()
        counter = PIL.Image.fromarray(counter)
        counter = counter.resize((int(315 * 1.2), int(210 * 1.2)))
        return counter

    def get_passes_background(self) -> PIL.Image.Image:
        """Get passes counter background"""
        # [Previous implementation remains the same]
        counter = PIL.Image.open("./images/passes_board.png").convert("RGBA")
        counter = Draw.add_alpha(counter, 210)
        counter = np.array(counter)
        red, green, blue, alpha = counter.T
        counter = np.array([blue, green, red, alpha])
        counter = counter.transpose()
        counter = PIL.Image.fromarray(counter)
        counter = counter.resize((int(315 * 1.2), int(210 * 1.2)))
        return counter

    def draw_counter_background(
        self,
        frame: PIL.Image.Image,
        origin: tuple,
        counter_background: PIL.Image.Image,
    ) -> PIL.Image.Image:
        """Draw counter background"""
        frame.paste(counter_background, origin, counter_background)
        return frame

    def draw_counter(
        self,
        frame: PIL.Image.Image,
        text: str,
        counter_text: str,
        origin: tuple,
        color: tuple,
        text_color: tuple,
        height: int = 27,
        width: int = 120,
    ) -> PIL.Image.Image:
        """Draw counter"""
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
            img=frame,
            rectangle=team_rectangle,
            color=color,
            radius=20,
        )

        frame = Draw.half_rounded_rectangle(
            img=frame,
            rectangle=time_rectangle,
            color=(239, 234, 229),
            radius=20,
            left=True,
        )

        frame = Draw.text_in_middle_rectangle(
            img=frame,
            origin=team_rectangle[0],
            height=height,
            width=team_width,
            text=text,
            color=text_color,
        )

        frame = Draw.text_in_middle_rectangle(
            img=frame,
            origin=time_rectangle[0],
            height=height,
            width=time_width,
            text=counter_text,
            color="black",
        )

        return frame

    def draw_debug(self, frame: PIL.Image.Image) -> PIL.Image.Image:
        """Draw line from closest player feet to ball"""
        if self.closest_player and self.ball:
            closest_foot = self.closest_player.closest_foot_to_ball(self.ball)

            color = (0, 0, 0)
            # Change line color if its greater than threshold
            distance = self.closest_player.distance_to_ball(self.ball)
            if distance > self.ball_distance_threshold:
                color = (255, 255, 255)

            draw = PIL.ImageDraw.Draw(frame)
            draw.line(
                [
                    tuple(closest_foot),
                    tuple(self.ball.center),
                ],
                fill=color,
                width=2,
            )

    def draw_possession_counter(
        self,
        frame: PIL.Image.Image,
        counter_background: PIL.Image.Image,
        debug: bool = False,
    ) -> PIL.Image.Image:
        """
        Draw elements of the possession in frame with enhanced tactical visualization

        Parameters
        ----------
        frame : PIL.Image.Image
            Frame
        counter_background : PIL.Image.Image
            Counter background
        debug : bool, optional
            Whether to draw extra debug information, by default False

        Returns
        -------
        PIL.Image.Image
            Frame with elements of the match
        """
        # get width of PIL.Image
        frame_width = frame.size[0]
        counter_origin = (frame_width - 540, 40)

        frame = self.draw_counter_background(
            frame,
            origin=counter_origin,
            counter_background=counter_background,
        )

        frame = self.draw_counter(
            frame,
            origin=(counter_origin[0] + 35, counter_origin[1] + 130),
            text=self.home.abbreviation,
            counter_text=self.home.get_time_possession(self.fps),
            color=self.home.board_color,
            text_color=self.home.text_color,
            height=31,
            width=150,
        )
        frame = self.draw_counter(
            frame,
            origin=(counter_origin[0] + 35 + 150 + 10, counter_origin[1] + 130),
            text=self.away.abbreviation,
            counter_text=self.away.get_time_possession(self.fps),
            color=self.away.board_color,
            text_color=self.away.text_color,
            height=31,
            width=150,
        )
        frame = self.possession_bar(
            frame, origin=(counter_origin[0] + 35, counter_origin[1] + 195)
        )

        if self.closest_player:
            frame = self.closest_player.draw_pointer(frame)

        if debug:
            frame = self.draw_debug(frame=frame)

        return frame

    def draw_passes_counter(
        self,
        frame: PIL.Image.Image,
        counter_background: PIL.Image.Image,
        debug: bool = False,
    ) -> PIL.Image.Image:
        """
        Draw elements of the passes in frame with enhanced tactical visualization

        Parameters
        ----------
        frame : PIL.Image.Image
            Frame
        counter_background : PIL.Image.Image
            Counter background
        debug : bool, optional
            Whether to draw extra debug information, by default False

        Returns
        -------
        PIL.Image.Image
            Frame with elements of the match
        """
        # get width of PIL.Image
        frame_width = frame.size[0]
        counter_origin = (frame_width - 540, 40)

        frame = self.draw_counter_background(
            frame,
            origin=counter_origin,
            counter_background=counter_background,
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

    def toggle_formation_lines(self):
        """Liga/desliga linhas de formação"""
        self.show_formation_lines = not self.show_formation_lines
        self.tactical_viz.formation_lines_enabled = self.show_formation_lines

    def toggle_formation_polygons(self):
        """Liga/desliga polígonos de formação"""
        self.show_formation_polygons = not self.show_formation_polygons
        self.tactical_viz.formation_polygons_enabled = self.show_formation_polygons

    def toggle_ball_trail(self):
        """Liga/desliga rastro da bola"""
        self.show_ball_trail = not self.show_ball_trail
        self.tactical_viz.ball_trail_enabled = self.show_ball_trail
        if self.ball:
            self.ball.trail_enabled = self.show_ball_trail

    def toggle_tactical_info(self):
        """Liga/desliga painel de informações táticas"""
        self.show_tactical_info = not self.show_tactical_info