import argparse

import cv2
import numpy as np
import PIL
from norfair import Tracker, Video
from norfair.camera_motion import MotionEstimator
from norfair.distances import mean_euclidean

from inference import Converter, HSVClassifier, InertiaClassifier, YoloV5
from inference.filters import filters
from run_utils import (
    get_ball_detections,
    get_main_ball,
    get_player_detections,
    update_motion_estimator,
)
from soccer import Match, Player, Team
from soccer.draw import AbsolutePath
from soccer.pass_event import Pass

parser = argparse.ArgumentParser(description="Soccer Video Analytics with Complete Tactical Analysis")
parser.add_argument(
    "--video",
    default="videos/soccer_possession.mp4",
    type=str,
    help="Path to the input video",
)
parser.add_argument(
    "--model", 
    default=None,  # Mudança: default None em vez de caminho específico
    type=str, 
    help="Path to the ball detection model (optional, will use sports ball detection if not provided)"
)
parser.add_argument(
    "--passes",
    action="store_true",
    help="Enable pass detection and visualization",
)
parser.add_argument(
    "--possession",
    action="store_true",
    help="Enable possession counter and analysis",
)
parser.add_argument(
    "--tactical",
    action="store_true",
    help="Enable complete tactical visualization (formation lines, polygons, ball trail)",
)
parser.add_argument(
    "--formation-lines",
    action="store_true",
    help="Show formation lines between players of same team",
)
parser.add_argument(
    "--formation-polygons",
    action="store_true",
    help="Show formation polygons for each team",
)
parser.add_argument(
    "--ball-trail",
    action="store_true",
    help="Show ball movement trail",
)
parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable debug mode with additional information",
)
args = parser.parse_args()

# Se --tactical foi especificado, habilita todos os recursos táticos
if args.tactical:
    args.formation_lines = True
    args.formation_polygons = True
    args.ball_trail = True

print("🏈 Iniciando Soccer Video Analytics com Análise Tática Completa")
print("=" * 60)
print(f"📹 Vídeo: {args.video}")
if args.model:
    print(f"🤖 Modelo da bola: {args.model}")
else:
    print("⚽ Usando detecção padrão de bola esportiva (sports ball)")
print(f"⚽ Análise de posse: {'✅' if args.possession else '❌'}")
print(f"🏃 Análise de passes: {'✅' if args.passes else '❌'}")
print(f"📊 Linhas de formação: {'✅' if args.formation_lines else '❌'}")
print(f"🔷 Polígonos de formação: {'✅' if args.formation_polygons else '❌'}")
print(f"🎯 Rastro da bola: {'✅' if args.ball_trail else '❌'}")
print(f"🐛 Modo debug: {'✅' if args.debug else '❌'}")
print("=" * 60)

video = Video(input_path=args.video)
fps = video.video_capture.get(cv2.CAP_PROP_FPS)

# Object Detectors
print("🔍 Inicializando detectores de objetos...")
player_detector = YoloV5()

# Detector de bola: usar modelo customizado se fornecido, senão usar detecção padrão
if args.model:
    try:
        print(f"🤖 Tentando carregar modelo customizado da bola: {args.model}")
        ball_detector = YoloV5(model_path=args.model)
        print("✅ Modelo customizado carregado com sucesso!")
    except Exception as e:
        print(f"⚠️  Erro ao carregar modelo customizado: {e}")
        print("🔄 Usando detecção padrão de bola esportiva...")
        ball_detector = YoloV5()
else:
    print("⚽ Usando detecção padrão de bola esportiva (classe 'sports ball')...")
    ball_detector = YoloV5()

# HSV Classifier
print("🎨 Configurando classificador HSV para times...")
hsv_classifier = HSVClassifier(filters=filters)

# Add inertia to classifier
classifier = InertiaClassifier(classifier=hsv_classifier, inertia=20)

# Teams and Match
print("⚽ Configurando times e partida...")
chelsea = Team(
    name="Chelsea",
    abbreviation="CHE",
    color=(255, 0, 0),
    board_color=(244, 86, 64),
    text_color=(255, 255, 255),
)
man_city = Team(
    name="Man City", 
    abbreviation="MNC", 
    color=(240, 230, 188),
    board_color=(135, 206, 235),
    text_color=(0, 0, 0)
)

# Para o jogo Miami vs Palmeiras, vamos usar nomes mais apropriados
miami = Team(
    name="Inter Miami",
    abbreviation="MIA",
    color=(255, 182, 193),  # Rosa/Pink
    board_color=(255, 20, 147),
    text_color=(255, 255, 255),
)
palmeiras = Team(
    name="Palmeiras", 
    abbreviation="PAL", 
    color=(0, 128, 0),      # Verde
    board_color=(34, 139, 34),
    text_color=(255, 255, 255)
)

teams = [miami, palmeiras]
match = Match(home=miami, away=palmeiras, fps=fps)
match.team_possession = miami

# Configurações táticas baseadas nos argumentos
match.show_formation_lines = args.formation_lines
match.show_formation_polygons = args.formation_polygons
match.show_ball_trail = args.ball_trail

