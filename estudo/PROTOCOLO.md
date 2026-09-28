# Protocolo do estudo com usuários (experimento E6)

## Pergunta

Espectadores leigos compreendem melhor uma jogada quando o vídeo gravado vem
acompanhado da sobreposição narrativa dinâmica do que quando vem acompanhado de
um mapa tático estático, que é o recurso gráfico usual das transmissões?

## Hipóteses

| | Hipótese | Medida |
| :--- | :--- | :--- |
| H1 | A sobreposição dinâmica aumenta a acurácia das respostas de compreensão | proporção de acertos |
| H2 | A sobreposição dinâmica reduz o tempo de resposta | mediana do tempo, em segundos |
| H3 | A sobreposição dinâmica reduz a carga de trabalho percebida | RTLX (NASA-TLX sem pesos), 0 a 100 |

## Delineamento

**Intrassujeitos, duas condições.** Cada participante passa pelas duas:

- **Estática (controle):** vídeo do lance e, ao lado, um mapa tático fixo com
  as posições no instante decisivo.
- **Dinâmica (tratamento):** o mesmo tipo de lance no player (`web/`), com
  zonas de controle, forma da equipe e legenda narrativa.

**Estímulos.** Doze clipes de 10 a 15 segundos de jogos gravados, divididos
em dois conjuntos equivalentes (S1 e S2, seis clipes cada), com a mesma
distribuição de desfechos (finalização, perda de posse, circulação). Três
perguntas por clipe resultam em **18 respostas por condição**, número definido
pela simulação de poder abaixo.

**Contrabalanceamento.** Quatro grupos cruzam ordem das condições e conjunto de
clipes, eliminando os efeitos de aprendizagem e de dificuldade dos clipes:

| Grupo | 1º bloco | 2º bloco |
| :--- | :--- | :--- |
| G1 | Estática com S1 | Dinâmica com S2 |
| G2 | Estática com S2 | Dinâmica com S1 |
| G3 | Dinâmica com S1 | Estática com S2 |
| G4 | Dinâmica com S2 | Estática com S1 |

## Participantes

**Meta: 24 pessoas** (seis por grupo). O cálculo de poder, para teste pareado
bicaudal com alfa de 0,05 e poder de 0,80, ajustado pela eficiência relativa
do Wilcoxon (3/π):

| Efeito (dz) | Sem correção | Com Holm sobre 3 hipóteses |
| :--- | ---: | ---: |
| grande (0,8) | 16 | 21 |
| médio (0,5) | 36 | 48 |

Com 24 participantes o estudo detecta um efeito grande mesmo após a correção
para múltiplas comparações.

**O número de perguntas importa tanto quanto o de pessoas.** A acurácia de
cada participante é uma proporção de acertos em itens binários, e com poucos
itens ela é ruidosa. Simulação (1.000 repetições, ganho de 12 pontos
percentuais, Holm no pior caso):

| Participantes | 9 perguntas por condição | 18 perguntas | 27 perguntas |
| ---: | ---: | ---: | ---: |
| 16 | 0,28 | 0,57 | 0,79 |
| 24 | 0,50 | **0,83** | 0,96 |
| 32 | 0,66 | 0,94 | 0,99 |

Com 9 perguntas o estudo teria chance de cara ou coroa de detectar o efeito;
com 18, supera o poder de 0,80. Um efeito médio exigiria o dobro, fora do alcance
deste trabalho; se o resultado for nulo, isso deve ser reportado como
limitação de poder, e não como ausência de efeito.

**Inclusão:** 18 anos ou mais; autoavaliação de conhecimento tático de futebol
igual ou inferior a 3 numa escala de 1 a 5. O público-alvo é o espectador
leigo, e especialistas responderiam a partir do conhecimento prévio.

## Procedimento (cerca de 35 minutos)

1. Termo de consentimento (`TCLE_modelo.md`) e questionário de perfil.
2. Treino com um clipe que não entra na análise, na primeira condição do grupo.
3. **Bloco 1:** seis clipes. Após cada um, três perguntas de compreensão
   (`questionario.md`), com registro de acerto e tempo.
4. RTLX do bloco 1.
5. **Bloco 2:** idem, na outra condição, com o outro conjunto de clipes.
6. RTLX do bloco 2.
7. Preferência declarada e comentário aberto.

## Ameaça à validade que o protocolo precisa neutralizar

Se o gabarito das perguntas viesse dos próprios números exibidos pela
sobreposição, a condição dinâmica venceria por simples leitura da tela, e o
estudo mediria a legibilidade de um número, não a compreensão da jogada. Por
isso:

- as perguntas tratam da **jogada** (onde havia espaço livre, que equipe estava
  mais exposta, se o lance terminou numa chance clara), nunca de um valor que a
  interface mostre literalmente;
- o gabarito vem das **posições de referência** (SoccerNet) ou, em clipes sem
  referência, do consenso de dois avaliadores com conhecimento tático,
  definido antes da coleta;
- a interface não exibe percentuais durante o estudo: a legenda é usada sem a
  frase "controla N% do campo".

## Análise

Por participante e condição: proporção de acertos, mediana do tempo e RTLX.
Comparação pareada pelo **teste de postos sinalizados de Wilcoxon**, com
correção de **Holm** sobre as três hipóteses. Tamanho de efeito pela
**correlação rank-biserial pareada**. Reportam-se medianas e intervalos
interquartis, nunca apenas o valor-p.

```bash
python -m estudo.analise --respostas respostas.csv --carga carga.csv
python -m estudo.analise --simular 24   # demonstração com dados sintéticos
```

## Ética

Pesquisa com participantes humanos pode exigir apreciação por Comitê de Ética
em Pesquisa (CEP), via Plataforma Brasil. Para uma atividade de disciplina,
em geral não é necessária; para publicação, pode ser. **Confirmar com o
professor antes de recrutar qualquer participante**, porque a tramitação no
CEP leva semanas.

Independentemente disso: participação voluntária, TCLE assinado, dados
anonimizados por código de participante, nenhum dado de identificação no
mesmo arquivo das respostas, e direito de desistência a qualquer momento sem
justificativa.
