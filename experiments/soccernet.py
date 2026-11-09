"""Leitura das anotações do SoccerNet Game State Reconstruction (SN-GSR).

Cada sequência tem 750 quadros (30 s a 25 fps) de transmissão, com a caixa de
cada atleta e da bola na imagem e a posição correspondente no campo, em metros.

O SN-GSR usa origem no centro do campo (x de -52,5 a 52,5; y de -34 a 34). Este
módulo converte para a convenção de `pitch.ModeloCampo`, com origem num canto
(x de 0 a 105; y de 0 a 68). A equipe `left` defende o gol da esquerda da
imagem e, portanto, ataca no sentido de x crescente.

Download (gratuito, sem senha, via Hugging Face):
    pip install SoccerNet
    python -c "from SoccerNet.Downloader import SoccerNetDownloader as D; \
D(LocalDirectory='data/SoccerNetGS').downloadDataTask(task='gamestate-2024', split=['test'])"
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from pitch.homografia import estimar_homografia

DESLOCAMENTO = np.array([52.5, 34.0])
EQUIPE = {"left": 0, "right": 1}
DIRECAO_ATAQUE = {0: 1, 1: -1}


@dataclass
class Atleta:
    track_id: int
    papel: str                 # player, goalkeeper, referee
    equipe: int | None         # 0 (left), 1 (right) ou None
    uv: np.ndarray             # ponto de apoio na imagem, em pixels
    xy: np.ndarray             # posição no campo, em metros
    caixa: tuple[float, float, float, float]  # x, y, w, h na imagem


@dataclass
class Quadro:
    indice: int                # 1 a 750
    atletas: list[Atleta] = field(default_factory=list)
    bola_uv: np.ndarray | None = None
    bola_xy: np.ndarray | None = None
    bola_caixa: tuple[float, float, float, float] | None = None

    def jogadores(self, com_goleiro: bool = True) -> list[Atleta]:
        papeis = ("player", "goalkeeper") if com_goleiro else ("player",)
        return [a for a in self.atletas if a.papel in papeis and a.equipe is not None]


@dataclass
class Sequencia:
    nome: str
    acao: str
    fps: float
    largura: int
    altura: int
    quadros: list[Quadro]
    pasta: Path

    def imagem(self, indice: int) -> Path:
        return self.pasta / "img1" / f"{indice:06d}.jpg"


def _para_campo(x: float, y: float) -> np.ndarray:
    return np.array([x, y], dtype=float) + DESLOCAMENTO


def carregar(caminho: str | Path) -> Sequencia:
    """Lê `Labels-GameState.json` de uma sequência."""
    caminho = Path(caminho)
    arquivo = caminho / "Labels-GameState.json" if caminho.is_dir() else caminho
    d = json.loads(arquivo.read_text(encoding="utf-8"))
    info = d["info"]

    ordem = {img["image_id"]: int(img["file_name"][:-4]) for img in d["images"]}
    quadros = {i: Quadro(i) for i in sorted(ordem.values())}
    dims = d["images"][0]

    for a in d["annotations"]:
        if a.get("supercategory") != "object" or not a.get("bbox_pitch") or not a.get("bbox_image"):
            continue
        q = quadros[ordem[a["image_id"]]]
        bi, bp = a["bbox_image"], a["bbox_pitch"]
        uv = np.array([bi["x_center"], bi["y"] + bi["h"]], dtype=float)
        xy = _para_campo(bp["x_bottom_middle"], bp["y_bottom_middle"])
        caixa = (float(bi["x"]), float(bi["y"]), float(bi["w"]), float(bi["h"]))
        papel = a["attributes"]["role"]
        if papel == "ball":
            q.bola_uv, q.bola_xy, q.bola_caixa = uv, xy, caixa
        elif papel in ("player", "goalkeeper", "referee"):
            eq = EQUIPE.get(a["attributes"].get("team"))
            q.atletas.append(Atleta(int(a["track_id"]), papel, eq, uv, xy, caixa))

    return Sequencia(
        nome=info["name"], acao=info.get("action_class", ""),
        fps=float(info.get("frame_rate", 25)), largura=int(dims["width"]),
        altura=int(dims["height"]), quadros=[quadros[k] for k in sorted(quadros)],
        pasta=arquivo.parent,
    )


def homografia_referencia(quadro: Quadro, minimo: int = 6) -> np.ndarray | None:
    """Homografia imagem -> campo ajustada às posições anotadas do próprio quadro.

    Serve de gabarito do registro: as posições do SN-GSR derivam da calibração
    anotada da câmera, e o resíduo do ajuste sobre elas é de cerca de 0,1 m.
    """
    pontos = [a for a in quadro.atletas if a.papel in ("player", "goalkeeper", "referee")]
    if len(pontos) < minimo:
        return None
    uv = np.array([a.uv for a in pontos])
    xy = np.array([a.xy for a in pontos])
    try:
        return estimar_homografia(uv, xy)
    except (ValueError, np.linalg.LinAlgError):
        return None


def listar(raiz: str | Path) -> list[Path]:
    """Pastas de sequência (SNGS-*) sob `raiz`."""
    return sorted(p for p in Path(raiz).glob("SNGS-*") if (p / "Labels-GameState.json").exists())
