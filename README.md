# ⚽ Análise Tática de Futebol com Visão Computacional

![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

Este projeto oferece uma solução completa para a análise tática de partidas de futebol, utilizando visão computacional e deep learning para transformar um vídeo de jogo numa fonte rica de insights visuais. O sistema foi desenhado para ser uma ferramenta de **IA Confiável e Interpretável**, que torna conceitos táticos complexos acessíveis a qualquer espectador, respondendo diretamente ao desafio proposto na "estória do cliente" do documento do trabalho.

## Índice

1.  [O Desafio: A "Estória do Cliente"](#o-desafio-a-estória-do-cliente)
2.  [Funcionalidades e Requisitos Atendidos](#funcionalidades-e-requisitos-atendidos)
3.  [Como Funciona: O Pipeline de Análise](#como-funciona-o-pipeline-de-análise)
4.  [Tecnologias e Arquitetura](#tecnologias-e-arquitetura)
5.  [Instruções de Execução](#instruções-de-execução)
6.  [Exemplo do Resultado](#exemplo-do-resultado)

---

## O Desafio: A "Estória do Cliente"

O ponto de partida foi a necessidade de um utilizador leigo em futebol que, ao ouvir os comentadores a falar sobre "esquemas táticos", "organização coletiva" e "posse de bola", não conseguia visualizar esses conceitos no jogo. O objetivo deste projeto é ser a ferramenta que preenche essa lacuna, traduzindo a linguagem do futebol em insights visuais claros e compreensíveis.

## Funcionalidades e Requisitos Atendidos

O sistema implementa todos os requisitos obrigatórios e desejáveis do documento de especificação, transformando dados brutos em análise tática.

| Requisito do PDF | Funcionalidade Implementada | Insight Tático Oferecido |
| :--- | :--- | :--- |
| **Percepção Tática Coletiva** | **Polígonos de Formação** | Mostra a **compactação** e a área de ocupação de cada equipa. Uma área menor indica um bloco defensivo, enquanto uma área maior sugere uma postura ofensiva. |
| **Deteção Contínua dos Jogadores** | **Caixas Delimitadoras com Rastreamento** | Garante que cada jogador seja identificado e seguido continuamente, permitindo a análise de movimento individual. |
| **Equipas com Cores Diferentes** | **Classificação de Equipas por Cor** | Atribui a cor correta a cada jogador, permitindo a diferenciação visual imediata entre as equipas e o árbitro. |
| **Rastreio Visual da Bola** | **Rasto da Bola Dinâmico** | A trajetória da bola é desenhada com um rasto, cuja cor muda com a posse, ilustrando a **dinâmica e velocidade** da jogada. |
| **Linhas de Ligação** | **Linhas de Conexão Tática** | Liga os jogadores mais próximos, revelando a **estrutura de apoio** e as opções de passe imediatas, um indicador de coesão da equipa. |
| _(Funcionalidade Extra)_ | **Painel de Posse de Bola** | Apresenta uma métrica quantitativa chave em tempo real, indicando qual equipa está a controlar o jogo. |
| _(Funcionalidade Extra)_ | **Ponteiro de Posse** | Um ponteiro visual destaca o jogador com a posse da bola, focando a atenção do espectador no epicentro da jogada. |

## Como Funciona: O Pipeline de Análise

O projeto opera como um **algoritmo único e coeso**, orquestrado pelo script `analise_video.py`. Para cada frame do vídeo, o sistema executa o seguinte pipeline:

1.  **Deteção de Objetos:** Utiliza o modelo YOLOv8 para identificar a localização de todos os jogadores e da bola no frame.
2.  **Rastreamento (Tracking):** O algoritmo Norfair recebe as deteções e atribui um ID único a cada jogador, seguindo-os ao longo dos frames.
3.  **Classificação de Equipas:** Cada jogador detetado tem o seu uniforme analisado pelo Classificador HSV, que o atribui a uma equipa (ex: "Inter Miami", "Palmeiras") com base na cor predominante. Um filtro de inércia estabiliza esta classificação.
4.  **Atualização da Lógica de Jogo:** O estado da partida é atualizado. O sistema verifica qual jogador classificado está mais próximo da bola para determinar a **posse de bola**.
5.  **Geração das Visualizações:** Com base no estado atual da partida, as camadas de visualização são desenhadas sobre o frame: polígonos, linhas, rasto da bola e o painel de posse.
6.  **Gravação:** O frame enriquecido é gravado no ficheiro de vídeo de saída.

## Tecnologias e Arquitetura

O código foi organizado como uma **biblioteca modular**, promovendo a clareza e a reutilização do código.

-   **Linguagem:** Python 3.9+
-   **Deep Learning / Visão Computacional:**
    -   **Ultralytics (YOLOv8):** Para a deteção de objetos de alta performance.
    -   **OpenCV:** Para manipulação de imagens e processamento de vídeo.
    -   **Norfair:** Para o rastreamento leve e eficiente dos jogadores e da bola.
-   **Outras Bibliotecas:** NumPy, Pillow, SciPy.

A estrutura do projeto é a seguinte:

```
soccer-video-analytics/
├── 📂 config/          # Ficheiros de configuração (filtros de cores)
├── 📂 inference/        # Classes para deteção e classificação (IA)
├── 📂 soccer/           # Classes que representam a lógica do jogo (Partida, Jogador)
├── 📂 utils/            # Funções auxiliares
├── 📂 videos/           # Vídeos de entrada
└── 📜 analise_video.py  # O script principal que orquestra tudo
```

## Instruções de Execução

### 1. Pré-requisitos
-   Garanta que tem o Python 3.9 ou superior instalado.
-   Instale todas as dependências necessárias com um único comando:
    ```bash
    pip install opencv-python ultralytics norfair numpy pillow scipy
    ```

### 2. Configuração
-   Coloque o seu ficheiro de vídeo (ex: `Miami_X_Palmeiras.mp4`) dentro da pasta `videos/`.

### 3. Execução
Para executar a análise com **todas as funcionalidades visuais ativadas**, utilize o seguinte comando no terminal:

```bash
python analise_video.py --tatico
```

O vídeo processado será guardado na pasta raiz do projeto com o sufixo `_out.mp4`.


## Detalhes Técnicos

### Detecção de Objetos com YOLOv8

- **O que é?** Usamos o **YOLOv8**, um modelo de *deep learning* de última geração, para a tarefa de detecção de objetos. Ele é responsável por encontrar e desenhar as caixas delimitadoras ao redor dos jogadores e da bola.
- **Dataset:** O modelo utilizado (`yolov8x.pt`) é **pré-treinado no COCO Dataset**, um enorme banco de dados de imagens que inclui as classes `person` (para os jogadores e árbitro) e `sports ball` (para a bola). Isso nos dá uma base de detecção robusta sem a necessidade de treinar um modelo do zero, otimizando o tempo de desenvolvimento.

### Classificação de Times com Filtro HSV

- **O que é?** Para separar os jogadores por time, adotamos uma abordagem **transparente e eficiente**: um classificador baseado em faixas de cor no espaço **HSV (Hue, Saturation, Value)**. 
- **Por que HSV?** Diferente do RGB, o HSV isola a matiz da cor (H) da sua intensidade e brilho (S e V). Isso torna a identificação de cores muito mais robusta a variações de iluminação no campo.
- **Como Funciona:** Definimos as faixas de cor para cada uniforme (ex: rosa para um time, branco/verde para outro) e contamos os pixels correspondentes na região do torso de cada jogador. O time com a maior contagem de pixels vence. Essa abordagem é **interpretável**, pois a regra de decisão é clara e não uma "caixa-preta".
- **Inércia Temporal:** Para estabilizar a classificação e evitar que um jogador mude de time por uma sombra momentânea, utilizamos um **Classificador de Inércia**, que considera o histórico recente de classificações para tomar a decisão final.

### Configuração de Filtros de Cores

Exemplo dos filtros de cor (HSV) definidos no arquivo `config/filtros_cores.py`:

```python
rosa = {"name": "rosa", "lower_hsv": (145, 60, 100), "upper_hsv": (175, 255, 255)}
branco = {"name": "branco", "lower_hsv": (0, 0, 180), "upper_hsv": (179, 30, 255)}
verde = {"name": "verde", "lower_hsv": (40, 40, 40), "upper_hsv": (80, 255, 255)}

filtro_inter_miami = {"name": "Inter Miami", "colors": [rosa]}
filtro_palmeiras = {"name": "Palmeiras", "colors": [branco, verde]}
```

## Análise das Métricas de Desempenho

O desempenho do sistema é medido pela **qualidade e clareza dos insights visuais** gerados. Cada elemento adicionado ao vídeo é uma métrica que ajuda a contar a história tática do jogo.

- **Painel de Posse de Bola:** Oferece uma métrica quantitativa clara de qual time está controlando o jogo.
- **Ponteiro de Posse:** Identifica inequivocamente qual jogador está com a bola, focando a atenção do espectador.
- **Rastro da Bola:** Indica a **dinâmica e velocidade** do jogo. Um rastro longo e rápido pode indicar um contra-ataque ou um lançamento. A cor do rastro indica qual time realizou a jogada.
- **Linhas de Conexão:** Demonstram a **coesão** de um time. Linhas curtas indicam um time compacto, enquanto linhas longas podem indicar um time espaçado.
- **Polígonos de Formação:** A **área** deste polígono é uma métrica direta da **compactação** do time. Uma área menor significa que o time está jogando de forma mais fechada e defensiva, enquanto uma área maior sugere uma postura mais ofensiva e expansiva.

## Conclusão

Este projeto cumpre com sucesso todos os requisitos obrigatórios e desejáveis, entregando uma ferramenta poderosa para a análise tática de futebol. A solução é robusta, bem organizada e atende diretamente à necessidade de um usuário que busca compreender visualmente as dinâmicas de uma partida, com clareza e credibilidade. A utilização de técnicas interpretáveis como o classificador HSV, aliada a modelos de ponta como o YOLOv8, demonstra uma abordagem equilibrada e alinhada aos princípios de uma IA Confiável.

## Trabalho Final

**Alunos:** *Andreia, Claudio Filho, Kelwin Menezes, Felipe Pereira, Laura Menezes, Lucas Ungarelli, Pedro Araújo*  
**Disciplina:** Processamento Inteligente de Imagens Aeroespaciais  
**Universidade:** *IDP*  
**Ano:** 2025

---

*Este projeto foi desenvolvido como trabalho final da disciplina de Processamento Inteligente de Imagens Aeroespaciais, demonstrando a aplicação prática de técnicas de visão computacional e deep learning na análise esportiva.*
