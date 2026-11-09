# Resumo executivo

**Projeto:** Do Pixel à Narrativa: Visualizações Confiáveis de Controle de
Espaço em Transmissões de Futebol para o Público Geral
**Equipe:** Claudio da Aparecida Meireles Filho, Felipe Pereira Dutra, Lucas Fiche
Ungarelli Borges, Pedro Rodrigues de Araújo (IDP)
**Situação em:** novembro de 2026, artigo final entregue (`paper/Artigo_Final.docx`)

## Em uma frase

Transformar jogos de futebol gravados da TV em explicações visuais que um
espectador leigo entende, mostrando **apenas** as informações que o sistema
consegue medir com confiança.

## O problema

Clubes profissionais usam uma métrica chamada **controle de espaço**: para cada
ponto do campo, qual equipe chegaria primeiro à bola. Ela explica boa parte do
que os comentaristas chamam de "espaço", "compactação" ou "organização". Mas
depende de câmeras caras instaladas nos estádios, e quase nada disso chega ao
público.

Dá para estimar a mesma coisa a partir do vídeo da transmissão, só que com
erro. E uma interface para leigos que ignore esse erro pode mostrar, com
aparência de precisão, algo que é falso.

## O que o sistema faz

O sistema funciona em três etapas, que se comunicam por um arquivo de dados:

| Etapa | O que faz | Onde está |
| :--- | :--- | :--- |
| **1. Extração** | Lê o jogo gravado, encontra jogadores e bola, converte as posições da tela para metros no gramado e calcula velocidades. Não desenha nada. | `extrair.py`, `anotar.py`, `exportacao/`, `pitch/` |
| **2. Narrativa** | Decide o momento da jogada (construção, ataque, transição, finalização) e escreve uma frase em linguagem comum. Decide também o que é confiável o bastante para ser mostrado. | `narrativa/`, `controle/` |
| **3. Visualização** | Player no navegador que sobrepõe ao vídeo as zonas de controle e a forma das equipes, acompanhando o movimento da câmera. | `web/` |

## Por que é original

Já existem sistemas que colocam gráficos sobre vídeos esportivos para
torcedores casuais. O principal é o **iBall** (CHI 2023), feito para basquete.
Todos funcionam em esportes de quadra pequena, com câmera quase parada e poucos
jogadores.

O futebol de TV é mais difícil: a câmera se move o tempo todo e mostra só parte
dos 22 jogadores. E **nenhum** desses trabalhos pergunta se o que é mostrado ao
público continua verdadeiro diante do erro de medição. É essa pergunta que
diferencia o nosso trabalho.

## Decisões tomadas

| Decisão | Motivo |
| :--- | :--- |
| Fundir o estudo de medição com a interface para o público | A medição diz o que é seguro mostrar; a interface mostra só isso. Uma parte justifica a outra. |
| Jogos gravados, processados offline | A equipe não tem câmera própria. Dispensar o tempo real permite anotar alguns quadros à mão, o que torna o registro do campo viável sem treinar um detector. |
| Controle de espaço no lugar do xG | O xG exige um modelo treinado com milhares de finalizações rotuladas. O controle de espaço já está implementado e validado. |
| Arquivo JSON no lugar de banco SQL | Um clipe tem cerca de 16 mil registros. Um banco de dados só acrescentaria complexidade. |
| Estudo com usuários como parte central | Sem ele, o trabalho seria uma demonstração, não uma pesquisa. |

## O que já está pronto

| Componente | Evidência |
| :--- | :--- |
| Registro do campo (homografia) | No caso sem ruído, erro praticamente nulo (menos de um bilionésimo de milímetro); descarta automaticamente pontos anotados errados |
| Registro por quadros-chave em vídeo com câmera móvel | Posições exportadas batem com a verdade simulada a menos de 5 cm |
| Controle de espaço | Direção do movimento pesa corretamente: um jogador mais distante, correndo para a bola, chega antes |
| Posse de bola corrigida | Não termina mais a cada passe, nem persiste com a bola fora de jogo |
| Máquina narrativa | Um defensor oscilando no limite faria um corte simples piscar mais de 100 vezes; a nossa troca de estado no máximo 2 |
| Player web | Testado em navegador real, sem erros, funciona no celular |
| Protocolo do estudo com usuários | Protocolo, termo de consentimento, questionário e análise estatística prontos |
| Artigo | Resumo, introdução, concepções das regras do futebol e metodologia, revisados conforme as notas do professor |
| Segmentação da transmissão em planos | Separa planos abertos de closes e replays, por histograma de cor e proporção de gramado |
| Formulário exploratório | Pronto para o Google Forms, com versões para quem é e quem não é do meio do futebol |
| Testes automatizados | 93 testes passando |

