"""Testes do leitor do SN-GSR e da seleção de marcos visíveis, com dados sintéticos."""
import json

import numpy as np

from experiments.e5_real import marcos_visiveis
from experiments.soccernet import carregar, homografia_referencia
from exportacao.demo import camera
from pitch import projetar

H_CI = camera(52.5, 1500.0)          # campo -> imagem (1280 x 720)
H_IC = np.linalg.inv(H_CI)


def _para_img(xy):
    h = H_CI @ np.array([xy[0], xy[1], 1.0])
    return h[:2] / h[2]


def _json(tmp_path):
    atletas = [(1, "player", "left", (40, 20)), (2, "player", "left", (45, 40)),
               (3, "player", "right", (60, 25)), (4, "player", "right", (58, 45)),
               (5, "goalkeeper", "right", (70, 34)), (6, "referee", None, (50, 30)),
               (7, "player", "left", (35, 50))]
    anns = []
    for tid, papel, eq, (x, y) in atletas + [(9, "ball", None, (52, 33))]:
        u, v = _para_img((x, y))
        anns.append({
            "image_id": "1", "track_id": tid, "supercategory": "object",
            "category_id": 4 if papel == "ball" else 1,
            "attributes": {"role": papel, "team": eq, "jersey": None},
            "bbox_image": {"x": u - 10, "y": v - 40, "x_center": u, "y_center": v - 20, "w": 20, "h": 40},
            "bbox_pitch": {"x_bottom_middle": x - 52.5, "y_bottom_middle": y - 34.0},
        })
    anns.append({"image_id": "1", "supercategory": "pitch", "category_id": 5, "lines": {}})
    d = {"info": {"name": "SNGS-T", "action_class": "Goal", "frame_rate": 25},
         "images": [{"image_id": "1", "file_name": "000001.jpg", "width": 1280, "height": 720}],
         "annotations": anns, "categories": []}
    pasta = tmp_path / "SNGS-T"
    pasta.mkdir()
    (pasta / "Labels-GameState.json").write_text(json.dumps(d))
    return pasta


def test_leitura_converte_coordenadas_e_papeis(tmp_path):
    seq = carregar(_json(tmp_path))
    q = seq.quadros[0]
    assert seq.nome == "SNGS-T" and seq.acao == "Goal" and len(seq.quadros) == 1
    assert np.allclose(q.bola_xy, [52, 33])
    assert {a.papel for a in q.atletas} == {"player", "goalkeeper", "referee"}
    assert len(q.jogadores()) == 6 and len(q.jogadores(com_goleiro=False)) == 5
    assert {a.equipe for a in q.jogadores()} == {0, 1}


def test_homografia_de_referencia_reproduz_as_posicoes(tmp_path):
    q = carregar(_json(tmp_path)).quadros[0]
    H = homografia_referencia(q)
    uv = np.array([a.uv for a in q.atletas])
    xy = np.array([a.xy for a in q.atletas])
    assert np.abs(projetar(H, uv) - xy).max() < 1e-6


def test_marcos_visiveis_ficam_dentro_do_quadro(tmp_path):
    q = carregar(_json(tmp_path)).quadros[0]
    uv, xy = marcos_visiveis(H_IC, 1280, 720, np.array([a.uv for a in q.atletas]))
    assert len(uv) >= 4
    assert (uv[:, 0] >= 0).all() and (uv[:, 0] <= 1280).all()
    assert (uv[:, 1] >= 0).all() and (uv[:, 1] <= 720).all()
    assert np.abs(projetar(H_IC, uv) - xy).max() < 1e-6
