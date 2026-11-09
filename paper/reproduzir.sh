#!/usr/bin/env bash
# Reproduz todos os números e figuras do artigo final a partir do SoccerNet-GSR.
#
# Uso: bash paper/reproduzir.sh [pasta-do-conjunto-de-teste]
# Tempo aproximado em CPU de 4 núcleos: 1h30 (a detecção é a etapa mais lenta).
set -euo pipefail

DADOS="${1:-data/SoccerNetGS/gamestate-2024/test}"
SAIDA="paper/dados"
MODELO="${MODELO:-yolov8x.pt}"

if [ ! -d "$DADOS" ]; then
  echo "Baixando o SoccerNet-GSR (partição de teste, cerca de 9 GB)..."
  python - <<'PY'
from SoccerNet.Downloader import SoccerNetDownloader
SoccerNetDownloader(LocalDirectory="data/SoccerNetGS").downloadDataTask(task="gamestate-2024", split=["test"])
PY
  unzip -q -o data/SoccerNetGS/gamestate-2024/test.zip -d data/SoccerNetGS/gamestate-2024/test
fi

mkdir -p "$SAIDA"
python -m experiments.caracterizacao   --dados "$DADOS" --saida "$SAIDA"
python -m experiments.e5_real          --dados "$DADOS" --saida "$SAIDA"
python -m experiments.e2_registro_real --dados "$DADOS" --saida "$SAIDA"
python -m experiments.narrativa_real   --dados "$DADOS" --saida "$SAIDA"
python -m experiments.e1_deteccao_real --dados "$DADOS" --saida "$SAIDA" --modelo "$MODELO"
python -m experiments.figura_sensibilidade --e5 "$SAIDA/e5_real.csv" --e2 "$SAIDA/e2_registro_real.csv" \
       --saida paper/figuras/sensibilidade_real.png
python paper/gerar_artigo.py --dados "$SAIDA" --saida paper/Artigo_Final.docx
