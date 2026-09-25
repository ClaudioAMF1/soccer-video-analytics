# Registro de alterações

## Fusão: medição + interface para o público geral, 2026-09

O artigo passou a ter três contribuições encadeadas: medir o que é confiável a
partir de jogos gravados da TV, usar essa medição para decidir o que exibir, e
avaliar com pessoas se a interface melhora a compreensão. O processamento é
offline, sobre jogos gravados.

### Acrescentado

- `pitch/propagacao.py`: registro do campo por quadros-chave anotados,
  propagado pelo movimento de câmera e reancorado entre chaves. Em simulação
  com deriva aleatória, a reancoragem reduz o erro médio em 41 %.
- `pitch/modelo_campo.py`: oito marcos novos (círculo central e arcos das
  áreas). Com a câmera no meio do campo, só três dos 21 marcos anteriores
  ficavam visíveis, menos que os quatro exigidos.
- `narrativa/estados.py`: estados da jogada (bola parada, disputa, construção,
  ataque, transição, finalização) com faixa de histerese e confirmação
  temporal, e legendas em linguagem comum.
- `narrativa/confiabilidade.py`: regra de exibição a partir do E5.
- `exportacao/`: segunda passada da extração, formato JSON documentado e jogada
  sintética de demonstração que passa pelo pipeline real.
- `extrair.py` e `anotar.py`: primeira passada sobre vídeo gravado e ferramenta
  de anotação de quadros-chave.
- `web/`: player narrativo, com modo de estudo (`?estudo`) sem percentuais.
- `estudo/`: protocolo, TCLE, questionário e análise estatística do E6.
- `RESUMO_EXECUTIVO.md`.

### Corrigido

- `soccer/partida.py`: com a bola em trânsito, a posse passava a "em disputa",
  de modo que **todo passe encerrava a posse**. A equipe que passa a bola agora
  a mantém até o adversário dominá-la. Novo parâmetro `em_metros`.
- `narrativa/estados.py`: a equipe narrada mudava antes do estado ser
  confirmado, e a legenda chegava a atribuir o ataque de uma equipe à outra.
  Estado e equipe agora são confirmados juntos.

### Alterado

- O antigo E6 (custo computacional para tempo real) saiu do protocolo: com
  processamento offline, não há exigência de tempo real. O E6 passa a ser o
  estudo com usuários.
- E5 refeito com os 29 marcos; conclusões inalteradas.
- Artigo reescrito com o novo título e foco; agora cita Tryolabs (2022) como
  base do código e não tem referências sem citação.

## Reorientação do repositório para a produção do artigo — 2026-09

O repositório deixou de ser uma demonstração visual e passou a ser o
instrumento experimental do artigo. As mudanças abaixo têm efeito sobre
**resultados**, não apenas sobre organização.

### Defeitos corrigidos

| Arquivo | Defeito | Efeito da correção |
| :--- | :--- | :--- |
| `soccer/partida.py` | `time_com_posse` nunca voltava a `None`; o contador incrementava em todo quadro após o primeiro toque, inclusive com bola fora, faltas e replays. | Máquina de estados explícita (`EstadoPosse`) com histerese e encerramento por bola ausente. As porcentagens passam a medir posse, e não "quem tocou por último". |
| `inference/hsv_classifier.py` | `max_pixels = -1` com comparação estrita fazia um recorte sem nenhum pixel correspondente retornar o *primeiro* filtro da lista — o do árbitro. | Retorno `unknown` e exigência de fração mínima de pixels. Atletas não classificáveis deixam de ser silenciosamente removidos das métricas. |
| `soccer/visualizacao_tatica.py` | Área do casco convexo calculada em pixels e reportada como "compactação"; variava com o zoom da câmera. | Cálculo movido para `soccer/metricas_taticas.py`, em metros. O módulo antigo passa a ser exclusivamente camada de desenho. |
| `analise_video.py` | Dois `Detector("yolov8x.pt")` idênticos executados por quadro sobre a mesma imagem. | Detector único compartilhado; metade do custo de inferência para resultado idêntico. |
| `utils/funcoes_execucao.py` | `DataFrame` vazio não tem coluna `confidence`; indexá-la levantava `KeyError`. | Tratamento explícito do quadro sem detecções (cortes de câmera, replays, telas de placar). |
| `soccer/bola.py` | `np.round_` foi removido no NumPy 2.0. | Substituído; o código volta a executar em ambientes atuais. |
| `soccer/time.py` | `round(x, 2)` antes de multiplicar por 100 zerava a casa decimal exibida. | Divisão sem arredondamento prematuro. |
| `soccer/jogador.py` | Distância à bola medida do centro da caixa (altura do tronco). | Novo `ponto_apoio` (aresta inferior), que projeta corretamente no gramado. |

### Removido

- `soccer/evento_passe.py` — métodos vazios, nunca implementados.
- `inference/box.py` — classe sem nenhum uso no projeto.
- `entrega_final.ipynb` — duplicava os módulos por cópia colada, de modo que as
  duas versões já divergiriam a cada correção; além disso, carregava o código
  anterior a todos os defeitos corrigidos acima. **Permanece recuperável no
  histórico** (`git show 738e740:entrega_final.ipynb`). Se o notebook ainda for
  exigido como entrega da disciplina anterior, restaure-o em vez de recriá-lo,
  para preservar o registro do que foi efetivamente submetido.

### Acrescentado

- `pitch/` — modelo métrico do campo, estimação de homografia (DLT normalizado
  e RANSAC) e perturbação controlada para a análise de sensibilidade.
- `controle/` — modelo de controle de espaço por tempo até a interceptação.
- `metrics/` — erro de registro, Brier, top-k, log-loss.
- `soccer/metricas_taticas.py` — métricas táticas em metros.
- `experiments/e5_sensibilidade.py` — experimento E5, executável.
- `tests/` — 46 testes, incluindo regressão dos defeitos acima.
- `LICENSE.md` restaurado e `NOTICE.md` com a procedência do código.
- `requirements.txt` com versões fixadas.
