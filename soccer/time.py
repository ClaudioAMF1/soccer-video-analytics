# soccer/time.py
class Time:
    def __init__(self, nome, abreviacao, cor, cor_placar=None, cor_texto=(255, 255, 255)):
        self.nome = nome
        self.abreviacao = abreviacao
        self.cor = cor
        self.cor_texto = cor_texto
        self.cor_placar = cor_placar if cor_placar is not None else cor
        self.posse_de_bola_frames = 0
        self.passes = []

    def obter_percentual_posse(self, duracao_total_frames: int) -> float:
        if duracao_total_frames == 0: return 0
        return round(self.posse_de_bola_frames / duracao_total_frames, 2)

    def obter_tempo_posse_formatado(self, fps: int) -> str:
        segundos = round(self.posse_de_bola_frames / fps) if fps > 0 else 0
        minutos = int(segundos // 60)
        segundos = int(segundos % 60)
        return f"{minutos:02d}:{segundos:02d}"

    def __str__(self): return self.nome
    def __eq__(self, other): return isinstance(other, Time) and self.nome == other.nome