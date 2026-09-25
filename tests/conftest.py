import sys
from pathlib import Path

# Permite executar `pytest` a partir da raiz sem instalar o pacote.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
