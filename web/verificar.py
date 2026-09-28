"""Teste de fumaça do player num navegador real (opcional; exige Playwright).

Sobe um servidor local, abre o player com a jogada de demonstração, percorre
três momentos da jogada e falha se houver erro de JavaScript ou se a página
rolar na horizontal num celular.

Uso:
    python -m exportacao.demo --saida web/dados/demo.json
    python web/verificar.py [--figura paper/figuras/prototipo.png]
"""
from __future__ import annotations

import argparse
import asyncio
import functools
import http.server
import threading
from pathlib import Path

from playwright.async_api import async_playwright

RAIZ = Path(__file__).resolve().parent


class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


async def verificar(porta: int, figura: Path | None, executavel: str | None) -> list[str]:
    problemas = []
    async with async_playwright() as p:
        navegador = await p.chromium.launch(executable_path=executavel) if executavel else await p.chromium.launch()
        # Figura para o artigo em densidade dobrada (cerca de 350 dpi impressa).
        pagina = await navegador.new_page(viewport={"width": 1440, "height": 900},
                                          device_scale_factor=2 if figura else 1)
        pagina.on("pageerror", lambda e: problemas.append(f"erro de página: {e}"))
        pagina.on("console", lambda m: problemas.append(f"console: {m.text}") if m.type == "error" else None)

        await pagina.goto(f"http://127.0.0.1:{porta}/index.html")
        await pagina.wait_for_function("document.getElementById('chip-estado').textContent !== '—'", timeout=20000)

        esperados = {60: "Construção", 150: "Ataque", 295: "Finalização"}
        for indice, chip in esperados.items():
            await pagina.evaluate(
                f"(()=>{{const r=document.getElementById('linha-tempo');r.value={indice};"
                "r.dispatchEvent(new Event('input'))})()"
            )
            obtido = await pagina.text_content("#chip-estado")
            print(f"quadro {indice}: {obtido} | {await pagina.text_content('#legenda')}")
            if obtido != chip:
                problemas.append(f"quadro {indice}: esperado {chip}, obtido {obtido}")

        if figura:
            figura.parent.mkdir(parents=True, exist_ok=True)
            await pagina.locator(".painel-video").screenshot(path=str(figura))
            print(f"figura: {figura}")

        await pagina.set_viewport_size({"width": 400, "height": 900})
        if await pagina.evaluate("document.documentElement.scrollWidth") > 400:
            problemas.append("rolagem horizontal em tela de 400 px")
        await navegador.close()
    return problemas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument("--figura", type=Path, default=None)
    ap.add_argument("--chromium", default=None, help="Caminho de um Chromium já instalado")
    args = ap.parse_args()

    manipulador = functools.partial(_Silencioso, directory=str(RAIZ))
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", args.porta), manipulador)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    try:
        problemas = asyncio.run(verificar(args.porta, args.figura, args.chromium))
    finally:
        servidor.shutdown()
    if problemas:
        raise SystemExit("FALHOU:\n  " + "\n  ".join(problemas))
    print("OK: player sem erros")


if __name__ == "__main__":
    main()
