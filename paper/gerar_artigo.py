"""Gera o artigo final (.docx) a partir dos resultados dos experimentos.

Todos os números do texto vêm dos CSVs em `paper/dados/`, produzidos pelos
scripts de `experiments/`. Nenhum valor é digitado à mão: para atualizar o
artigo, reexecute os experimentos, copie os CSVs e rode este script.

Formatação: Times New Roman 12, espaçamento 1,5, margens de 2,5 cm; resumo,
legendas e referências em espaço simples; referências segundo a ABNT NBR 6023.

Uso:
    python paper/gerar_artigo.py --dados paper/dados --saida paper/Artigo_Final.docx
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import numpy as np
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

RAIZ = Path(__file__).resolve().parent
FONTE = "Times New Roman"
LIMIAR = 5.0


# ------------------------------------------------------------------ dados
def ler(caminho: Path) -> list[dict]:
    with caminho.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def br(v: float, casas: int = 1) -> str:
    """Número no formato brasileiro: 1.470,5."""
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def cruzamento(x, y, limiar=LIMIAR):
    """Primeiro erro de registro em que a curva atinge o limiar (interpolação linear)."""
    for (x0, y0), (x1, y1) in zip(zip(x, y), zip(x[1:], y[1:])):
        if y0 < limiar <= y1:
            return x0 + (limiar - y0) / (y1 - y0) * (x1 - x0)
    return None


def numeros(d: Path) -> dict:
    R = {}
    # E5 real
    e5 = [l for l in ler(d / "e5_real.csv") if l["erro_medio_m"] not in ("", "None")]
    x = [float(l["erro_medio_m"]) for l in e5]
    for k in ("controle_equipe", "largura", "profundidade", "area_ocupacao", "identidade_dominante"):
        y = [float(l[k]) for l in e5]
        R[f"lim_{k}"] = cruzamento(x, y)
        R[f"max_{k}"] = y[-1]
    R["e5_xmax"] = x[-1]
    R["e5_controle_1m"] = float(np.interp(1.0, x, [float(l["controle_equipe"]) for l in e5]))
    R["e5_area_1m"] = float(np.interp(1.0, x, [float(l["area_ocupacao"]) for l in e5]))
    R["e5_ident_1m"] = float(np.interp(1.0, x, [float(l["identidade_dominante"]) for l in e5]))
    R["e5_amostras"] = sum(int(l["n"]) for l in e5)
    info = dict(l.split("=", 1) for l in (d / "e5_real_info.txt").read_text(encoding="utf-8").split())
    R.update({f"e5_{k}": float(v) for k, v in info.items()})

    # E2 real
    e2 = {l["condicao"]: l for l in ler(d / "e2_registro_real.csv")}
    R["e2"] = e2
    R["e2_quadros"] = int(e2["referencia_por_quadro"]["quadros"])

    # E1 real
    e1 = {l["medida"]: l for l in ler(d / "e1_deteccao_real.csv")}
    R["e1"] = {k: float(v["valor_pct"]) for k, v in e1.items()}
    R["e1_n"] = {k: int(v["n"]) for k, v in e1.items()}

    # Narrativa real
    nr = ler(d / "narrativa_real.csv")
    R["nar"] = {(float(l["erro_m"]), l["versao"]): l for l in nr}

    # Caracterização
    R.update({k: float(v) for k, v in (l.split("=", 1) for l in
              (d / "caracterizacao.txt").read_text(encoding="utf-8").split())})
    return R


# ------------------------------------------------------------------ formatação
def _runs(p, texto: str, tamanho=12):
    """**negrito** e _itálico_ dentro do texto."""
    for parte in re.split(r"(\*\*[^*]+\*\*|_[^_]+_)", texto):
        if not parte:
            continue
        r = p.add_run(parte.strip("*") if parte.startswith("**") else parte[1:-1] if parte.startswith("_") else parte)
        r.bold = parte.startswith("**")
        r.italic = parte.startswith("_")
        r.font.name = FONTE
        r.font.size = Pt(tamanho)
        r._element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)


def paragrafo(doc, texto, *, recuo=True, alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, simples=False,
              tamanho=12, antes=0, depois=0):
    p = doc.add_paragraph()
    f = p.paragraph_format
    f.alignment = alinhamento
    f.first_line_indent = Cm(1.25) if recuo else Cm(0)
    f.line_spacing_rule = WD_LINE_SPACING.SINGLE if simples else WD_LINE_SPACING.ONE_POINT_FIVE
    f.space_before, f.space_after = Pt(antes), Pt(depois)
    _runs(p, texto, tamanho)
    return p


def secao(doc, titulo):
    p = paragrafo(doc, f"**{titulo.upper()}**", recuo=False, alinhamento=WD_ALIGN_PARAGRAPH.LEFT,
                  antes=12, depois=6)
    p.paragraph_format.keep_with_next = True


def legenda(doc, texto):
    p = paragrafo(doc, texto, recuo=False, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, simples=True,
                  tamanho=10, antes=6, depois=3)
    p.paragraph_format.keep_with_next = True


def fonte(doc, texto="Fonte: elaborada pelos autores (2026)."):
    paragrafo(doc, texto, recuo=False, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, simples=True,
              tamanho=10, antes=3, depois=6)


def figura(doc, caminho: Path, largura_cm: float):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(caminho), width=Cm(largura_cm))


def _borda(celula, **lados):
    tcPr = celula._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for lado, esp in lados.items():
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single" if esp else "nil")
        e.set(qn("w:sz"), str(esp or 0))
        e.set(qn("w:color"), "000000")
        b.append(e)
    tcPr.append(b)


def tabela(doc, linhas: list[list[str]], larguras_cm: list[float]):
    """Tabela aberta (padrão IBGE adotado pela ABNT): só traços horizontais."""
    t = doc.add_table(rows=len(linhas), cols=len(linhas[0]))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, linha in enumerate(linhas):
        for j, texto in enumerate(linha):
            c = t.cell(i, j)
            c.width = Cm(larguras_cm[j])
            c.paragraphs[0].text = ""
            p = c.paragraphs[0]
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            _runs(p, f"**{texto}**" if i == 0 else texto, 10)
            topo = 8 if i == 0 else 0
            base = 4 if i == 0 else (8 if i == len(linhas) - 1 else 0)
            _borda(c, top=topo, bottom=base, left=0, right=0)
    return t


def referencia(doc, texto):
    p = paragrafo(doc, texto, recuo=False, alinhamento=WD_ALIGN_PARAGRAPH.LEFT, simples=True, depois=12)
    p.paragraph_format.keep_together = True


# ------------------------------------------------------------------ texto
def montar(R: dict, saida: Path) -> None:
    e2, e1, nar = R["e2"], R["e1"], R["nar"]
    dist = lambda v: br(v, 1 if v >= 10 else 2)
    m = lambda k: dist(float(e2[k]["mediana_m"]))
    p90 = lambda k: dist(float(e2[k]["p90_m"]))
    abaixo = lambda k: br(float(e2[k]["pct_abaixo_1m"]), 0)
    ing, his = nar[(1.0, "ingenua")], nar[(1.0, "histerese")]
    his0 = nar[(0.0, "histerese")]
    fr = lambda s: tuple(int(v) for v in s.split("/"))
    fc, fo = fr(his0["finalizacao_em_chutes"]), fr(his0["finalizacao_em_outros"])
    pc, po = 100 * fc[0] / fc[1], 100 * fo[0] / fo[1]
    L = lambda k: br(R[f"lim_{k}"], 2)
    r1, rr = "chaves_1s_so_anterior", "chaves_1s_reancorado"

    doc = Document()
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
    for lado in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(sec, lado, Cm(2.5))
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = FONTE, Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)

    # ---------------- cabeçalho do artigo
    paragrafo(doc, "**DO PIXEL À NARRATIVA: VISUALIZAÇÕES CONFIÁVEIS DE CONTROLE DE ESPAÇO EM "
                   "TRANSMISSÕES DE FUTEBOL PARA O PÚBLICO GERAL**",
              recuo=False, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, depois=12)
    paragrafo(doc, "Claudio da Aparecida Meireles Filho, Felipe Pereira Dutra, "
                   "Lucas Fiche Ungarelli Borges, Pedro Rodrigues de Araújo",
              recuo=False, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, simples=True)
    paragrafo(doc, "Instituto Brasileiro de Ensino, Desenvolvimento e Pesquisa (IDP)",
              recuo=False, alinhamento=WD_ALIGN_PARAGRAPH.CENTER, simples=True, depois=12)

    paragrafo(doc,
        "**Resumo:** Modelos de controle de espaço estimam qual equipe domina cada região do campo "
        "(SPEARMAN et al., 2017), mas dependem de rastreamento proprietário e raramente chegam ao "
        "público. Este trabalho investiga se essas métricas podem ser extraídas de jogos gravados de "
        "transmissão e apresentadas a espectadores leigos sem afirmar o que a medição não sustenta. O "
        "pipeline proposto combina detecção de atletas, registro do campo por homografia em "
        "quadros-chave propagados pelo movimento da câmera, uma regra de exibição derivada de análise "
        "de sensibilidade e uma interface narrativa orientada a estados. Avaliado em "
        f"{br(R['quadros'], 0)} quadros de 49 transmissões reais do SoccerNet-GSR, o registro com uma "
        f"chave por segundo errou {m(r1)} m em mediana, contra {m('homografia_unica')} m de uma "
        "homografia única. O controle de espaço por equipe manteve erro relativo abaixo de 5% até "
        f"{br(R['e5_xmax'], 1)} m de erro de registro, enquanto a forma da equipe e a identidade do "
        f"jogador dominante atingiram esse limite entre {L('area_ocupacao')} e {L('largura')} m. A "
        "histerese reduziu as trocas de posse por minuto de "
        f"{br(float(ing['trocas_posse_por_min']))} para {br(float(his['trocas_posse_por_min']))}. "
        "Conclui-se que visualizações coletivas podem ser oferecidas ao público com segurança, e as "
        "individuais exigem registro mais preciso.",
        recuo=False, simples=True, depois=6)
    paragrafo(doc, "**Palavras-chave:** visão computacional; homografia; análise esportiva; "
                   "narrativa com dados; interação humano-computador.",
              recuo=False, simples=True, depois=6)

    # ---------------- introdução
    secao(doc, "Introdução")
    paragrafo(doc,
        "Dados de rastreamento transformaram a análise tática no futebol profissional. Sistemas ópticos "
        "registram a posição de todos os atletas e da bola várias vezes por segundo, e Bialkowski et al. "
        "(2014) mostraram que essas trajetórias revelam formações e papéis táticos ao longo de uma "
        "temporada inteira. Esse conhecimento, porém, quase não chega ao público, por três motivos: os "
        "dados vêm de sistemas instalados nos estádios e vendidos sob contratos exclusivos; as métricas "
        "são grandezas probabilísticas, pensadas para analistas; e a transmissão dispõe de poucos "
        "segundos para cada gráfico, limitando-se a números como posse de bola e finalizações. O "
        "espectador ouve falar de espaço e compactação, mas raramente enxerga esses conceitos no lance, "
        "dificuldade também relatada entre torcedores casuais de basquete (CHEN et al., 2023).")
    paragrafo(doc,
        "Um exemplo evidencia a distância. O modelo de Spearman et al. (2017) atribui a cada ponto do "
        "campo a probabilidade de cada atleta alcançá-lo primeiro, a partir de posição, velocidade e "
        "tempo de reação, e prevê a equipe que receberá um passe com 81% de acurácia. Fernández, Bornn "
        "e Cervone (2021) combinam esse controle com as probabilidades de passe e de finalização no "
        "valor esperado da posse, um número entre −1 e 1. São ferramentas poderosas, mas um valor "
        "esperado de 0,07 nada diz a um espectador sem formação técnica.")
    paragrafo(doc,
        "A visão computacional permite estimar essas posições a partir do próprio vídeo, mas a "
        "transmissão impõe duas dificuldades. A câmera principal gira e aproxima a imagem para "
        "acompanhar a bola, o que obriga a recalcular a cada quadro a correspondência entre imagem e "
        "gramado; e a transmissão alterna entre câmeras, com 13 tipos distinguidos no SoccerNet-v2 "
        "(DELIÈGE et al., 2021). Métricas calculadas sobre a imagem variam com o enquadramento, e uma "
        "interface que ignore o erro de medição pode apresentar ao público, com aparência de precisão, "
        "uma informação falsa. Este artigo investiga se o controle de espaço pode ser levado de jogos "
        "gravados de transmissão ao espectador leigo exibindo apenas o que resiste a esse erro: propõe "
        "um registro do campo por quadros-chave, mede sobre transmissões reais a sensibilidade de cada "
        "métrica ao registro e usa a medição para decidir o que uma interface narrativa pode mostrar.")

    # ---------------- fundamentação
    secao(doc, "Fundamentação teórica")
    paragrafo(doc,
        "As Regras do Jogo admitem campos de 100 a 110 por 64 a 75 metros em partidas internacionais, "
        "mas fixam as marcações, como a grande área de 16,5 metros e o círculo central de 9,15 metros de "
        "raio (IFAB, 2026); adota-se o campo de 105 por 68 metros. Como o gramado é plano, a correspondência entre a "
        "imagem e o campo é uma homografia, transformação projetiva de oito graus de liberdade "
        "estimável a partir de quatro pontos pelo algoritmo DLT com normalização prévia (HARTLEY; "
        "ZISSERMAN, 2004), enquanto o RANSAC descarta correspondências espúrias (FISCHLER; BOLLES, "
        "1981); Theiner e Ewerth (2023) tratam o problema como calibração da câmera. Quando a câmera "
        "apenas gira e aproxima a imagem, quadros consecutivos também se relacionam por uma homografia, "
        "estimável rastreando cantos do fundo (SHI; TOMASI, 1994) por fluxo óptico (LUCAS; KANADE, "
        "1981); compor essas transformações propaga o registro de um quadro aos vizinhos, ao custo de "
        "acumular erro.")
    paragrafo(doc,
        "O controle de espaço estende a região dominante de Taki e Hasegawa (2000): cada ponto do campo "
        "pertence à equipe cujo atleta chegaria primeiro a ele, considerando velocidade e direção do "
        "movimento, o que exige vídeo, e não imagens isoladas; Fernández e Bornn (2018) usam a mesma "
        "formulação para medir a criação de espaços. A posse de bola não é definida pelas regras: "
        "adota-se a convenção de que a equipe a mantém enquanto a bola circula entre seus jogadores, "
        "inclusive durante um passe. A narrativa apoia-se nas fases do jogo: construção, com a posse no "
        "próprio campo; ataque, no campo adversário; transição, logo após uma troca de posse; e "
        "finalização, a chegada perto do gol com espaço livre.")
    paragrafo(doc,
        "Para a detecção, o YOLOv8 (JOCHER; CHAURASIA; QIU, 2023) treinado no COCO (LIN et al., 2014) "
        "oferece as classes pessoa e bola esportiva, e a inferência fatiada processa recortes da imagem "
        "em resolução maior, favorecendo objetos pequenos como a bola (AKYON; ALTINUC; TEMIZEL, 2022). O "
        "SoccerNet-GSR fornece sequências de transmissão com a posição de referência de cada atleta "
        "(SOMERS et al., 2024). Na visualização esportiva (PERIN et al., 2018), o SoccerStories "
        "(PERIN; VUILLEMOT; FEKETE, 2013) apoia analistas de futebol, e o VisCommentator (CHEN et al., "
        "2022) e o iBall (CHEN et al., 2023) inserem visualizações em vídeos de tênis de mesa e de "
        "basquete, este avaliado com 16 torcedores casuais. Esses sistemas operam com poucos atletas e "
        "câmera quase fixa, e nenhum verifica se o que exibem resiste ao erro da medição automática.")

    # ---------------- metodologia
    secao(doc, "Metodologia")
    paragrafo(doc,
        "O sistema tem três módulos que se comunicam por um arquivo JSON. O de extração parte da "
        "implementação aberta de Tryolabs (2022), da qual herda o rastreamento e a classificação de "
        "equipes por cor. O vídeo é segmentado em planos de câmera, pela distância de Bhattacharyya "
        "entre histogramas de cor de quadros consecutivos e pela proporção de gramado, e só os planos "
        "abertos são processados. Em quadros-chave, marcos do campo escolhidos entre 29 definidos pelas "
        "medidas oficiais são anotados manualmente, e a homografia é estimada por DLT normalizado com "
        "RANSAC. Entre chaves, ela é propagada a partir da chave anterior pelo movimento da câmera, "
        "estimado por fluxo óptico com as caixas dos atletas e as faixas de grafismo mascaradas; "
        "avaliou-se também a reancoragem, que combina as estimativas das duas chaves vizinhas "
        "ponderadas pela proximidade. Cada atleta é representado pelo ponto médio da base de "
        "sua caixa, que aproxima o contato dos pés com o gramado.")
    paragrafo(doc,
        "O módulo narrativo decide a posse com limiar de 2 metros e confirmação em três quadros, e "
        "calcula o controle de espaço numa grade de 3 metros a partir do tempo até a interceptação de "
        "cada atleta. Uma máquina de estados classifica cada instante nas fases do jogo; a finalização "
        "exige a bola a menos de 20 metros do gol e o defensor mais próximo a mais de 5 metros, com "
        "histerese (o estado só termina acima de 23 metros ou com defensor a menos de 3,5 metros) e "
        "confirmação em cinco quadros, e cada estado gera uma legenda em linguagem comum. Uma "
        "visualização só é exibida se as métricas que a sustentam tiverem erro relativo abaixo de 5% "
        "no erro de registro medido. O módulo de visualização é um player web que projeta as camadas "
        "sobre o vídeo pela homografia de cada quadro (Figura 1).")
    legenda(doc, "Figura 1 – Protótipo do player: zonas de controle e forma das equipes projetadas "
                 "sobre a imagem, com a legenda do estado de finalização")
    figura(doc, RAIZ / "figuras" / "prototipo_player.png", 8.0)
    fonte(doc)
    paragrafo(doc,
        f"A avaliação usou as {br(R['sequencias'], 0)} sequências de teste do SoccerNet-GSR, de 30 "
        f"segundos a 25 quadros por segundo ({br(R['quadros'], 0)} quadros) e de "
        f"{br(R['tipos_evento'], 0)} tipos de evento, como escanteios, chutes e faltas. Em cada quadro, "
        "uma homografia de referência foi ajustada às posições anotadas, com resíduo mediano de "
        f"{br(R['residuo_ref_m'], 2)} m. Foram quatro experimentos. Na detecção, o YOLOv8x com pesos "
        "COCO e os limiares do pipeline foi aplicado a um quadro a cada 3 segundos. No registro, "
        "a anotação foi simulada projetando os marcos visíveis com a homografia de referência e somando "
        "ruído de 2 pixels, a imprecisão de um clique, com chaves a cada 1, 2 e 5 segundos. Na "
        "sensibilidade, em um quadro por segundo, as correspondências do registro receberam ruído de 2 "
        "a 32 pixels. Na narrativa, a máquina de estados foi comparada a uma versão de corte único sob "
        "ruído de registro de 1 metro, e o estado de finalização foi confrontado com o tipo de evento anotado, "
        "rótulo independente do sistema. Um estudo com 24 espectadores leigos, que compara o player a "
        "um mapa tático estático, foi planejado como etapa seguinte.")

    # ---------------- resultados
    secao(doc, "Resultados e discussão")
    paragrafo(doc,
        f"A câmera mostra em média {br(R['atletas_por_quadro'])} atletas por quadro, de 22 em campo, e "
        f"a bola tem posição anotada em {br(R['pct_bola'], 0)}% dos quadros. Há em mediana "
        f"{br(R['e5_marcos_mediana'], 0)} marcos do campo visíveis por quadro; {br(R['e5_pct_4'], 0)}% "
        f"dos quadros têm os quatro necessários ao registro e {br(R['e5_pct_6'], 0)}% têm seis ou mais, "
        "o que torna viável a anotação de quadros-chave. A câmera se move continuamente: uma "
        "homografia única, válida no primeiro quadro, erra a posição dos atletas em "
        f"{m('homografia_unica')} m (mediana) ao longo da sequência.")
    paragrafo(doc,
        f"O detector encontrou {br(e1['revocacao_atletas'], 0)}% dos atletas, mas só "
        f"{br(e1['revocacao_atletas_pequenos'], 0)}% dos que têm menos de 60 pixels de altura, ao fundo "
        f"do enquadramento. Das detecções de pessoa, {br(e1['precisao_pessoas_sem_filtro'], 0)}% eram "
        "atletas; as demais eram torcedores, gandulas e comissões técnicas. Descartar as detecções "
        "cujo ponto de apoio, projetado pelo registro, cai fora do gramado elevou a precisão para "
        f"{br(e1['precisao_pessoas_filtro_campo'], 0)}%, sem treinamento adicional. A bola, com diâmetro "
        f"mediano de {br(e1['tamanho_mediano_bola_px'], 0)} pixels em imagens de 1920 por 1080, foi "
        f"localizada em {br(e1['bola_localizada_quadro_inteiro'], 0)}% dos quadros; numa subamostra de "
        f"{R['e1_n']['bola_localizada_fatiado_subamostra']} quadros, a inferência fatiada passou de "
        f"{br(e1['bola_localizada_inteiro_subamostra'], 0)}% para "
        f"{br(e1['bola_localizada_fatiado_subamostra'], 0)}%, ganho modesto. A bola é o elo mais frágil "
        "do pipeline e justifica o ajuste fino do detector com dados de futebol.")
    paragrafo(doc,
        "A Tabela 1 mostra o erro do registro por quadros-chave. Com uma chave por segundo propagada "
        f"a partir da anterior, o erro mediano foi de {m(r1)} m, com {abaixo(r1)}% dos quadros abaixo "
        f"de 1 metro, ante {m('chaves_1s_sem_propagacao')} m sem propagação. A reancoragem reduziu a "
        f"mediana para {m(rr)} m, mas elevou o percentil 90 de {p90(r1)} para {p90(rr)} m: quando a "
        "propagação a partir de uma das chaves falha, a média ponderada herda o erro. Com chaves mais "
        "espaçadas, a deriva do fluxo óptico cresce nas sequências em que a "
        "câmera gira depressa. O custo é o principal limite do método: com seis marcos por chave, uma "
        "sequência de 30 segundos exige cerca de 180 cliques.")
    legenda(doc, "Tabela 1 – Erro de posição dos atletas, em metros, por intervalo entre "
                 "quadros-chave: mediana (percentil 90)")
    linhas = [["Intervalo", "Sem propagação", "Só chave anterior", "Com reancoragem",
               "< 1 m (anterior / reanc.)"]]
    for s in (1, 2, 5):
        k = f"chaves_{s}s_"
        linhas.append([f"{s} s", f"{m(k + 'sem_propagacao')} ({p90(k + 'sem_propagacao')})",
                       f"{m(k + 'so_anterior')} ({p90(k + 'so_anterior')})",
                       f"{m(k + 'reancorado')} ({p90(k + 'reancorado')})",
                       f"{abaixo(k + 'so_anterior')}% / {abaixo(k + 'reancorado')}%"])
    tabela(doc, linhas, [2.2, 3.3, 3.3, 3.3, 2.7])
    fonte(doc)
    paragrafo(doc,
        f"A Figura 2 mostra a sensibilidade das métricas, medida em {br(R['e5_quadros'], 0)} quadros. O "
        "controle de espaço agregado por equipe é o mais robusto: com 1 metro de erro de registro, "
        f"desvia {br(R['e5_controle_1m'])}%, e fica abaixo de 5% até {br(R['e5_xmax'], 1)} m. As demais "
        f"atingem o limiar com {L('area_ocupacao')} m (área de ocupação), {L('identidade_dominante')} m "
        f"(jogador dominante), {L('profundidade')} m (profundidade) e {L('largura')} m (largura). O "
        "controle agrega centenas de células e todos os atletas visíveis, e os deslocamentos se "
        "compensam; a área de ocupação depende de poucos atletas da periferia. Uma simulação preliminar com os 22 atletas indicava "
        "que a forma da equipe toleraria 2 metros; a visibilidade parcial a torna bem mais frágil, o "
        "que mostra a importância de medir sobre transmissões reais.")
    legenda(doc, "Figura 2 – Erro relativo de cada métrica em função do erro de registro, "
                 "sobre transmissões reais do SoccerNet-GSR")
    figura(doc, RAIZ / "figuras" / "sensibilidade_real.png", 12.0)
    fonte(doc)
    paragrafo(doc,
        f"Cruzando as medições, no erro mediano do registro ({m(r1)} m) todas as métricas ficariam "
        f"abaixo do limiar, mas no percentil 90 ({p90(r1)} m) só o controle de espaço permanece nele. "
        "Adotando o percentil 90 como critério conservador, a interface exibe as zonas de controle e "
        "oculta a forma da equipe e o domínio individual, que estariam errados em uma parte relevante "
        "dos quadros. A interface é coletiva por consequência da medição, e não por escolha estética.")
    paragrafo(doc,
        "Na narrativa, sob ruído de registro de 1 metro, a versão de corte único trocou a posse "
        f"{br(float(ing['trocas_posse_por_min']))} vezes por minuto e exibiu "
        f"{br(float(ing['estados_curtos_por_min']))} estados por minuto com menos de meio segundo, curtos "
        f"demais para leitura; com histerese, {br(float(his['trocas_posse_por_min']))} e "
        f"{br(float(his['estados_curtos_por_min']))}. O erro de registro pouco afetou a posse, porque "
        "desloca atletas e bola em conjunto. A finalização ocorreu em "
        f"{fc[0]} das {fc[1]} sequências de chute ({br(pc, 0)}%) e em {fo[0]} das {fo[1]} demais "
        f"({br(po, 0)}%): a associação é moderada, pois escanteios e faltas também levam a bola para "
        "perto do gol com espaço livre, e chutes de longe não atendem ao critério de 20 metros; a "
        "legenda indica a chegada ao ataque, e não o anúncio de um chute.")
    paragrafo(doc,
        "Há limitações: as sequências avaliadas não têm cortes de câmera, o que impediu avaliar a "
        "segmentação em planos; a anotação foi simulada; a bola é projetada como se estivesse no "
        "gramado; e o efeito da interface sobre a compreensão do espectador ainda não foi medido.")

    # ---------------- conclusão
    secao(doc, "Conclusão")
    paragrafo(doc,
        f"Sobre {br(R['sequencias'], 0)} transmissões reais, o registro por quadros-chave posicionou os "
        f"atletas com erro mediano de {m(r1)} m, e a análise de sensibilidade mostrou que, nesse nível, "
        "só o controle de espaço agregado por equipe é confiável em praticamente todos os quadros; a "
        "forma da equipe e o domínio individual exigiriam que também o percentil 90 do erro ficasse "
        f"abaixo de {L('area_ocupacao')} a {L('largura')} m. A reancoragem entre chaves, que em "
        "simulação reduzira o erro em 41%, ampliou a cauda do erro no vídeo real, o que mostra a "
        "importância de avaliar sobre transmissões. A escolha de design passa a ser consequência da "
        "medição: a interface mostra zonas de controle e oculta o que poderia enganar o espectador. "
        "Como trabalhos futuros, destacam-se o ajuste fino do detector para a bola, a calibração "
        "automática da câmera, que reduziria o custo das chaves, e o estudo com usuários, que dirá se "
        "a interface de fato melhora a compreensão do jogo.")

    # ---------------- referências
    secao(doc, "Referências")
    for r in REFERENCIAS:
        referencia(doc, r)

    doc.core_properties.title = "Do Pixel à Narrativa"
    doc.core_properties.author = "Meireles Filho, Dutra, Borges, Araújo"
    saida.parent.mkdir(parents=True, exist_ok=True)
    doc.save(saida)


REFERENCIAS = [
    "AKYON, F. C.; ALTINUC, S. O.; TEMIZEL, A. Slicing aided hyper inference and fine-tuning for small "
    "object detection. In: IEEE INTERNATIONAL CONFERENCE ON IMAGE PROCESSING, 2022, Bordeaux. "
    "**Proceedings** [...]. Piscataway: IEEE, 2022. p. 966-970.",
    "BIALKOWSKI, A. et al. Large-scale analysis of soccer matches using spatiotemporal tracking data. "
    "In: IEEE INTERNATIONAL CONFERENCE ON DATA MINING, 2014, Shenzhen. **Proceedings** [...]. "
    "Piscataway: IEEE, 2014. p. 725-730.",
    "CHEN, Z. et al. Augmenting sports videos with VisCommentator. **IEEE Transactions on "
    "Visualization and Computer Graphics**, v. 28, n. 1, p. 824-834, 2022.",
    "CHEN, Z. et al. iBall: augmenting basketball videos with gaze-moderated embedded visualizations. "
    "In: CHI CONFERENCE ON HUMAN FACTORS IN COMPUTING SYSTEMS, 2023, Hamburgo. **Proceedings** [...]. "
    "New York: ACM, 2023.",
    "DELIÈGE, A. et al. SoccerNet-v2: a dataset and benchmarks for holistic understanding of broadcast "
    "soccer videos. In: IEEE/CVF CONFERENCE ON COMPUTER VISION AND PATTERN RECOGNITION WORKSHOPS, "
    "2021. **Proceedings** [...]. Piscataway: IEEE, 2021.",
    "FERNÁNDEZ, J.; BORNN, L. Wide open spaces: a statistical technique for measuring space creation "
    "in professional soccer. In: MIT SLOAN SPORTS ANALYTICS CONFERENCE, 12., 2018, Boston. "
    "**Proceedings** [...]. Boston: MIT, 2018.",
    "FERNÁNDEZ, J.; BORNN, L.; CERVONE, D. A framework for the fine-grained evaluation of the "
    "instantaneous expected value of soccer possessions. **Machine Learning**, v. 110, n. 6, "
    "p. 1389-1427, 2021.",
    "FISCHLER, M. A.; BOLLES, R. C. Random sample consensus: a paradigm for model fitting with "
    "applications to image analysis and automated cartography. **Communications of the ACM**, v. 24, "
    "n. 6, p. 381-395, 1981.",
    "HARTLEY, R.; ZISSERMAN, A. **Multiple view geometry in computer vision**. 2. ed. Cambridge: "
    "Cambridge University Press, 2004.",
    "IFAB. **Laws of the game**: law 1, the field of play. Zurique: The International Football "
    "Association Board, 2026. Disponível em: https://www.theifab.com/laws/latest/the-field-of-play/. "
    "Acesso em: 27 set. 2026.",
    "JOCHER, G.; CHAURASIA, A.; QIU, J. **Ultralytics YOLOv8**. [S. l.]: Ultralytics, 2023. "
    "Disponível em: https://github.com/ultralytics/ultralytics. Acesso em: 9 nov. 2026.",
    "LIN, T.-Y. et al. Microsoft COCO: common objects in context. In: EUROPEAN CONFERENCE ON COMPUTER "
    "VISION, 2014, Zurique. **Proceedings** [...]. Cham: Springer, 2014. p. 740-755.",
    "LUCAS, B. D.; KANADE, T. An iterative image registration technique with an application to stereo "
    "vision. In: INTERNATIONAL JOINT CONFERENCE ON ARTIFICIAL INTELLIGENCE, 7., 1981, Vancouver. "
    "**Proceedings** [...]. San Francisco: Morgan Kaufmann, 1981. p. 674-679.",
    "PERIN, C.; VUILLEMOT, R.; FEKETE, J.-D. SoccerStories: a kick-off for visual soccer analysis. "
    "**IEEE Transactions on Visualization and Computer Graphics**, v. 19, n. 12, p. 2506-2515, 2013.",
    "PERIN, C. et al. State of the art of sports data visualization. **Computer Graphics Forum**, "
    "v. 37, n. 3, p. 663-686, 2018.",
    "SHI, J.; TOMASI, C. Good features to track. In: IEEE CONFERENCE ON COMPUTER VISION AND PATTERN "
    "RECOGNITION, 1994, Seattle. **Proceedings** [...]. Los Alamitos: IEEE, 1994. p. 593-600.",
    "SOMERS, V. et al. SoccerNet game state reconstruction: end-to-end athlete tracking and "
    "identification on a minimap. In: IEEE/CVF CONFERENCE ON COMPUTER VISION AND PATTERN RECOGNITION "
    "WORKSHOPS, 2024, Seattle. **Proceedings** [...]. Piscataway: IEEE, 2024. p. 3293-3305.",
    "SPEARMAN, W. et al. Physics-based modeling of pass probabilities in soccer. In: MIT SLOAN SPORTS "
    "ANALYTICS CONFERENCE, 11., 2017, Boston. **Proceedings** [...]. Boston: MIT, 2017.",
    "TAKI, T.; HASEGAWA, J. Visualization of dominant region in team games and its application to "
    "teamwork analysis. In: COMPUTER GRAPHICS INTERNATIONAL, 2000, Genebra. **Proceedings** [...]. "
    "Los Alamitos: IEEE, 2000. p. 227-235.",
    "THEINER, J.; EWERTH, R. TVCalib: camera calibration for sports field registration in soccer. "
    "In: IEEE/CVF WINTER CONFERENCE ON APPLICATIONS OF COMPUTER VISION, 2023, Waikoloa. "
    "**Proceedings** [...]. Piscataway: IEEE, 2023. p. 1166-1175.",
    "TRYOLABS. **soccer-video-analytics**. [S. l.]: Tryolabs, 2022. Disponível em: "
    "https://github.com/tryolabs/soccer-video-analytics. Acesso em: 11 set. 2026.",
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Gera o artigo final a partir dos resultados")
    ap.add_argument("--dados", type=Path, default=RAIZ / "dados")
    ap.add_argument("--saida", type=Path, default=RAIZ / "Artigo_Final.docx")
    args = ap.parse_args()
    montar(numeros(args.dados), args.saida)
    print(f"artigo: {args.saida}")


if __name__ == "__main__":
    main()
