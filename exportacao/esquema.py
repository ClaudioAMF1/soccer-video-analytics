"""Formato do arquivo trocado entre a extração (Python) e o player (JavaScript).

Um único JSON por clipe. Chaves curtas nos quadros porque o arquivo cresce com
o número de quadros; o significado de cada uma está documentado abaixo.

Documento::

    versao        int      versão do esquema
    origem        str      caminho do vídeo, ou "demo sintética"
    fps           float
    largura_img   int      largura do quadro, em pixels
    altura_img    int
    campo         {comprimento, largura} em metros
    equipes       [{id, nome, cor, direcao}]  direcao: +1 ataca para x crescente
    grade         {passo, nx, ny}  grade do controle de espaço; célula (i, j)
                  no índice i * ny + j, com centro em ((i+0,5)*passo, (j+0,5)*passo)
    exibicao      {visualizacao: {exibir, erro_pct, nivel, motivo}}
    quadros       lista de quadros

Quadro::

    f        índice do quadro no vídeo
    t        instante, em segundos
    H        homografia campo -> imagem (3x3), ou null se não houver registro
    j        [{id, eq, x, y, vx, vy, gk, vis}] atletas em metros e m/s;
             gk marca goleiros; vis indica se o atleta aparece no quadro
    b        {x, y} posição da bola, ou null
    posse    equipe com a posse confirmada, ou null
    portador id do atleta com a bola, ou null
    estado   estado narrativo (ver narrativa.estados)
    legenda  frase exibida ao espectador
    c        controle da equipe 0 por célula, em % inteiro (0 a 100)
    cf       fração do campo controlada pela equipe 0, em [0, 1]
"""
from __future__ import annotations

import json
from pathlib import Path

VERSAO = 1

_CHAVES_DOC = ["versao", "origem", "fps", "largura_img", "altura_img",
               "campo", "equipes", "grade", "exibicao", "quadros"]
_CHAVES_QUADRO = ["f", "t", "H", "j", "b", "posse", "portador", "estado", "legenda", "c", "cf"]
_CHAVES_ATLETA = ["id", "eq", "x", "y", "vx", "vy", "gk", "vis"]


def montar_documento(*, origem, fps, largura_img, altura_img, equipes, grade,
                     exibicao, quadros, comprimento=105.0, largura=68.0) -> dict:
    return {
        "versao": VERSAO,
        "origem": origem,
        "fps": float(fps),
        "largura_img": int(largura_img),
        "altura_img": int(altura_img),
        "campo": {"comprimento": float(comprimento), "largura": float(largura)},
        "equipes": equipes,
        "grade": grade,
        "exibicao": exibicao,
        "quadros": quadros,
    }


def validar(doc: dict) -> list[str]:
    """Lista de problemas encontrados; vazia quando o documento é válido."""
    problemas = [f"documento sem a chave '{k}'" for k in _CHAVES_DOC if k not in doc]
    if problemas:
        return problemas
    if doc["versao"] != VERSAO:
        problemas.append(f"versão {doc['versao']} não suportada (esperada {VERSAO})")

    ids_equipes = {e.get("id") for e in doc["equipes"]}
    if ids_equipes != {0, 1}:
        problemas.append("são esperadas exatamente as equipes 0 e 1")
    for e in doc["equipes"]:
        if e.get("direcao") not in (1, -1):
            problemas.append(f"equipe {e.get('id')}: direcao deve ser +1 ou -1")

    g = doc["grade"]
    n_celulas = int(g.get("nx", 0)) * int(g.get("ny", 0))
    if n_celulas <= 0:
        problemas.append("grade sem células")

    for q in doc["quadros"]:
        rot = f"quadro {q.get('f', '?')}"
        faltando = [k for k in _CHAVES_QUADRO if k not in q]
        if faltando:
            problemas.append(f"{rot}: faltam {faltando}")
            continue
        if q["H"] is not None and (len(q["H"]) != 3 or any(len(l) != 3 for l in q["H"])):
            problemas.append(f"{rot}: H deve ser 3x3")
        if len(q["c"]) != n_celulas:
            problemas.append(f"{rot}: 'c' tem {len(q['c'])} células, esperadas {n_celulas}")
        if not 0.0 <= q["cf"] <= 1.0:
            problemas.append(f"{rot}: 'cf' fora de [0, 1]")
        if q["posse"] not in (None, 0, 1):
            problemas.append(f"{rot}: posse inválida")
        for a in q["j"]:
            if any(k not in a for k in _CHAVES_ATLETA):
                problemas.append(f"{rot}: atleta com chaves faltando")
                break
        if len(problemas) > 50:
            problemas.append("(interrompido: problemas demais)")
            break
    return problemas


def salvar(doc: dict, caminho: str | Path) -> Path:
    problemas = validar(doc)
    if problemas:
        raise ValueError("documento inválido: " + "; ".join(problemas[:5]))
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return destino


def carregar(caminho: str | Path) -> dict:
    doc = json.loads(Path(caminho).read_text(encoding="utf-8"))
    problemas = validar(doc)
    if problemas:
        raise ValueError("documento inválido: " + "; ".join(problemas[:5]))
    return doc
