# soccer/desenho.py
import PIL
from PIL import ImageDraw, ImageFont

class Desenho:
    @staticmethod
    def obter_fonte(tamanho=18):
        try:
            return PIL.ImageFont.truetype("DejaVuSans.ttf", size=tamanho)
        except IOError:
            return PIL.ImageFont.load_default()

    @staticmethod
    def desenhar_deteccao(detection, img, cor):
        desenhador = ImageDraw.Draw(img)
        desenhador.rounded_rectangle([tuple(p) for p in detection.points], radius=5, outline=cor, width=3)
        return img

    @staticmethod
    def desenhar_ponteiro(detection, img, cor):
        x1, y1 = detection.points[0]; x2, _ = detection.points[1]
        centro_x = (x1 + x2) / 2
        desenhador = ImageDraw.Draw(img)
        pontos = [(centro_x, y1 - 8), (centro_x - 10, y1 - 25), (centro_x + 10, y1 - 25)]
        desenhador.polygon(pontos, fill=cor, outline="black", width=1)
        return img

    @staticmethod
    def desenhar_painel_posse(img, partida):
        desenhador = ImageDraw.Draw(img, "RGBA")
        painel_rect = (10, 10, 310, 90)
        desenhador.rounded_rectangle(painel_rect, radius=10, fill=(0, 0, 0, 180))

        fonte_titulo = Desenho.obter_fonte(16); fonte_time = Desenho.obter_fonte(20)
        
        desenhador.text((25, 18), "POSSE DE BOLA", fill="white", font=fonte_titulo)
        
        casa, fora = partida.time_casa, partida.time_visitante
        
        # Exibe "SEM POSSE" se nenhum time tiver o controle
        if not partida.time_com_posse:
            fonte_sem_posse = Desenho.obter_fonte(22)
            desenhador.text((90, 45), "SEM POSSE", fill=(200, 200, 200), font=fonte_sem_posse)
        else:
            posse_casa = casa.obter_percentual_posse(partida.duracao_total_frames) * 100
            posse_fora = fora.obter_percentual_posse(partida.duracao_total_frames) * 100

            desenhador.text((25, 45), f"{casa.abreviacao}", fill=casa.cor, font=fonte_time)
            desenhador.text((90, 45), f"{posse_casa:.1f}%", fill="white", font=fonte_time)
            
            desenhador.text((170, 45), f"{fora.abreviacao}", fill=fora.cor, font=fonte_time)
            desenhador.text((235, 45), f"{posse_fora:.1f}%", fill="white", font=fonte_time)
            
        return img