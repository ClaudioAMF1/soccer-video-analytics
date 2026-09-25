# Instrumentos de coleta

## 1. Perfil (antes do estudo)

1. Idade: ______
2. Com que frequência você assiste a jogos de futebol?
   ( ) nunca ( ) raramente ( ) algumas vezes por mês ( ) toda semana
3. De 1 (nenhum) a 5 (profissional), quanto você entende de tática no futebol? ___
   > Critério de inclusão: resposta igual ou inferior a 3.

## 2. Perguntas de compreensão (após cada clipe)

Três perguntas por clipe, adaptadas ao lance. As respostas são objetivas, com
gabarito definido **antes** da coleta a partir das posições de referência ou do
consenso de dois avaliadores. Nenhuma pergunta pode ser respondida lendo um
número exibido na tela. Registrar acerto (0/1) e tempo até a resposta.

**Modelo A — espaço livre.** "No momento em que o vídeo pausa, em qual destas
regiões havia mais espaço livre para a equipe atacante?" (mapa com quatro
regiões marcadas: A, B, C, D)

**Modelo B — equipe mais exposta.** "Qual das duas equipes estava mais
desorganizada na defesa durante o lance?" (Azul / Laranja / Nenhuma)

**Modelo C — desfecho.** "O lance terminou numa oportunidade clara de gol?"
(Sim / Não)

**Modelo D — antecipação.** O vídeo pausa antes do passe decisivo: "Para onde
a jogada tem mais chance de seguir?" (mapa com quatro regiões)

Após cada clipe: "Quão confiante você está nas suas respostas?" (1 a 5)

## 3. Carga de trabalho: RTLX (após cada bloco)

NASA-TLX na versão sem pesos (Hart e Staveland, 1988). Marque de 0 a 100:

| Dimensão | Pergunta | 0 | 100 |
| :--- | :--- | :--- | :--- |
| Exigência mental | Quanto esforço mental foi necessário para entender os lances? | muito baixa | muito alta |
| Exigência física | Quanto esforço físico foi necessário? | muito baixa | muito alta |
| Exigência temporal | Quanta pressão de tempo você sentiu? | muito baixa | muito alta |
| Desempenho | Quão bem-sucedido(a) você foi em entender os lances? | perfeito | fracasso |
| Esforço | Quanto você precisou se esforçar para atingir seu desempenho? | muito baixo | muito alto |
| Frustração | Quão inseguro(a), irritado(a) ou estressado(a) você se sentiu? | muito baixa | muito alta |

> Atenção à escala de desempenho: é invertida (0 = perfeito), para que em todas
> as dimensões um valor maior signifique carga maior. O RTLX é a média simples
> das seis.

## 4. Encerramento

1. Qual das duas formas de apresentação ajudou mais a entender o jogo?
   ( ) a primeira ( ) a segunda ( ) nenhuma diferença
2. O que mais ajudou ou atrapalhou? ______________________________

## Formato dos arquivos para `estudo/analise.py`

`respostas.csv`, uma linha por pergunta respondida:

```
participante,grupo,condicao,clipe,questao,acerto,tempo_s
P01,G1,estatica,c1,A,1,8.4
```

`carga.csv`, uma linha por bloco:

```
participante,condicao,mental,fisica,temporal,desempenho,esforco,frustracao
P01,estatica,65,10,40,50,60,35
```

`condicao` assume `estatica` ou `dinamica`.
