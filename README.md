# Do Pixel à Narrativa

Repositório de pesquisa do artigo *Do Pixel à Narrativa: Visualizações
Confiáveis de Controle de Espaço em Transmissões de Futebol para o Público
Geral* (IDP). Para uma visão geral do projeto, leia primeiro o
[**resumo executivo**](RESUMO_EXECUTIVO.md).

> **Trabalho derivado.** A base de detecção, rastreamento e classificação vem de
> [tryolabs/soccer-video-analytics](https://github.com/tryolabs/soccer-video-analytics)
> (MIT, 2022). [`NOTICE.md`](NOTICE.md) delimita o que foi herdado e o que é
> contribuição própria. **Qualquer publicação derivada deve citar o projeto
> original.**

## A pergunta

Modelos de controle de espaço mostram qual equipe domina cada região do campo,
mas dependem de rastreamento proprietário e quase não chegam ao público. **É
possível estimá-los a partir de jogos gravados da TV e mostrá-los a
espectadores leigos sem afirmar nada falso?**

O projeto responde em três partes: mede quanto cada informação tática se
distorce com o erro do vídeo de transmissão; usa essa medição para decidir o
que pode ser exibido; e avalia, com pessoas, se a interface resultante melhora
a compreensão do jogo.

## Arquitetura

```
 jogo gravado ──► 1. EXTRAÇÃO ──────────► JSON ──► 3. VISUALIZAÇÃO
                  detecção, rastreamento,          player web sobre o vídeo
                  registro do campo,        ▲
                  posições em metros        │
                                   2. NARRATIVA
                                   estado da jogada, legenda,
                                   regra do que é confiável exibir
```

```
pitch/          Registro do campo: 29 marcos oficiais, homografia (DLT + RANSAC),
                quadros-chave com propagação e reancoragem, perturbação (E5)
controle/       Controle de espaço por tempo até a interceptação
narrativa/      Estados da jogada com histerese; regra de exibição
exportacao/     Segunda passada da extração, formato JSON, jogada de demonstração
soccer/         Posse de bola, métricas táticas em metros, camada de desenho
inference/      Detecção (YOLOv8) e classificação de equipes (linha de base HSV)
metrics/        Erro de registro, Brier, top-k, log-loss
experiments/    Protocolo E1 a E6 e o experimento E5, executável
estudo/         Estudo com usuários: protocolo, TCLE, questionário, análise
web/            Player (HTML, CSS, JavaScript, sem dependências)
paper/          O artigo (.docx no modelo SBC) e suas figuras
tests/          88 testes automatizados
extrair.py      Etapa 1 sobre um jogo gravado
anotar.py       Anotação manual dos quadros-chave
```

## Como usar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Ver o player funcionando, sem vídeo nem dados externos:**

```bash
python -m exportacao.demo --saida web/dados/demo.json
cd web && python -m http.server 8000
# abrir http://localhost:8000
```

Acrescente `?estudo` ao endereço para o modo usado no estudo com usuários, que
omite os percentuais da legenda.

**Processar um jogo gravado:**

```bash
python anotar.py --video jogo.mp4 --quadros 0,250,500 --saida anotacoes.json
python extrair.py --video jogo.mp4 --anotacoes anotacoes.json \
    --equipes "Palmeiras,Inter Miami" --saida web/dados/jogo.json
```

Os nomes das equipes devem ser os mesmos de `config/filtros_cores.py`. Anote
quadros-chave a cada 5 a 10 segundos e após cada corte de câmera, com ao menos
seis marcos visíveis. O formato está em `exemplos/anotacoes_exemplo.json`.

**Experimento E5 e análise do estudo:**

```bash
python -m experiments.e5_sensibilidade --repeticoes 200 --saida resultados/
python -m estudo.analise --simular 24        # demonstração com dados sintéticos
```

**Testes:**

```bash
pytest tests/ -q
python web/verificar.py      # opcional: teste do player em navegador (exige Playwright)
```

## Situação

| Componente | Situação |
| :--- | :--- |
| Registro do campo, quadros-chave e reancoragem | pronto e testado |
| Controle de espaço, posse, métricas em metros | pronto e testado |
| Estados narrativos e regra de exibição | pronto e testado |
| Exportação JSON e jogada de demonstração | pronto e testado |
| Player web | pronto; testado em navegador real |
| E5 (sensibilidade) | executável, com resultado em [`experiments/README.md`](experiments/README.md) |
| Estudo com usuários (E6) | protocolo e análise prontos; falta a coleta |
| E1 a E4 | dependem do SoccerNet |
| Artigo | título, resumo, introdução e metodologia escritos |

`extrair.py` e `anotar.py` dependem de detector, vídeo e interface gráfica, e
não foram executados no ambiente em que o restante foi testado. A lógica que
eles alimentam (`exportacao/pipeline.py`) é testada com dados sintéticos.

## Licença

MIT. Ver [`LICENSE.md`](LICENSE.md) e [`NOTICE.md`](NOTICE.md).
