# Controle de espaço em futebol a partir de vídeo monocular

Repositório de pesquisa do artigo *Estimação de Controle de Espaço em Futebol a
partir de Vídeo Monocular: o Impacto do Erro de Registro do Campo em Métricas
Táticas*, produzido na disciplina de Processamento Inteligente de Imagens
Aeroespaciais do IDP.

> **Trabalho derivado.** A base de detecção, rastreamento e classificação vem de
> [tryolabs/soccer-video-analytics](https://github.com/tryolabs/soccer-video-analytics)
> (MIT, 2022). Ver [`NOTICE.md`](NOTICE.md) para a delimitação exata do que foi
> herdado e do que é contribuição própria. **Qualquer publicação derivada deve
> citar o projeto original.**

## A pergunta

Modelos de controle de espaço quantificam qual equipe domina cada região do
campo, mas dependem de rastreamento multicâmera disponível apenas a clubes
profissionais. **É possível alimentá-los com vídeo de transmissão de câmera
única — e quanto se perde ao fazê-lo?**

A peça que torna a pergunta respondível é o **registro do campo**. Métricas
calculadas no plano da imagem variam com o zoom e o enquadramento da câmera, e
não com o comportamento das equipes: a mesma formação, sem ninguém se mover,
produz áreas de casco convexo completamente diferentes. Só após a projeção para
o plano do gramado as grandezas passam a ser físicas — metros, metros por
segundo, metros quadrados — e comparáveis entre lances, partidas e estudos.

## Estrutura

```
pitch/          Registro do campo: modelo métrico, homografia (DLT + RANSAC),
                perturbação controlada para a análise de sensibilidade
controle/       Controle de espaço por tempo até a interceptação
metrics/        Avaliação: erro de registro, Brier, top-k, log-loss
soccer/         Lógica de jogo, métricas táticas em metros, camada de desenho
inference/      Detecção (YOLOv8) e classificação de equipes (linha de base HSV)
utils/          Funções de apoio ao pipeline
experiments/    Protocolo experimental E1–E6
paper/          O artigo e seu estado por seção
tests/          Suíte de regressão (46 testes)
```

A separação entre `soccer/metricas_taticas.py` (cálculo, em metros) e
`soccer/visualizacao_tatica.py` (desenho, em pixels) é deliberada: nenhum número
do artigo sai da camada de desenho.

## Instalação

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

**Experimento E5** — sensibilidade ao erro de registro. Não depende do
SoccerNet nem de GPU:

```bash
python -m experiments.e5_sensibilidade --repeticoes 200 --saida resultados/
```

**Vídeo anotado** — figura qualitativa do artigo:

```bash
python analise_video.py --video videos/partida.mp4 --tatico --homografia H.npy
```

Sem `--homografia`, a posse é decidida por limiar em pixels, que não é
invariante à escala. É um modo degradado, e o programa avisa.

**Testes:**

```bash
pytest tests/ -q
```

## Situação

| Componente | Situação |
| :--- | :--- |
| Modelo do campo e homografia | pronto e testado |
| Controle de espaço | pronto e testado |
| Métricas táticas em metros | pronto e testado |
| Métricas de avaliação | pronto e testado |
| E5 (sensibilidade) | **executável**, com resultado em [`experiments/README.md`](experiments/README.md) |
| E1–E4, E6 | dependem do SoccerNet; a implementar |
| Artigo | título, resumo, introdução e metodologia escritos |

Os defeitos da versão anterior — entre eles a posse de bola que nunca se
encerrava e a compactação medida em pixels — estão documentados em
[`CHANGELOG.md`](CHANGELOG.md), com testes de regressão para cada um.

## Dados

Os experimentos E1–E4 e E6 usam o [SoccerNet Game State
Reconstruction](https://github.com/SoccerNet/sn-gamestate), que fornece
posições de referência em coordenadas do campo. É esse dado que permite
estabelecer o teto de desempenho contra o qual a estimativa monocular é
comparada. Vídeos e pesos de modelos não são versionados (ver `.gitignore`).

## Licença

MIT. Ver [`LICENSE.md`](LICENSE.md) e [`NOTICE.md`](NOTICE.md).
