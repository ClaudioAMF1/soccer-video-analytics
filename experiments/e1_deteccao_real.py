"""E1 sobre transmissões reais: o detector pré-treinado encontra atletas e bola?

Avalia o YOLOv8 com pesos COCO, tal como usado pelo pipeline (classe `person`
com confiança mínima de 0,40; `sports ball` com 0,15), contra as caixas
anotadas no SN-GSR. Três perguntas:

1. **Atletas.** Quantos são encontrados (revocação), em função do tamanho na
   imagem, e quantas detecções são de fato atletas (precisão)?
2. **Filtro pelo campo.** O detector também encontra torcedores, gandulas e
   comissão técnica. Descartar as detecções cujo ponto de apoio, projetado pela
   homografia, cai fora do gramado (com 3 m de tolerância) recupera a precisão?
3. **Bola.** Em que fração dos quadros a bola mais confiante coincide com a
   anotada, com o quadro inteiro e com inferência fatiada (Akyon et al., 2022)?

Uso:
    python -m experiments.e1_deteccao_real --dados data/SoccerNetGS/test \\
        --modelo yolov8x.pt --saida resultados/
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np

from experiments.soccernet import carregar, homografia_referencia, listar
from pitch import ModeloCampo, projetar

CONF_PESSOA, CONF_BOLA = 0.40, 0.15
IOU_MIN = 0.5
DIST_BOLA_PX = 15.0
MARGEM_CAMPO_M = 3.0
PEQUENO_PX = 60       # altura da caixa abaixo da qual o atleta é "pequeno"


def iou(a, b) -> float:
    ax2, ay2, bx2, by2 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw = max(0.0, min(ax2, bx2) - max(a[0], b[0]))
    ih = max(0.0, min(ay2, by2) - max(a[1], b[1]))
    inter = iw * ih
    return inter / (a[2] * a[3] + b[2] * b[3] - inter + 1e-9)


def casar(gt: list, pred: list) -> tuple[list[bool], list[bool]]:
    """Casamento guloso por IoU. Retorna (gt encontrado?, predição correta?)."""
    pares = sorted(((iou(g, p), i, j) for i, g in enumerate(gt) for j, p in enumerate(pred)), reverse=True)
    achado, certo = [False] * len(gt), [False] * len(pred)
    for v, i, j in pares:
        if v < IOU_MIN:
            break
        if not achado[i] and not certo[j]:
            achado[i] = certo[j] = True
    return achado, certo


def detectar(modelo, img, imgsz: int, fatiado: bool):
    """Lista de (classe, conf, x, y, w, h). Fatiado: 2x2 recortes com 20 % de sobreposição."""
    import torch
    from torchvision.ops import batched_nms

    if not fatiado:
        r = modelo(img, imgsz=imgsz, conf=0.1, classes=[0, 32], verbose=False)[0]
        b = r.boxes
        xyxy, conf, cls = b.xyxy.numpy(), b.conf.numpy(), b.cls.numpy()
    else:
        h, w = img.shape[:2]
        tw, th = int(w * 0.6), int(h * 0.6)
        caixas, confs, classes = [], [], []
        for x0 in (0, w - tw):
            for y0 in (0, h - th):
                r = modelo(img[y0:y0 + th, x0:x0 + tw], imgsz=imgsz, conf=0.1, classes=[0, 32], verbose=False)[0]
                if len(r.boxes):
                    caixas.append(r.boxes.xyxy.numpy() + [x0, y0, x0, y0])
                    confs.append(r.boxes.conf.numpy())
                    classes.append(r.boxes.cls.numpy())
        r = modelo(img, imgsz=imgsz, conf=0.1, classes=[0, 32], verbose=False)[0]
        caixas.append(r.boxes.xyxy.numpy()); confs.append(r.boxes.conf.numpy()); classes.append(r.boxes.cls.numpy())
        xyxy, conf, cls = np.concatenate(caixas), np.concatenate(confs), np.concatenate(classes)
        if len(xyxy):
            manter = batched_nms(torch.tensor(xyxy, dtype=torch.float32), torch.tensor(conf, dtype=torch.float32),
                                 torch.tensor(cls), 0.5).numpy()
            xyxy, conf, cls = xyxy[manter], conf[manter], cls[manter]
    return [(int(c), float(s), x1, y1, x2 - x1, y2 - y1) for (x1, y1, x2, y2), s, c in zip(xyxy, conf, cls)]


def main() -> None:
    import cv2
    from ultralytics import YOLO

    ap = argparse.ArgumentParser(description="E1 sobre o SN-GSR")
    ap.add_argument("--dados", type=Path, required=True)
    ap.add_argument("--modelo", default="yolov8x.pt")
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--passo", type=int, default=75, help="1 quadro a cada N (75 = 3 s)")
    ap.add_argument("--passo-fatiado", type=int, default=150, help="1 quadro a cada N para a inferência fatiada")
    ap.add_argument("--saida", type=Path, default=Path("resultados"))
    args = ap.parse_args()

    modelo = YOLO(args.modelo)
    campo = ModeloCampo()
    chaves = ("gt", "gt_peq", "achados", "achados_peq", "pred", "pred_ok", "pred_campo",
              "pred_campo_ok", "quadros", "bola_gt", "bola_ok", "bola_fat_gt", "bola_fat_ok",
              "bola_inteiro_mesmos_ok")
    total = {k: 0 for k in chaves}
    tamanhos_bola = []
    t0 = time.time()
    # Resultado parcial por sequência: uma execução interrompida é retomada
    # sem reprocessar o que já foi feito.
    cache = args.saida / "e1_cache"
    cache.mkdir(parents=True, exist_ok=True)

    for pasta in [p for p in listar(args.dados) if (p / "img1").exists()]:
        arquivo = cache / f"{pasta.name}.json"
        if arquivo.exists():
            parcial = json.loads(arquivo.read_text())
            for k in chaves:
                total[k] += parcial[k]
            tamanhos_bola += parcial["tamanhos_bola"]
            continue
        seq = carregar(pasta)
        cont = {k: 0 for k in chaves}
        tam_seq = []
        for q in seq.quadros[::args.passo]:
            img = cv2.imread(str(seq.imagem(q.indice)))
            if img is None:
                continue
            cont["quadros"] += 1
            det = detectar(modelo, img, args.imgsz, False)

            gt = [a.caixa for a in q.atletas]
            pred = [d[2:] for d in det if d[0] == 0 and d[1] >= CONF_PESSOA]
            achado, certo = casar(gt, pred)
            cont["gt"] += len(gt); cont["achados"] += sum(achado)
            for g, a in zip(gt, achado):
                if g[3] < PEQUENO_PX:
                    cont["gt_peq"] += 1; cont["achados_peq"] += a
            cont["pred"] += len(pred); cont["pred_ok"] += sum(certo)

            H = homografia_referencia(q)
            if H is not None and pred:
                apoio = np.array([[p[0] + p[2] / 2, p[1] + p[3]] for p in pred])
                no_campo = campo.dentro(projetar(H, apoio), margem=MARGEM_CAMPO_M)
                cont["pred_campo"] += int(no_campo.sum())
                cont["pred_campo_ok"] += int(np.array(certo)[no_campo].sum())

            def acerta_bola(dets):
                bolas = [d for d in dets if d[0] == 32 and d[1] >= CONF_BOLA]
                if not bolas:
                    return False
                b = max(bolas, key=lambda d: d[1])
                cx, cy = b[2] + b[4] / 2, b[3] + b[5] / 2
                gx, gy, gw, gh = q.bola_caixa
                return np.hypot(cx - gx - gw / 2, cy - gy - gh / 2) <= max(DIST_BOLA_PX, gw)

            if q.bola_caixa is not None:
                tam_seq.append(max(q.bola_caixa[2], q.bola_caixa[3]))
                cont["bola_gt"] += 1
                ok = acerta_bola(det)
                cont["bola_ok"] += ok
                if (q.indice - 1) % args.passo_fatiado == 0:
                    cont["bola_fat_gt"] += 1
                    cont["bola_inteiro_mesmos_ok"] += ok
                    cont["bola_fat_ok"] += acerta_bola(detectar(modelo, img, args.imgsz, True))
        cont = {k: int(v) for k, v in cont.items()}
        arquivo.write_text(json.dumps({**cont, "tamanhos_bola": tam_seq}))
        for k in chaves:
            total[k] += cont[k]
        tamanhos_bola += tam_seq
        print(f"  {seq.nome}: {total['quadros']} quadros, {time.time() - t0:.0f}s", flush=True)

    cont = total

    pct = lambda a, b: round(100.0 * a / b, 1) if b else None
    linhas = [
        {"medida": "revocacao_atletas", "valor_pct": pct(cont["achados"], cont["gt"]), "n": cont["gt"]},
        {"medida": "revocacao_atletas_pequenos", "valor_pct": pct(cont["achados_peq"], cont["gt_peq"]), "n": cont["gt_peq"]},
        {"medida": "precisao_pessoas_sem_filtro", "valor_pct": pct(cont["pred_ok"], cont["pred"]), "n": cont["pred"]},
        {"medida": "precisao_pessoas_filtro_campo", "valor_pct": pct(cont["pred_campo_ok"], cont["pred_campo"]), "n": cont["pred_campo"]},
        {"medida": "bola_localizada_quadro_inteiro", "valor_pct": pct(cont["bola_ok"], cont["bola_gt"]), "n": cont["bola_gt"]},
        {"medida": "bola_localizada_inteiro_subamostra", "valor_pct": pct(cont["bola_inteiro_mesmos_ok"], cont["bola_fat_gt"]), "n": cont["bola_fat_gt"]},
        {"medida": "bola_localizada_fatiado_subamostra", "valor_pct": pct(cont["bola_fat_ok"], cont["bola_fat_gt"]), "n": cont["bola_fat_gt"]},
        {"medida": "tamanho_mediano_bola_px", "valor_pct": float(np.median(tamanhos_bola)) if tamanhos_bola else None, "n": len(tamanhos_bola)},
    ]
    args.saida.mkdir(parents=True, exist_ok=True)
    with (args.saida / "e1_deteccao_real.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["medida", "valor_pct", "n"])
        w.writeheader()
        w.writerows(linhas)
    print(f"\n{cont['quadros']} quadros")
    for l in linhas:
        print(l)


if __name__ == "__main__":
    main()
