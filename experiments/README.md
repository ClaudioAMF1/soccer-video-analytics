# Protocolo experimental

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
