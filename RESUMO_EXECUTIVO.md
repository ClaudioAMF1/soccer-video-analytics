# Resumo executivo

**Projeto:** Do Pixel à Narrativa: Visualizações Confiáveis de Controle de
Espaço em Transmissões de Futebol para o Público Geral
**Equipe:** Claudio Meireles Filho, Felipe Pereira, Lucas Ungarelli, Pedro Araújo (IDP)
**Situação em:** setembro de 2026

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

## Primeiros resultados

**1. Informação coletiva é muito mais robusta que individual.** Simulamos
erros de medição de 0 a 3 metros e medimos quanto cada informação se distorce.
Com limite de tolerância de 5%:

| Informação | Deixa de ser confiável a partir de |
| :--- | ---: |
| Qual jogador domina cada ponto | 1,2 m de erro |
| Forma da equipe | 2,0 m de erro |
| Zonas de controle da equipe | não atingiu o limite até 2,9 m |

A informação individual se distorce cerca de **5 vezes mais rápido**. Por isso a
interface mostra zonas e formas de equipe, e esconde "qual jogador domina cada
ponto", explicando ao espectador o motivo.

**2. Anotar dois quadros vizinhos reduz o erro.** Combinar a estimativa das
duas anotações mais próximas reduziu o erro médio de 0,85 m para 0,50 m (menos
41%), em simulação.

**3. O estudo precisa de mais perguntas, não só de mais pessoas.** Com 24
participantes e 9 perguntas cada, a chance de detectar uma melhora real seria
de 50%. Com 18 perguntas, sobe para 83%. O protocolo já foi ajustado para 18.

> Esses números vêm de simulações. Servem para decidir o desenho do sistema e
> do estudo, mas precisam ser confirmados com dados reais antes de entrarem no
> artigo como resultado principal.

## O que falta

| Item | Depende de |
| :--- | :--- |
| Baixar o SoccerNet e rodar os experimentos E1 a E4 com dados reais | acesso ao conjunto de dados (gratuito, exige cadastro) |
| Medir o erro real de registro (E2), que define o que o player pode mostrar | E1 a E4 |
| Selecionar os 12 clipes do estudo e definir o gabarito | jogos gravados + dois avaliadores |
| Recrutar 24 participantes e aplicar o estudo | confirmação sobre o Comitê de Ética |
| Escrever Resultados, Discussão e Conclusão | todos os itens acima |

## Próximos passos sugeridos

1. **Divulgar o formulário exploratório** (`estudo/formulario_exploratorio.md`),
   que é anônimo e pode começar antes de tudo; meta de 30 respostas por grupo.
2. **Confirmar com o professor** se o estudo com pessoas exige aprovação do
   Comitê de Ética. Se exigir, a tramitação leva semanas: é o item de prazo
   mais longo.
3. **Baixar o SoccerNet** e rodar o pipeline sobre uma sequência, para ver o
   sistema funcionando com dados reais.
4. **Anotar os quadros-chave** de um jogo gravado com `anotar.py` e gerar o
   primeiro arquivo real com `extrair.py`.
5. **Selecionar os clipes** do estudo em paralelo aos experimentos.

## Riscos

| Risco | Como reduzir |
| :--- | :--- |
| Erro real de registro maior que o simulado | A regra de exibição se ajusta sozinha: esconde mais coisas. O resultado continua publicável, com a interface mais simples. |
| Estudo sem diferença significativa | O protocolo já tem poder calculado; um resultado nulo com poder adequado também é resultado. |
| Aprovação ética demorada | Consultar o professor agora, antes de qualquer outra etapa do estudo. |
| Poucos marcos visíveis em algumas cenas | O modelo de campo tem 29 marcos, incluindo o círculo central e os arcos das áreas; escolher quadros-chave onde aparecem ao menos 6. |

## Pendências da equipe

- O modelo SBC pede e-mail dos autores, em fonte Courier New; a versão atual
  mostra só a instituição.
- Confirmar se a primeira entrega aceita a mudança de título e de foco em
  relação à versão anterior do artigo.