# Tracking
print("🎯 Configurando sistema de tracking...")
player_tracker = Tracker(
    distance_function=mean_euclidean,
    distance_threshold=250,
    initialization_delay=3,
    hit_counter_max=90,
)

ball_tracker = Tracker(
    distance_function=mean_euclidean,
    distance_threshold=150,
    initialization_delay=20,
    hit_counter_max=2000,
)
motion_estimator = MotionEstimator()
coord_transformations = None

# Paths
path = AbsolutePath()

# Get Counter img
print("🖼️ Carregando backgrounds dos contadores...")
try:
    possession_background = match.get_possession_background()
    passes_background = match.get_passes_background()
except:
    print("⚠️ Aviso: Imagens de background não encontradas, usando background padrão")
    possession_background = None
    passes_background = None

print("🚀 Iniciando processamento do vídeo...")
frame_count = 0
total_frames = int(video.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))

for i, frame in enumerate(video):
    frame_count += 1
    
    # Progress indicator
    if frame_count % 30 == 0:  # A cada segundo (assumindo 30 fps)
        progress = (frame_count / total_frames) * 100
        print(f"⏳ Processando frame {frame_count}/{total_frames} ({progress:.1f}%)")

    # Get Detections
    players_detections = get_player_detections(player_detector, frame)
    ball_detections = get_ball_detections(ball_detector, frame, use_sports_ball=(args.model is None))
    detections = ball_detections + players_detections

    # Update trackers
    coord_transformations = update_motion_estimator(
        motion_estimator=motion_estimator,
        detections=detections,
        frame=frame,
    )

    player_track_objects = player_tracker.update(
        detections=players_detections, coord_transformations=coord_transformations
    )

    ball_track_objects = ball_tracker.update(
        detections=ball_detections, coord_transformations=coord_transformations
    )

    player_detections = Converter.TrackedObjects_to_Detections(player_track_objects)
    ball_detections = Converter.TrackedObjects_to_Detections(ball_track_objects)

    # Classify players by team
    player_detections = classifier.predict_from_detections(
        detections=player_detections,
        img=frame,
    )

    # Match update
    ball = get_main_ball(ball_detections, match)
    players = Player.from_detections(detections=player_detections, teams=teams)
    match.update(players, ball)

    # Convert to PIL for drawing
    frame = PIL.Image.fromarray(frame)

    # Draw tactical visualization FIRST (background layer)
    if args.formation_lines or args.formation_polygons or args.ball_trail:
        frame = match.draw_tactical_visualization(frame, players)

    # Draw possession analysis
    if args.possession:
        frame = Player.draw_players(
            players=players, frame=frame, confidence=args.debug, id=args.debug
        )

        # Draw ball trail and ball
        if ball and ball.detection:
            # Ball trail is drawn automatically in ball.draw() if enabled
            ball.trail_enabled = args.ball_trail
            frame = ball.draw(frame)
        
        # Draw path with team color
        if ball and ball.detection:
            frame = path.draw(
                img=frame,
                detection=ball.detection,
                coord_transformations=coord_transformations,
                color=match.team_possession.color if match.team_possession else (255, 255, 255),
            )

        # Draw possession counter
        if possession_background is not None:
            frame = match.draw_possession_counter(
                frame, counter_background=possession_background, debug=args.debug
            )

    # Draw passes analysis
    if args.passes:
        pass_list = match.passes

        frame = Pass.draw_pass_list(
            img=frame, passes=pass_list, coord_transformations=coord_transformations
        )

        if passes_background is not None:
            frame = match.draw_passes_counter(
                frame, counter_background=passes_background, debug=args.debug
            )

    # Draw enhanced tactical info panel
    if args.debug or args.tactical:
        frame = match.draw_enhanced_info_panel(frame)

    # Add watermark with enabled features
    if args.debug:
        features = []
        if args.formation_lines: features.append("Lines")
        if args.formation_polygons: features.append("Polygons") 
        if args.ball_trail: features.append("Trail")
        if args.possession: features.append("Possession")
        if args.passes: features.append("Passes")
        
        watermark = f"Tactical Analysis: {', '.join(features) if features else 'Basic'}"
        draw = PIL.ImageDraw.Draw(frame)
        draw.text((10, 10), watermark, fill=(255, 255, 255))

    frame = np.array(frame)

    # Write video
    video.write(frame)

print("✅ Processamento concluído!")
print(f"📊 Estatísticas finais:")
print(f"   • Frames processados: {frame_count}")
print(f"   • Duração: {frame_count//fps//60:02d}:{(frame_count//fps)%60:02d}")

if match.team_possession:
    stats = match.get_tactical_stats()
    print(f"   • Posse de bola {miami.name}: {stats['possession_ratio']['home']*100:.1f}%")
    print(f"   • Posse de bola {palmeiras.name}: {stats['possession_ratio']['away']*100:.1f}%")
    print(f"   • Total de passes: {stats['total_passes']}")
    print(f"   • Passes {miami.name}: {stats['home_passes']}")
    print(f"   • Passes {palmeiras.name}: {stats['away_passes']}")

print(f"🎬 Vídeo de saída salvo como: {args.video.replace('.mp4', '_out.mp4')}")