## Resultados sobre transmissões reais

Os experimentos rodaram sobre as **49 sequências de teste do SoccerNet-GSR**
(36.750 quadros de transmissões reais, com a posição verdadeira de cada atleta
anotada). Todos os números abaixo estão no artigo final.

| O que foi medido | Resultado |
| :--- | :--- |
| Atletas que a câmera mostra por quadro | 13,0 em média, de 22 em campo |
| Quadros com marcos suficientes para anotar o campo | 94% (4 marcos); 79% (6 ou mais) |
| Erro ao usar uma única calibração para a sequência inteira | 17,3 m (a câmera se move muito) |
| Erro do registro com um quadro-chave por segundo | **0,42 m** (mediana); 1,92 m no pior 10% |
| Atletas encontrados pelo detector | 91% (só 60% dos pequenos, ao fundo) |
| Detecções de pessoa que eram atletas | 87%; **93%** descartando quem está fora do gramado |
| Quadros em que a bola foi localizada | 60% (a bola tem só 17 px) |
| Trocas de posse por minuto, sem e com histerese | 14,0 → **6,0** |

**O achado principal.** Com o limite de 5% de erro, cada visualização aguenta
um erro de registro diferente:

| Visualização | Aguenta até |
| :--- | ---: |
| Área ocupada pela equipe | 0,54 m |
| Qual jogador domina cada ponto | 0,65 m |
| Largura da equipe | 0,92 m |
| **Zonas de controle da equipe** | **mais de 2,4 m** |

Como o registro erra até 1,92 m em 10% dos quadros, **só as zonas de controle
são seguras para mostrar ao público**. A interface é coletiva por consequência
da medição.

**Duas simulações foram corrigidas pelos dados reais.** A forma da equipe é bem
mais frágil do que a simulação indicava (0,5 a 0,9 m, contra 2 m), porque a
câmera mostra só parte de cada time. E a reancoragem entre quadros-chave, que
em simulação reduzia o erro em 41%, piorou os casos difíceis no vídeo real. O
artigo reporta as duas coisas.

## O que falta

| Item | Situação |
| :--- | :--- |
| Estudo com 24 espectadores | planejado em `estudo/`, não executado |
| Formulário exploratório | pronto em `estudo/formulario_exploratorio.md`, não divulgado |
| Avaliar a separação de planos de câmera | as sequências do SoccerNet-GSR não têm cortes |
| Melhorar a detecção da bola | ajuste fino do detector com dados de futebol |

## Riscos

| Risco | Como reduzir |
| :--- | :--- |
| Erro real de registro maior que o simulado | A regra de exibição se ajusta sozinha: esconde mais coisas. O resultado continua publicável, com a interface mais simples. |
| Estudo sem diferença significativa | O protocolo já tem poder calculado; um resultado nulo com poder adequado também é resultado. |
| Aprovação ética demorada | Consultar o professor agora, antes de qualquer outra etapa do estudo. |
| Poucos marcos visíveis em algumas cenas | O modelo de campo tem 29 marcos, incluindo o círculo central e os arcos das áreas; escolher quadros-chave onde aparecem ao menos 6. |

## Pendências da equipe

- Abrir `paper/Artigo_Final.docx` no Word e conferir a paginação (8 páginas no
  LibreOffice, com cerca de um quarto da última página livre).
- Decidir se o artigo deve trazer também o *Abstract* em inglês: não está na
  lista de seções pedida e foi retirado para caber em 8 páginas.
