# Protocolo experimental

Cada experimento isola uma fonte de erro, de modo que a degradação no
resultado final seja atribuível a um estágio específico do pipeline.

| Exp. | Objeto | Depende do SoccerNet | Situação |
| :--- | :--- | :--- | :--- |
| **E1** | Detecção (COCO / ajuste fino / fatiamento / Kalman) | sim | a implementar |
| **E2** | Registro do campo (homografia / calibração de câmera) | sim | módulo `pitch/` pronto; falta o avaliador sobre dados reais |
| **E3** | Velocidade estimada vs. de referência | sim | a implementar |
| **E4** | Controle de espaço: entrada estimada vs. de referência | sim | modelo em `controle/` pronto; falta o avaliador |
| **E5** | Sensibilidade ao erro de registro | **não** | **executável** |
| **E6** | Custo computacional e fronteira de Pareto | parcial | a implementar |

## E5 — executável hoje

Não depende de detector, rastreador nem vídeo: parte de uma configuração de
jogadores em coordenadas conhecidas, projeta para a imagem, perturba o registro
com magnitude calibrada em metros e mede o desvio induzido em cada métrica.

```bash
python -m experiments.e5_sensibilidade --repeticoes 200 --saida resultados/
```

Produz `resultados/e5_sensibilidade.csv` e `resultados/e5_sensibilidade.png`.

### Resultado obtido (200 repetições, semente 20260925)

Erro relativo de cada métrica, em função do erro médio de reprojeção:

| Erro de registro | Largura | Profundidade | Área de ocupação | Controle de espaço | **Identidade do dominante** |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0,26 m | 0,46 % | 0,22 % | 0,53 % | 0,24 % | **1,83 %** |
| 1,08 m | 1,90 % | 0,92 % | 2,13 % | 0,90 % | **4,58 %** |
| 1,95 m | 3,83 % | 1,76 % | 4,16 % | 1,75 % | **8,07 %** |
| 3,12 m | 5,51 % | 2,95 % | 6,29 % | 2,69 % | **12,42 %** |

**Leitura.** Os agregados de nível de equipe são notavelmente robustos: mesmo a
3 m de erro de registro, o controle de espaço desvia menos de 3 %. A identidade
do atleta que domina cada célula degrada cerca de **4,6 vezes mais rápido** — a
média sobre 22 atletas e milhares de células cancela parcialmente os
deslocamentos, mas a atribuição de uma célula a *um* atleta específico não tem
o que cancelar.

O viés é praticamente nulo em todos os níveis: o erro de registro se manifesta
como variância, não como deslocamento sistemático das métricas.

### Ressalvas

A configuração de jogadores é sintética e a homografia de transmissão é fixa.
Os números acima descrevem a **sensibilidade do estimador**, não o desempenho
sobre partidas reais — este último exige E2 e E4 sobre o SoccerNet. A
conclusão qualitativa (agregados robustos, identidade frágil) é o que deve ser
levado ao artigo; os valores percentuais devem ser reproduzidos sobre dados
reais antes de figurarem como resultado principal.
