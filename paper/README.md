# Artigo

`Artigo_Controle_de_Espaco_SBC.docx`, no modelo SBC.

**Título.** Do Pixel à Narrativa: Visualizações Confiáveis de Controle de
Espaço em Transmissões de Futebol para o Público Geral

**Autores.** Claudio Meireles Filho, Felipe Pereira, Lucas Ungarelli, Pedro
Araújo (IDP)

## Situação por seção

| Seção | Situação | Origem dos números |
| :--- | :--- | :--- |
| Título, autores, instituição | pronto | faltam os e-mails (o modelo SBC os pede) |
| Abstract, Resumo, palavras-chave | pronto | 8 e 9 linhas, dentro do limite de 10 |
| 1. Introdução | pronto | |
| 2. Metodologia (2.1 a 2.8, Figura 1, Tabela 1) | pronto | simulações de `tests/` e `experiments/` |
| 3. Resultados | a escrever | E1 a E6 |
| 4. Discussão e limitações | a escrever | |
| 5. Conclusão | a escrever | |
| Referências | 13, todas citadas e conferidas na fonte | |

## Figuras

- `figuras/prototipo_player.png`: Figura 1, gerada por
  `python web/verificar.py --figura paper/figuras/prototipo_player.png`.

## Números citados na metodologia e sua origem

| Número | Origem |
| :--- | :--- |
| 29 marcos do campo | `pitch/modelo_campo.py` |
| Reancoragem: 0,85 m para 0,50 m | simulação descrita em `experiments/README.md` |
| Histerese: mais de 100 trocas contra no máximo 2 | `tests/test_narrativa.py` |
| Poder de 0,83 com 24 pessoas e 18 perguntas | `estudo/PROTOCOLO.md` |
| 81 % de acurácia de Spearman et al. | Spearman et al. (2017) |
| 16 participantes do iBall | Chen et al. (2023) |

## Antes de entregar

- Abrir no Word e conferir a primeira página e a posição da Figura 1: a
  formatação foi validada nas propriedades do arquivo, não numa página
  renderizada.
- Acrescentar os e-mails dos autores, se exigidos.
