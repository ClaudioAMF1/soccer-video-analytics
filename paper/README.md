# Artigo

| Arquivo | O que é |
| :--- | :--- |
| `Artigo_Final.docx` | **Artigo final**, formato da disciplina (ABNT) |
| `Artigo_Controle_de_Espaco_SBC.docx` | Primeira entrega (modelo SBC), mantida como histórico |
| `gerar_artigo.py` | Gera o artigo final a partir de `dados/` |
| `reproduzir.sh` | Refaz dados, figura e artigo desde o download do SoccerNet-GSR |
| `dados/` | CSVs e fichas de todos os experimentos citados no texto |
| `figuras/` | Figura 1 (protótipo) e Figura 2 (sensibilidade) |

**Título.** Do Pixel à Narrativa: Visualizações Confiáveis de Controle de
Espaço em Transmissões de Futebol para o Público Geral

**Autores.** Claudio da Aparecida Meireles Filho, Felipe Pereira Dutra, Lucas
Fiche Ungarelli Borges, Pedro Rodrigues de Araújo (IDP)

## Conferência dos requisitos

| Requisito | Situação |
| :--- | :--- |
| Título, autores | sim |
| Resumo | sim, com objetivo, método, resultados e conclusão; 100 a 250 palavras (NBR 6028) |
| Palavras-chave (3 a 5) | 5, separadas por ponto e vírgula |
| Introdução | sim |
| Fundamentação Teórica | sim (inclui as concepções das regras do futebol) |
| Metodologia | sim |
| Resultados e Discussão | sim, sobre 49 sequências reais do SoccerNet-GSR |
| Conclusão | sim, com limitações e trabalhos futuros |
| Referências | ABNT NBR 6023, ordem alfabética, todas citadas no texto |
| Entre 4 e 8 páginas | verificado renderizando o `.docx` |
| Times New Roman 12 | sim; legendas e fontes de figura em 10 |
| Espaçamento 1,5 | sim; resumo, legendas e referências em simples, como pede a ABNT |
| Margens de 2,5 cm | sim, nos quatro lados |

## Como regenerar

```bash
python paper/gerar_artigo.py --dados paper/dados --saida paper/Artigo_Final.docx
```

Nenhum número do texto é digitado à mão: alterar um resultado exige reexecutar
o experimento correspondente e regenerar o artigo.

## O que não está no artigo, e por quê

- **Estudo com usuários e formulário exploratório:** planejados (`estudo/`),
  não executados. O artigo os apresenta como etapa seguinte e não afirma nada
  sobre compreensão do espectador.
- **Segmentação em planos de câmera:** implementada e testada com quadros
  sintéticos, mas não avaliada: as sequências do SoccerNet-GSR não têm cortes.
