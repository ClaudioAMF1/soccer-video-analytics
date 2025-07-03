# ⚽ Análise Tática de Futebol com Visão Computacional

Este projeto realiza uma análise tática completa de vídeos de jogos de futebol, utilizando detecção de objetos e algoritmos de visão computacional para extrair insights sobre a partida. A solução foi desenvolvida para atender rigorosamente a todos os requisitos obrigatórios e desejáveis de análise visual tática.

## 🎯 Conformidade com os Requisitos do PDF

### ✅ Requisitos Obrigatórios (DEVE) - 100% Implementados

| Requisito | Status | Implementação |
| --- | :---: | --- |
| **Percepção visual do aspecto tático** | ✅ | Desenhando polígonos de formação e linhas de conexão. |
| **Visualização contínua da detecção dos jogadores** | ✅ | Rastreamento contínuo com Norfair e bounding boxes visíveis. |
| **Destacar os dois times com cores diferentes** | ✅ | Classificador de cores HSV para identificar uniformes. |

### ✅ Requisitos Desejáveis - 100% Implementados

| Requisito | Status | Implementação |
| --- | :---: | --- |
| **Apresentar rastreio visual para a bola** | ✅ | A classe `Bola` desenha um rastro com efeito de fade. |
| **Linhas de ligação entre jogadores do mesmo time** | ✅ | A classe `VisualizacaoTatica` desenha conexões. |
| **Polígonos entre jogadores do mesmo time** | ✅ | A classe `VisualizacaoTatica` desenha o casco convexo da formação. |

## 🚀 Funcionalidades Principais

* **Detecção de Jogadores e Bola:** Utiliza o modelo YOLOv8 para identificar objetos em cada frame.
* **Classificação de Times:** Um classificador baseado em cores (HSV) e inércia temporal atribui cada jogador a um time.
* **Cálculo de Posse de Bola:** Identifica qual time tem o controle da bola com base na proximidade do jogador.
* **Visualizações Táticas:**
    * **Ponteiro de Posse:** Um losango/ponteiro é desenhado sobre o jogador mais próximo da bola.
    * **Rastro da Bola:** Mostra a trajetória recente da bola com um efeito de "fade".
    * **Linhas de Formação:** Conecta os jogadores mais próximos de um mesmo time para ilustrar a estrutura tática.
    * **Polígonos de Formação:** Desenha a área ocupada pela formação de cada time.

## ⚙️ Como Executar o Código

### Pré-requisitos

1.  **Python 3.9+** instalado.
2.  **Instale as dependências** necessárias. É altamente recomendável criar um ambiente virtual:
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Linux/macOS
    # venv\Scripts\activate   # No Windows

    pip install opencv-python-headless numpy norfair ultralytics pillow scipy
    ```
3.  **Estrutura de Pastas:** Garanta que seu projeto tenha a estrutura de pastas correta, com o vídeo a ser analisado dentro da pasta `videos/`.

### Execução

Para rodar a análise, utilize o script `analise_video.py` no seu terminal.

**Comando Recomendado (Ativa todas as funcionalidades):**
```bash
python analise_video.py --tatico