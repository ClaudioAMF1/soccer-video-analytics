# Protocolo experimental

## Resultados sobre transmissões reais (SoccerNet-GSR, artigo final)

Todos os números do artigo final vêm destes scripts, executados sobre as 49
sequências de teste do SoccerNet-GSR (36.750 quadros de 1920 × 1080 a 25 fps).
Os CSVs estão em `paper/dados/`; `paper/reproduzir.sh` refaz tudo.

| Script | O que mede |
| :--- | :--- |
| `caracterizacao.py` | atletas visíveis por quadro, presença da bola, resíduo da referência |
| `e1_deteccao_real.py` | YOLOv8x COCO: revocação, precisão, filtro pelo campo, bola com e sem fatiamento |
| `e2_registro_real.py` | erro do registro por quadros-chave, com fluxo óptico real |
| `e5_real.py` | sensibilidade de cada métrica ao erro de registro, em configurações reais |
| `narrativa_real.py` | estabilidade da posse e da legenda; validade do estado de finalização |
| `figura_sensibilidade.py` | Figura 2 do artigo |

### Registro por quadros-chave (E2)

Anotação simulada: marcos visíveis projetados pela homografia de referência,
com ruído de 2 px. Erro de posição dos atletas, mediana (percentil 90):

| Intervalo | Sem propagação | Só chave anterior | Com reancoragem |
| ---: | ---: | ---: | ---: |
| 1 s | 1,65 m (11,9) | **0,42 m (1,92)** | 0,39 m (3,42) |
| 2 s | 3,14 m (17,5) | 0,52 m (2,64) | 0,48 m (4,19) |
| 5 s | 6,99 m (33,1) | 0,81 m (5,88) | 0,76 m (8,08) |

Uma homografia única para a sequência erra 17,3 m (mediana). **A reancoragem
reduz a mediana, mas piora a cauda**: quando a propagação a partir de uma das
chaves falha, a média ponderada herda o erro. A simulação indicava ganho de
41 %; o vídeo real não confirma. Uma salvaguarda que descarte a estimativa
divergente fica como trabalho futuro, e deve ser calibrada na partição de
validação, não no teste.

### Sensibilidade sobre configurações reais (E5)

1.285 quadros utilizáveis (1 por segundo), 4 repetições por nível de ruído.
Erro de registro em que cada métrica atinge 5 % de erro relativo:

| Métrica | Limite |
| :--- | ---: |
| Área de ocupação | 0,54 m |
| Jogador dominante (identidade) | 0,65 m |
| Profundidade | 0,77 m |
| Largura | 0,92 m |
| Controle de espaço da equipe | não atinge até 2,4 m (4,2 %) |

**A simulação sintética abaixo superestimou a robustez da forma da equipe**
(indicava 2 m). Com só cerca de seis atletas visíveis por equipe, o contorno
depende de poucos pontos. O controle de espaço continua robusto.

### Posse e narrativa

Com ruído de registro de 1 m e oscilação de 0,2 m por atleta, a versão de
corte único troca a posse 14,0 vezes por minuto; com histerese, 6,0. Estados
de menos de meio segundo caem de 6,4 para 3,6 por minuto. O estado de
finalização aparece em 8 de 13 sequências de chute (62 %) e em 11 de 36 demais
(31 %): associação moderada, pois escanteios e faltas também levam a bola
para perto do gol.

---

## Resultados anteriores com dados sintéticos

O artigo tem três contribuições encadeadas, e cada experimento serve a uma:

- **Medição** (E1 a E5): o que é confiável quando se parte de vídeo gravado de
  transmissão.
- **Design**: a regra de exibição (`narrativa/confiabilidade.py`) usa E2 e E5
  para decidir o que o espectador pode ver.
- **Avaliação** (E6): o espectador leigo entende melhor a jogada com a
  interface?

| Exp. | Objeto | Depende do SoccerNet | Situação |
| :--- | :--- | :--- | :--- |
| **E1** | Detecção (COCO / ajuste fino / fatiamento / Kalman) | sim | a implementar |
| **E2** | Registro por quadros-chave: erro por região e deriva entre chaves, com e sem reancoragem | sim | `pitch/propagacao.py` pronto e testado; falta o avaliador sobre dados reais |
| **E3** | Velocidade estimada vs. de referência | sim | estimador em `exportacao/pipeline.py` pronto; falta o avaliador |
| **E4** | Controle de espaço: entrada estimada vs. de referência | sim | modelo em `controle/` pronto; falta o avaliador |
| **E5** | Sensibilidade de cada métrica ao erro de registro | **não** | **executável, com resultado** |
| **E6** | Estudo com usuários: interface dinâmica vs. mapa estático | não | protocolo, instrumentos e análise prontos em `estudo/`; falta a coleta |

Como o processamento é offline, sobre jogos gravados, não há exigência de tempo
real: o antigo experimento de custo computacional deixou de fazer parte do
protocolo.

## E5: resultado

```bash
python -m experiments.e5_sensibilidade --repeticoes 200 --saida resultados/
```

Configuração sintética (22 atletas, homografia de transmissão fixa, 29 marcos
do campo), 200 repetições por nível, semente 20260925. Erro relativo de cada
métrica em função do erro médio de reprojeção:

| Erro de registro | Largura | Área de ocupação | Controle de espaço | **Identidade do dominante** |
| ---: | ---: | ---: | ---: | ---: |
| 0,52 m | 1,07 % | 1,24 % | 0,40 % | **2,58 %** |
| 1,07 m | 2,31 % | 2,46 % | 0,82 % | **4,54 %** |
| 1,92 m | 4,22 % | 4,67 % | 1,63 % | **8,00 %** |
| 2,89 m | 6,23 % | 6,90 % | 2,36 % | **11,92 %** |

**Hierarquia de robustez.** Com o limiar de exibição de 5 %:

| Visualização | Deixa de ser exibível a partir de |
| :--- | ---: |
| Qual jogador domina cada ponto (nível de jogador) | 1,18 m |
| Forma da equipe (área de ocupação) | 2,04 m |
| Forma da equipe (largura) | 2,24 m |
| Zonas de controle (nível de equipe) | não atinge o limiar até 2,89 m |

A identidade individual degrada cerca de **cinco vezes** mais rápido que o
controle de espaço agregado. A média sobre 22 atletas e centenas de células
cancela parcialmente os deslocamentos; a atribuição de uma célula a *um*
atleta não tem o que cancelar. O viés é praticamente nulo: o erro de registro
aparece como variância, não como distorção sistemática das métricas.

**Ressalva.** Os valores descrevem a sensibilidade do estimador numa
configuração sintética. A conclusão qualitativa (agregados robustos, identidade
frágil) é o que vai para o artigo como motivação da regra de exibição; os
percentuais devem ser reproduzidos com posições do SoccerNet antes de figurarem
como resultado principal.

## Registro por quadros-chave: indicação sintética para o E2

Deriva em passeio aleatório (desvio de 0,8 px por quadro), quadros-chave a
cada 100 quadros, 200 simulações (`tests/test_propagacao.py` reproduz o
cenário):

| | Erro médio | p95 |
| :--- | ---: | ---: |
| Propagação só a partir da chave anterior | 0,85 m | 1,49 m |
| Com reancoragem entre as duas chaves | 0,50 m | 0,79 m |

Redução de 41 %. Com deriva puramente linear a compensação é total, mas a
deriva real não é linear; o E2 mede o valor efetivo sobre vídeo real.
