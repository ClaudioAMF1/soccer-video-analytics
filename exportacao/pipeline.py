"""Segunda passada da extração: de medições na imagem a dados no campo.

A primeira passada (`extrair.py`) percorre o vídeo gravado com detector,
rastreador e estimador de movimento de câmera, e guarda para cada quadro apenas
medições em pixels. Esta segunda passada é determinística e não depende de
nenhum modelo de aprendizado, o que permite testá-la com dados sintéticos:

1. estima a homografia de cada quadro a partir dos quadros-chave anotados;
2. projeta atletas e bola para o campo, em metros;
3. estima velocidades por trajetória suavizada;
4. decide a posse (com a mesma máquina de estados de `soccer.partida`);
5. calcula o controle de espaço e o estado narrativo;
6. monta o documento no formato de `exportacao.esquema`.

Só o que é necessário ao processamento offline justifica duas passadas: a
reancoragem de um quadro depende da chave *seguinte*, ainda não vista na
primeira passada.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import savgol_filter

from controle import ParametrosMovimento, controle_por_equipe
from narrativa import MaquinaNarrativa, ParametrosNarrativa, legenda
from pitch import ModeloCampo, RegistroPorChaves, estimar_homografia, projetar
from soccer.partida import Partida
from soccer.time import Time

JANELA_SUAVIZACAO = 9  # quadros; ~0,36 s a 25 fps


@dataclass
class QuadroBruto:
    """Medições de um quadro, em pixels, produzidas pela primeira passada.

    atletas: lista de (id, equipe ou None, u, v, goleiro), com (u, v) no ponto
        de apoio (meio da aresta inferior da caixa delimitadora).
    bola: (u, v) ou None.
    movimento: 3x3, imagem deste quadro -> referência absoluta da câmera.
    """

    f: int
    atletas: list[tuple[int, int | None, float, float, bool]]
    bola: tuple[float, float] | None
    movimento: np.ndarray = field(default_factory=lambda: np.eye(3))


def anotacoes_para_chaves(anotacoes: dict, modelo: ModeloCampo | None = None) -> dict[int, np.ndarray]:
    """Converte anotações manuais em homografias de quadro-chave.

    Formato esperado (o mesmo de `exemplos/anotacoes_exemplo.json`)::

        {"0":   {"canto_inf_esq": [u, v], "ga_esq_sup_frente": [u, v], ...},
         "250": {...}}

    Os nomes são os marcos de `ModeloCampo.marcos()`. São necessários ao menos
    quatro por quadro; seis ou mais, bem espalhados, tornam a estimativa estável.
    """
    modelo = modelo or ModeloCampo()
    marcos = modelo.marcos()
    chaves = {}
    for quadro, pontos in anotacoes.items():
        desconhecidos = [n for n in pontos if n not in marcos]
        if desconhecidos:
            raise KeyError(f"quadro {quadro}: marcos desconhecidos {desconhecidos}")
        if len(pontos) < 4:
            raise ValueError(f"quadro {quadro}: são necessários ao menos 4 marcos, há {len(pontos)}")
        nomes = list(pontos)
        img = np.array([pontos[n] for n in nomes], dtype=float)
        campo = np.array([marcos[n] for n in nomes], dtype=float)
        chaves[int(quadro)] = estimar_homografia(img, campo)
    return chaves


def _velocidades(trajetorias: dict[int, list[tuple[int, float, float]]], fps: float) -> dict:
    """(id, quadro) -> (vx, vy) em m/s, por diferenciação suavizada.

    A posição projetada oscila de um quadro para o outro porque a caixa
    delimitadora oscila; derivar o sinal bruto amplificaria esse ruído. O filtro
    de Savitzky-Golay ajusta um polinômio local e deriva o polinômio.
    """
    saida = {}
    for ident, pontos in trajetorias.items():
        pontos = sorted(pontos)
        # Trechos contíguos: uma lacuna no rastreamento não pode ser derivada.
        trechos, atual = [], [pontos[0]]
        for p in pontos[1:]:
            if p[0] == atual[-1][0] + 1:
                atual.append(p)
            else:
                trechos.append(atual)
                atual = [p]
        trechos.append(atual)

        for trecho in trechos:
            quadros = [p[0] for p in trecho]
            xy = np.array([[p[1], p[2]] for p in trecho])
            if len(trecho) >= JANELA_SUAVIZACAO:
                v = savgol_filter(xy, JANELA_SUAVIZACAO, 2, deriv=1, delta=1.0 / fps, axis=0)
            elif len(trecho) >= 2:
                v = np.gradient(xy, 1.0 / fps, axis=0)
            else:
                v = np.zeros_like(xy)
            for q, (vx, vy) in zip(quadros, v):
                saida[(ident, q)] = (float(vx), float(vy))
    return saida


class _AtletaCampo:
    """Adaptador: expõe um atleta já projetado à interface de `Partida`."""

    def __init__(self, ident, time, distancia):
        self.ident = ident
        self.time = time
        self.detection = True
        self._distancia = distancia

    def distancia_para_bola(self, bola, homografia=None):
        return self._distancia


class _BolaCampo:
    def __init__(self, presente):
        self.detection = True if presente else None
        self.centro = (0.0, 0.0) if presente else None


def montar_exportacao(
    brutos: list[QuadroBruto],
    anotacoes: dict,
    *,
    fps: float,
    largura_img: int,
    altura_img: int,
    equipes: list[dict],
    exibicao: dict,
    origem: str,
    passo_grade: float = 3.0,
    par_movimento: ParametrosMovimento | None = None,
    par_narrativa: ParametrosNarrativa | None = None,
    reancorar: bool = True,
) -> dict:
    """Produz o documento de exportação a partir das medições em pixels."""
    from .esquema import montar_documento

    if not brutos:
        raise ValueError("nenhum quadro para exportar")

    modelo = ModeloCampo()
    grade = modelo.grade(passo_grade)
    nx, ny = modelo.formato_grade(passo_grade)
    par_mov = par_movimento or ParametrosMovimento()

    por_quadro = {b.f: b for b in brutos}
    registro = RegistroPorChaves(
        anotacoes_para_chaves(anotacoes, modelo),
        lambda f: por_quadro[f].movimento,
        largura_img, altura_img,
    )

    # --- 1-2. Registro e projeção --------------------------------------- #
    projetados, homografias, trajetorias = {}, {}, {}
    for b in brutos:
        H = registro.homografia(b.f, reancorar=reancorar)
        homografias[b.f] = H
        atletas = []
        for ident, eq, u, v, gk in b.atletas:
            x, y = projetar(H, np.array([u, v]))[0]
            if not np.isfinite([x, y]).all():
                continue
            vis = 0.0 <= u <= largura_img and 0.0 <= v <= altura_img
            atletas.append((ident, eq, float(x), float(y), bool(gk), bool(vis)))
            trajetorias.setdefault(ident, []).append((b.f, float(x), float(y)))
        bola = None
        if b.bola is not None:
            bx, by = projetar(H, np.array(b.bola))[0]
            if np.isfinite([bx, by]).all():
                bola = np.array([bx, by])
        projetados[b.f] = (atletas, bola)

    # --- 3. Velocidades -------------------------------------------------- #
    velocidades = _velocidades(trajetorias, fps)

    # --- 4-5. Posse, controle e narrativa -------------------------------- #
    times = [Time(e["nome"], e["nome"][:3].upper(), (0, 0, 0)) for e in sorted(equipes, key=lambda e: e["id"])]
    id_do_time = {id(t): i for i, t in enumerate(times)}
    partida = Partida(times[0], times[1], fps=fps, em_metros=True)
    maquina = MaquinaNarrativa({e["id"]: e["direcao"] for e in equipes}, par_narrativa)
    nomes = {e["id"]: e["nome"] for e in equipes}

    quadros = []
    for b in brutos:
        atletas, bola = projetados[b.f]
        t = b.f / fps

        adaptados = []
        for ident, eq, x, y, _, _ in atletas:
            if eq is None:
                continue
            d = float(np.hypot(x - bola[0], y - bola[1])) if bola is not None else float("inf")
            adaptados.append(_AtletaCampo(ident, times[eq], d))
        partida.atualizar(adaptados, _BolaCampo(bola is not None))
        posse = id_do_time[id(partida.time_com_posse)] if partida.time_com_posse else None
        portador = partida.jogador_mais_proximo.ident if partida.jogador_mais_proximo else None

        classificados = [a for a in atletas if a[1] is not None]
        if classificados:
            pos = np.array([[a[2], a[3]] for a in classificados])
            vel = np.array([velocidades.get((a[0], b.f), (0.0, 0.0)) for a in classificados])
            eqs = np.array([a[1] for a in classificados])
            controle = controle_por_equipe(pos, vel, eqs, grade, 0, par_mov)
        else:
            controle = np.full(len(grade), 0.5)
        cf = float(controle.mean())

        if posse is not None:
            adversarios = np.array([[a[2], a[3]] for a in classificados if a[1] != posse]).reshape(-1, 2)
        else:
            adversarios = None
        estado = maquina.atualizar(t, posse, bola, adversarios)
        eq_narrada = maquina.equipe
        frac_narrada = None if eq_narrada is None else (cf if eq_narrada == 0 else 1.0 - cf)

        H_campo_img = np.linalg.inv(homografias[b.f])
        H_campo_img = H_campo_img / H_campo_img[2, 2]

        quadros.append({
            "f": b.f,
            "t": round(t, 3),
            "H": [[round(float(v), 8) for v in linha] for linha in H_campo_img],
            "j": [{
                "id": ident, "eq": eq, "x": round(x, 2), "y": round(y, 2),
                "vx": round(velocidades.get((ident, b.f), (0.0, 0.0))[0], 2),
                "vy": round(velocidades.get((ident, b.f), (0.0, 0.0))[1], 2),
                "gk": gk, "vis": vis,
            } for ident, eq, x, y, gk, vis in atletas],
            "b": None if bola is None else {"x": round(float(bola[0]), 2), "y": round(float(bola[1]), 2)},
            "posse": posse,
            "portador": portador,
            "estado": estado.value,
            "legenda": legenda(estado, nomes.get(eq_narrada), frac_narrada),
            "c": [int(round(v * 100)) for v in controle],
            "cf": round(cf, 4),
        })

    return montar_documento(
        origem=origem, fps=fps, largura_img=largura_img, altura_img=altura_img,
        equipes=equipes, grade={"passo": passo_grade, "nx": nx, "ny": ny},
        exibicao=exibicao, quadros=quadros,
    )
