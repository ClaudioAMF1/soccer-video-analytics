#!/bin/bash

echo "🔧 Corrigindo dependências do Soccer Video Analytics"
echo "===================================================="

# Ativar ambiente virtual se não estiver ativo
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "📦 Ativando ambiente virtual..."
    source venv/bin/activate
fi

# Configurar matplotlib para evitar erros de permissão
echo "🎨 Configurando matplotlib..."
export MPLCONFIGDIR=/tmp/matplotlib-config
mkdir -p /tmp/matplotlib-config

echo "📚 Instalando dependências faltantes..."

# Instalar requests (necessário para YOLOv5)
pip install requests

# Instalar outras dependências que podem estar faltando
pip install urllib3
pip install psutil

# Instalar dependências específicas do YOLOv5
pip install ultralytics

# Verificar se todas as dependências estão instaladas
echo "🔍 Verificando dependências..."

python3 -c "
import sys

def check_import(module_name, friendly_name=None):
    if friendly_name is None:
        friendly_name = module_name
    try:
        __import__(module_name)
        print(f'✅ {friendly_name}: OK')
        return True
    except ImportError as e:
        print(f'❌ {friendly_name}: ERRO - {e}')
        return False

success = True
success &= check_import('torch', 'PyTorch')
success &= check_import('cv2', 'OpenCV')
success &= check_import('norfair', 'Norfair')
success &= check_import('numpy', 'NumPy')
success &= check_import('PIL', 'Pillow')
success &= check_import('scipy', 'SciPy')
success &= check_import('requests', 'Requests')
success &= check_import('urllib3', 'urllib3')

if success:
    print('\\n🎉 Todas as dependências estão OK!')
else:
    print('\\n❌ Algumas dependências estão faltando. Execute novamente ou instale manualmente.')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dependências corrigidas com sucesso!"
    echo ""
    echo "🎯 Agora você pode executar:"
    echo "   export MPLCONFIGDIR=/tmp/matplotlib-config"
    echo "   python run.py --tactical --possession --video videos/Miami_X_Palmeiras.mp4"
else
    echo "❌ Erro ao verificar dependências."
    exit 1
fi
