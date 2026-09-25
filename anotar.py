"""Anotação manual de quadros-chave para o registro do campo.

Abre cada quadro pedido e percorre os marcos do campo: clique sobre o marco
indicado na barra de título, ou tecle ESPAÇO se ele não estiver visível.
Tecle ENTER para encerrar o quadro atual (exige ao menos 4 marcos; seis ou
mais, bem espalhados, dão uma homografia estável). Tecle Z para desfazer.

Uso:
    python anotar.py --video jogo.mp4 --quadros 0,250,500 --saida anotacoes.json

Escolha quadros-chave a cada 5 a 10 segundos e sempre que a câmera fizer um
movimento brusco ou um corte. A deriva entre chaves é medida no experimento E2.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from pitch import ModeloCampo

JANELA = "anotar"
MIN_MARCOS = 4


def anotar_quadro(imagem, nomes: list[str]) -> dict[str, list[float]]:
    pontos: dict[str, list[float]] = {}
    ordem: list[str] = []
    estado = {"i": 0, "clique": None}

    def ao_clicar(evento, x, y, *_):
        if evento == cv2.EVENT_LBUTTONDOWN:
            estado["clique"] = (float(x), float(y))

    cv2.setMouseCallback(JANELA, ao_clicar)
    while estado["i"] < len(nomes):
        nome = nomes[estado["i"]]
        tela = imagem.copy()
        for n, (u, v) in pontos.items():
            cv2.circle(tela, (int(u), int(v)), 5, (0, 255, 255), -1)
            cv2.putText(tela, n, (int(u) + 6, int(v) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
        cv2.setWindowTitle(JANELA, f"Marco: {nome}  |  clique = marcar, ESPACO = pular, "
                                   f"Z = desfazer, ENTER = concluir ({len(pontos)} marcados)")
        cv2.imshow(JANELA, tela)
        tecla = cv2.waitKey(30) & 0xFF

        if estado["clique"] is not None:
            pontos[nome] = list(estado["clique"])
            ordem.append(nome)
            estado["clique"] = None
            estado["i"] += 1
        elif tecla == ord(" "):
            estado["i"] += 1
        elif tecla in (ord("z"), ord("Z")) and ordem:
            desfeito = ordem.pop()
            pontos.pop(desfeito, None)
            estado["i"] = nomes.index(desfeito)
        elif tecla in (13, 10):
            if len(pontos) >= MIN_MARCOS:
                break
            print(f"São necessários ao menos {MIN_MARCOS} marcos; há {len(pontos)}.")
    return pontos


def main() -> None:
    p = argparse.ArgumentParser(description="Anota quadros-chave para o registro do campo")
    p.add_argument("--video", required=True)
    p.add_argument("--quadros", required=True, help="Índices separados por vírgula, ex.: 0,250,500")
    p.add_argument("--saida", required=True, type=Path)
    args = p.parse_args()

    nomes = list(ModeloCampo().marcos().keys())
    anotacoes = json.loads(args.saida.read_text(encoding="utf-8")) if args.saida.exists() else {}

    captura = cv2.VideoCapture(args.video)
    cv2.namedWindow(JANELA, cv2.WINDOW_NORMAL)
    for q in [int(x) for x in args.quadros.split(",")]:
        captura.set(cv2.CAP_PROP_POS_FRAMES, q)
        ok, imagem = captura.read()
        if not ok:
            print(f"Quadro {q} não pôde ser lido; ignorado.")
            continue
        pontos = anotar_quadro(imagem, nomes)
        if len(pontos) >= MIN_MARCOS:
            anotacoes[str(q)] = pontos
            args.saida.write_text(json.dumps(anotacoes, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Quadro {q}: {len(pontos)} marcos gravados em {args.saida}")
    captura.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
