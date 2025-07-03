# config/filtros_cores.py
preto = {"name": "preto", "lower_hsv": (0, 0, 0), "upper_hsv": (179, 255, 45)}
branco = {"name": "branco", "lower_hsv": (0, 0, 180), "upper_hsv": (179, 30, 255)}
verde = {"name": "verde", "lower_hsv": (40, 40, 40), "upper_hsv": (80, 255, 255)}
rosa = {"name": "rosa", "lower_hsv": (145, 60, 100), "upper_hsv": (175, 255, 255)}
amarelo = {"name": "amarelo", "lower_hsv": (22, 93, 0), "upper_hsv": (45, 255, 255)}

filtro_arbitro = {"name": "Referee", "colors": [amarelo, preto]}
filtro_inter_miami = {"name": "Inter Miami", "colors": [rosa]}
filtro_palmeiras = {"name": "Palmeiras", "colors": [branco, verde]}

# Ordem de prioridade: Árbitro primeiro, para evitar confusão com outras cores
filtros = [filtro_arbitro, filtro_inter_miami, filtro_palmeiras]