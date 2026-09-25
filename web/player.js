/* Player narrativo: lê o JSON da extração e desenha sobre o vídeo gravado.
 *
 * Duas vistas do mesmo quadro:
 *  - transmissão: o vídeo (se aberto) com as camadas projetadas pela
 *    homografia campo -> imagem de cada quadro; sem vídeo, o gramado é
 *    desenhado em perspectiva a partir da mesma homografia;
 *  - visto de cima: o campo em escala, em metros.
 * Nenhum cálculo tático é feito aqui: tudo vem pronto do arquivo.
 */
(() => {
  "use strict";

  const NOMES_ESTADO = {
    bola_morta: "Bola parada", disputa: "Disputa", construcao: "Construção",
    ataque: "Ataque", transicao: "Transição", finalizacao: "Finalização",
  };
  const NOMES_VIS = {
    zonas_de_controle: "Zonas de controle",
    forma_da_equipe: "Forma da equipe",
    distancia_entre_linhas: "Distância entre as equipes",
    dominio_individual: "Qual jogador domina cada ponto",
  };
  const CAMADA_DA_VIS = { zonas_de_controle: "camada-zonas", forma_da_equipe: "camada-forma" };

  const $ = (id) => document.getElementById(id);
  const telaTx = $("tela-transmissao"), ctxTx = telaTx.getContext("2d");
  const telaMapa = $("tela-mapa"), ctxMapa = telaMapa.getContext("2d");
  const video = $("video");

  const MARGEM = 30, ESCALA = 10; // mapa: 10 px por metro
  // Modo de estudo (?estudo na URL): a legenda omite o percentual de controle,
  // para que nenhuma pergunta do estudo possa ser respondida lendo um número
  // da tela (ver estudo/PROTOCOLO.md).
  const MODO_ESTUDO = new URLSearchParams(location.search).has("estudo");
  const semPercentual = (t) => t.replace(/\s*\S+ controla \d+% do campo\./, "");
  let doc = null, indice = 0, tocando = false, ultimoTs = null, acumulado = 0, comVideo = false;

  // ---------------------------------------------------------------- geometria
  function projetar(H, x, y) {
    const w = H[2][0] * x + H[2][1] * y + H[2][2];
    if (w <= 1e-9) return null; // atrás da câmera
    return [(H[0][0] * x + H[0][1] * y + H[0][2]) / w, (H[1][0] * x + H[1][1] * y + H[1][2]) / w];
  }
  const noMapa = (x, y) => [MARGEM + x * ESCALA, MARGEM + (doc.campo.largura - y) * ESCALA];

  function cascoConvexo(pts) {
    if (pts.length < 3) return pts.slice();
    const p = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const cruz = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const inf = [], sup = [];
    for (const q of p) { while (inf.length >= 2 && cruz(inf[inf.length - 2], inf[inf.length - 1], q) <= 0) inf.pop(); inf.push(q); }
    for (let i = p.length - 1; i >= 0; i--) { const q = p[i]; while (sup.length >= 2 && cruz(sup[sup.length - 2], sup[sup.length - 1], q) <= 0) sup.pop(); sup.push(q); }
    sup.pop(); inf.pop();
    return inf.concat(sup);
  }

  function linhasDoCampo() {
    const C = doc.campo.comprimento, L = doc.campo.largura, m = L / 2;
    const arco = (cx, cy, r, a0, a1, n = 40) =>
      Array.from({ length: n + 1 }, (_, i) => { const a = a0 + (a1 - a0) * i / n; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; });
    const ga = 40.32 / 2, pa = 18.32 / 2, ab = Math.acos(5.5 / 9.15);
    return [
      [[0, 0], [C, 0], [C, L], [0, L], [0, 0]],
      [[C / 2, 0], [C / 2, L]],
      arco(C / 2, m, 9.15, 0, 2 * Math.PI, 64),
      [[0, m - ga], [16.5, m - ga], [16.5, m + ga], [0, m + ga]],
      [[C, m - ga], [C - 16.5, m - ga], [C - 16.5, m + ga], [C, m + ga]],
      [[0, m - pa], [5.5, m - pa], [5.5, m + pa], [0, m + pa]],
      [[C, m - pa], [C - 5.5, m - pa], [C - 5.5, m + pa], [C, m + pa]],
      arco(11, m, 9.15, -ab, ab),
      arco(C - 11, m, 9.15, Math.PI - ab, Math.PI + ab),
    ];
  }

  // ---------------------------------------------------------------- desenho
  function tracar(ctx, pontosCampo, paraTela) {
    ctx.beginPath();
    let aberto = false;
    for (const [x, y] of pontosCampo) {
      const p = paraTela(x, y);
      if (!p) { aberto = false; continue; }
      if (aberto) ctx.lineTo(p[0], p[1]); else { ctx.moveTo(p[0], p[1]); aberto = true; }
    }
  }

  function hexRgba(hex, a) {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
  }

  function desenharZonas(ctx, q, paraTela) {
    const { passo, nx, ny } = doc.grade;
    const L = doc.campo.largura, C = doc.campo.comprimento;
    const [e0, e1] = doc.equipes;
    for (let i = 0; i < nx; i++) {
      for (let j = 0; j < ny; j++) {
        const t = (q.c[i * ny + j] - 50) / 50;
        if (Math.abs(t) < 0.08) continue;
        const x0 = i * passo, x1 = Math.min(C, x0 + passo), y0 = j * passo, y1 = Math.min(L, y0 + passo);
        tracar(ctx, [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]], paraTela);
        ctx.fillStyle = hexRgba(t > 0 ? e0.cor : e1.cor, Math.min(0.55, Math.abs(t) * 0.55));
        ctx.fill();
      }
    }
  }

  function desenharForma(ctx, q, paraTela, espessura) {
    for (const eq of doc.equipes) {
      const pts = q.j.filter((a) => a.eq === eq.id && !a.gk && a.vis).map((a) => [a.x, a.y]);
      if (pts.length < 3) continue;
      const casco = cascoConvexo(pts);
      tracar(ctx, casco.concat([casco[0]]), paraTela);
      ctx.fillStyle = hexRgba(eq.cor, 0.12); ctx.fill();
      ctx.strokeStyle = eq.cor; ctx.lineWidth = espessura; ctx.stroke();
    }
  }

  function desenharAtletas(ctx, q, paraTela, raio, mostrarInvisiveis) {
    const cor = Object.fromEntries(doc.equipes.map((e) => [e.id, e.cor]));
    for (const a of q.j) {
      if (!a.vis && !mostrarInvisiveis) continue;
      const p = paraTela(a.x, a.y); if (!p) continue;
      ctx.beginPath(); ctx.arc(p[0], p[1], raio, 0, 2 * Math.PI);
      ctx.globalAlpha = a.vis ? 1 : 0.35;
      ctx.fillStyle = a.eq === null ? "#9AA39F" : cor[a.eq]; ctx.fill();
      ctx.lineWidth = 2; ctx.strokeStyle = "#FFFFFF"; ctx.stroke();
      ctx.globalAlpha = 1;
      if (a.id === q.portador) {
        ctx.beginPath(); ctx.arc(p[0], p[1], raio + 6, 0, 2 * Math.PI);
        ctx.lineWidth = 3; ctx.strokeStyle = "#FFD447"; ctx.stroke();
      }
    }
    if (q.b) {
      const p = paraTela(q.b.x, q.b.y);
      if (p) { ctx.beginPath(); ctx.arc(p[0], p[1], raio * 0.55, 0, 2 * Math.PI); ctx.fillStyle = "#FFFFFF"; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = "#111"; ctx.stroke(); }
    }
  }

  function desenharGramado(ctx, paraTela, largura, altura) {
    ctx.fillStyle = "#1F4630"; ctx.fillRect(0, 0, largura, altura);
    tracar(ctx, [[-5, -5], [doc.campo.comprimento + 5, -5], [doc.campo.comprimento + 5, doc.campo.largura + 5], [-5, doc.campo.largura + 5], [-5, -5]], paraTela);
    ctx.fillStyle = "#2C5A3E"; ctx.fill();
  }

  function desenharLinhas(ctx, paraTela, espessura) {
    ctx.strokeStyle = "rgba(255,255,255,0.85)"; ctx.lineWidth = espessura;
    for (const linha of linhasDoCampo()) { tracar(ctx, linha, paraTela); ctx.stroke(); }
  }

  const camadaAtiva = (id) => $(id).checked && !$(id).disabled;

  function desenharQuadro() {
    if (!doc) return;
    const q = doc.quadros[indice];

    // Vista de transmissão
    const paraImagem = (x, y) => (q.H ? projetar(q.H, x, y) : null);
    ctxTx.clearRect(0, 0, telaTx.width, telaTx.height);
    if (!comVideo) { desenharGramado(ctxTx, paraImagem, telaTx.width, telaTx.height); desenharLinhas(ctxTx, paraImagem, 2); }
    if (q.H) {
      if (camadaAtiva("camada-zonas")) desenharZonas(ctxTx, q, paraImagem);
      if (camadaAtiva("camada-forma")) desenharForma(ctxTx, q, paraImagem, 3);
      if (camadaAtiva("camada-atletas")) desenharAtletas(ctxTx, q, paraImagem, 9, false);
    }

    // Vista de cima
    ctxMapa.clearRect(0, 0, telaMapa.width, telaMapa.height);
    desenharGramado(ctxMapa, noMapa, telaMapa.width, telaMapa.height);
    if (camadaAtiva("camada-zonas")) desenharZonas(ctxMapa, q, noMapa);
    desenharLinhas(ctxMapa, noMapa, 2);
    if (camadaAtiva("camada-forma")) desenharForma(ctxMapa, q, noMapa, 3);
    if (camadaAtiva("camada-atletas")) desenharAtletas(ctxMapa, q, noMapa, 9, true);

    // Narração
    const chip = $("chip-estado");
    chip.textContent = NOMES_ESTADO[q.estado] || q.estado;
    chip.className = "chip " + q.estado;
    $("legenda").textContent = MODO_ESTUDO ? semPercentual(q.legenda) : q.legenda;
    $("relogio").textContent = (q.t - doc.quadros[0].t).toFixed(1).replace(".", ",") + " s";
    $("linha-tempo").value = String(indice);
  }

  // ---------------------------------------------------------------- tempo
  function indiceDoVideo() {
    const f = Math.floor(video.currentTime * doc.fps + 1e-6);
    return Math.max(0, Math.min(doc.quadros.length - 1, f - doc.quadros[0].f));
  }

  function laco(ts) {
    if (doc) {
      if (comVideo) {
        indice = indiceDoVideo();
      } else if (tocando) {
        if (ultimoTs !== null) acumulado += ((ts - ultimoTs) / 1000) * doc.fps;
        const passos = Math.floor(acumulado); acumulado -= passos;
        indice = Math.min(doc.quadros.length - 1, indice + passos);
        if (indice === doc.quadros.length - 1) alternar(false);
      }
      ultimoTs = ts;
      desenharQuadro();
    }
    requestAnimationFrame(laco);
  }

  function alternar(forcar) {
    tocando = forcar === undefined ? !tocando : forcar;
    if (tocando && !comVideo && indice >= doc.quadros.length - 1) indice = 0;
    const b = $("botao-tocar");
    b.textContent = tocando ? "❚❚" : "▶";
    b.setAttribute("aria-label", tocando ? "Pausar" : "Reproduzir");
    if (comVideo) { tocando ? video.play() : video.pause(); }
    acumulado = 0;
  }

  // ---------------------------------------------------------------- carga
  function carregar(novo) {
    if (!novo || novo.versao !== 1 || !Array.isArray(novo.quadros) || !novo.quadros.length) {
      $("legenda").textContent = "Arquivo inválido: gere-o com extrair.py ou exportacao.demo.";
      return;
    }
    doc = novo; indice = 0;
    telaTx.width = doc.largura_img; telaTx.height = doc.altura_img;
    telaMapa.width = doc.campo.comprimento * ESCALA + 2 * MARGEM;
    telaMapa.height = doc.campo.largura * ESCALA + 2 * MARGEM;
    $("palco").style.aspectRatio = `${doc.largura_img} / ${doc.altura_img}`;
    $("linha-tempo").max = String(doc.quadros.length - 1);

    const [a, b] = doc.equipes;
    const seta = (e) => `${e.nome} ataca ${e.direcao === 1 ? "para a direita →" : "← para a esquerda"}`;
    $("nota-direcao").textContent = `${seta(a)} · ${seta(b)}. Círculos apagados: fora do enquadramento da câmera.`;

    const lista = $("confiabilidade"); lista.textContent = "";
    for (const [vis, d] of Object.entries(doc.exibicao)) {
      const li = document.createElement("li");
      const marca = document.createElement("span");
      marca.className = d.exibir ? "sim" : "nao"; marca.textContent = d.exibir ? "✓" : "✗";
      const texto = document.createElement("span");
      texto.textContent = d.exibir
        ? `${NOMES_VIS[vis] || vis}: confiável com o erro de medição atual.`
        : `${NOMES_VIS[vis] || vis}: oculto. Com o erro de medição atual, esta informação estaria errada com frequência (${d.motivo}).`;
      li.append(marca, texto); lista.append(li);
      const camada = CAMADA_DA_VIS[vis];
      if (camada) { $(camada).disabled = !d.exibir; if (!d.exibir) $(camada).checked = false; }
    }
    $("origem").textContent = `Origem dos dados: ${doc.origem}.`;
    desenharQuadro();
  }

  $("entrada-json").addEventListener("change", async (ev) => {
    const arq = ev.target.files[0]; if (!arq) return;
    try { carregar(JSON.parse(await arq.text())); } catch (e) { $("legenda").textContent = "Não foi possível ler o arquivo: " + e.message; }
  });
  $("entrada-video").addEventListener("change", (ev) => {
    const arq = ev.target.files[0]; if (!arq) return;
    video.src = URL.createObjectURL(arq); video.hidden = false; comVideo = true;
    alternar(false);
  });
  $("botao-tocar").addEventListener("click", () => doc && alternar());
  $("linha-tempo").addEventListener("input", (ev) => {
    if (!doc) return;
    indice = Number(ev.target.value);
    if (comVideo) video.currentTime = (doc.quadros[indice].f + 0.5) / doc.fps;
    desenharQuadro();
  });
  for (const id of ["camada-zonas", "camada-forma", "camada-atletas"]) $(id).addEventListener("change", desenharQuadro);
  document.addEventListener("keydown", (ev) => {
    if (ev.code === "Space" && doc && ev.target.tagName !== "INPUT") { ev.preventDefault(); alternar(); }
  });

  // Servido por HTTP (python -m http.server), abre a demonstração sozinho.
  fetch("dados/demo.json").then((r) => (r.ok ? r.json() : Promise.reject())).then(carregar)
    .catch(() => { $("legenda").textContent = "Abra um arquivo de dados (.json) para começar."; });
  requestAnimationFrame(laco);
})();
