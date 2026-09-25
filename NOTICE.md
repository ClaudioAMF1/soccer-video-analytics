# Procedência do código

Este repositório é um **trabalho derivado** de
[tryolabs/soccer-video-analytics](https://github.com/tryolabs/soccer-video-analytics),
publicado por Tryolabs em 2022 sob licença MIT.

## O que foi herdado

Os módulos `inference/` e `utils/`, e parte de `soccer/`, originam-se daquele
projeto e foram traduzidos para português e simplificados. A correspondência
direta inclui:

| Neste repositório | No projeto original |
| :--- | :--- |
| `inference/converter.py` (`Converter`) | `inference/converter.py` |
| `inference/hsv_classifier.py` (`HSVClassifier`) | `inference/hsv_classifier.py` |
| `inference/inertia_classifier.py` (`InertiaClassifier`) | `inference/inertia_classifier.py` |
| `inference/base_detector.py`, `base_classifier.py` | idem |
| `utils/funcoes_execucao.py` | `run_utils.py` |
| `soccer/partida.py` (`Partida`) | `soccer/match.py` (`Match`) |
| `soccer/jogador.py`, `bola.py`, `time.py` | `soccer/player.py`, `ball.py`, `team.py` |

O histórico Git preserva os commits originais (os mais antigos, de setembro a
novembro de 2022, assinados por Diego Marvid, Diego Fernandez e Alan Descoins).

## O que é contribuição própria

- `pitch/` — registro do campo e mudança de referencial para coordenadas métricas
- `controle/` — modelo de controle de espaço (tempo até interceptação)
- `metrics/` — avaliação quantitativa (erro de reprojeção, Brier, top-k)
- `experiments/` — protocolo experimental do artigo
- `soccer/metricas_taticas.py` — métricas táticas no plano do campo
- Migração do detector de YOLOv5 para YOLOv8
- Correção dos defeitos documentados em `CHANGELOG.md`

## Obrigação de citação

Qualquer publicação derivada deste repositório **deve** citar o projeto original.
Entrada sugerida:

> Tryolabs (2022). soccer-video-analytics. Disponível em:
> https://github.com/tryolabs/soccer-video-analytics. Licença MIT.

O aviso de copyright da licença MIT está preservado em `LICENSE.md` e deve
permanecer no repositório.
