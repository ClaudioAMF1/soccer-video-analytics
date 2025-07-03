#!/usr/bin/env python3
"""
Script para aplicar correções rápidas e executar o Soccer Video Analytics
"""

import os
import shutil
import subprocess
import sys

def backup_file(filepath):
    """Faz backup de um arquivo"""
    if os.path.exists(filepath):
        backup_path = filepath + ".backup"
        shutil.copy2(filepath, backup_path)
        print(f"✅ Backup criado: {backup_path}")

def patch_draw_file():
    """Aplica patch no arquivo draw.py para corrigir o erro de textsize"""
    draw_file = "soccer/draw.py"
    
    if not os.path.exists(draw_file):
        print(f"❌ Arquivo {draw_file} não encontrado")
        return False
    
    # Fazer backup
    backup_file(draw_file)
    
    # Ler conteúdo atual
    with open(draw_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Substituições necessárias
    patches = [
        # Corrigir método textsize
        ('w, h = draw.textsize(text, font=font)', 'w, h = Draw.get_text_size(text, font)'),
        # Adicionar import necessário
        ('import PIL', 'import PIL\nfrom PIL import ImageDraw, ImageFont'),
    ]
    
    patched = False
    for old, new in patches:
        if old in content:
            content = content.replace(old, new)
            patched = True
            print(f"✅ Aplicado patch: {old[:30]}...")
    
    # Adicionar método get_text_size se não existir
    if 'def get_text_size(' not in content:
        get_text_size_method = '''
    @staticmethod
    def get_text_size(text: str, font: PIL.ImageFont = None) -> tuple:
        """
        Get text size compatible with different Pillow versions
        
        Parameters
        ----------
        text : str
            Text to measure
        font : PIL.ImageFont, optional
            Font to use
            
        Returns
        -------
        tuple
            (width, height) of text
        """
        if font is None:
            try:
                font = PIL.ImageFont.truetype("fonts/Gidole-Regular.ttf", size=20)
            except:
                font = PIL.ImageFont.load_default()
        
        # Try new method first (Pillow 8.0.0+)
        try:
            # Create temporary image to measure text
            temp_img = PIL.Image.new('RGB', (1, 1))
            temp_draw = PIL.ImageDraw.Draw(temp_img)
            
            # Use textbbox (newer method)
            if hasattr(temp_draw, 'textbbox'):
                bbox = temp_draw.textbbox((0, 0), text, font=font)
                return (bbox[2] - bbox[0], bbox[3] - bbox[1])
            # Use textsize (older method)
            elif hasattr(temp_draw, 'textsize'):
                return temp_draw.textsize(text, font=font)
            else:
                # Fallback: estimate based on font size
                if hasattr(font, 'size'):
                    return (len(text) * font.size * 0.6, font.size)
                else:
                    return (len(text) * 12, 16)  # Default estimate
                    
        except Exception as e:
            print(f"⚠️ Erro ao medir texto: {e}")
            # Fallback estimation
            return (len(text) * 10, 16)
'''
        
        # Inserir após a definição da classe Draw
        class_def = "class Draw:"
        if class_def in content:
            insert_pos = content.find(class_def) + len(class_def)
            content = content[:insert_pos] + get_text_size_method + content[insert_pos:]
            patched = True
            print("✅ Adicionado método get_text_size")
    
    if patched:
        # Salvar arquivo corrigido
        with open(draw_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Arquivo {draw_file} corrigido com sucesso!")
        return True
    else:
        print(f"ℹ️ Nenhuma correção necessária em {draw_file}")
        return True

def create_missing_folders():
    """Cria pastas necessárias se não existirem"""
    folders = ["videos", "models", "images", "fonts"]
    
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"📁 Pasta criada: {folder}/")
        else:
            print(f"✅ Pasta existe: {folder}/")

def check_video_file():
    """Verifica se o arquivo de vídeo existe"""
    video_file = "videos/Miami_X_Palmeiras.mp4"
    
    if os.path.exists(video_file):
        print(f"🎬 Vídeo encontrado: {video_file}")
        return True
    else:
        print(f"❌ Vídeo não encontrado: {video_file}")
        print("📋 Coloque seu vídeo na pasta videos/ com o nome Miami_X_Palmeiras.mp4")
        return False

def run_soccer_analytics():
    """Executa o sistema de análise tática"""
    cmd = [
        sys.executable, "run.py", 
        "--tactical", "--possession", "--passes",
        "--video", "videos/Miami_X_Palmeiras.mp4"
    ]
    
    print("🚀 Executando Soccer Video Analytics...")
    print(f"💻 Comando: {' '.join(cmd)}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        print("✅ Processamento concluído com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro durante a execução: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️ Processamento interrompido pelo usuário")
        return False

def main():
    print("🔧 Soccer Video Analytics - Correção e Execução Automática")
    print("=" * 60)
    
    # 1. Criar pastas necessárias
    print("\n1️⃣ Verificando estrutura de pastas...")
    create_missing_folders()
    
    # 2. Aplicar patches necessários
    print("\n2️⃣ Aplicando correções no código...")
    if not patch_draw_file():
        print("❌ Falha ao aplicar correções")
        return False
    
    # 3. Verificar vídeo
    print("\n3️⃣ Verificando arquivo de vídeo...")
    if not check_video_file():
        print("\n📋 Para continuar:")
        print("   1. Coloque seu vídeo em videos/Miami_X_Palmeiras.mp4")
        print("   2. Execute novamente: python quick_fix.py")
        return False
    
    # 4. Configurar ambiente
    print("\n4️⃣ Configurando ambiente...")
    os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib-config'
    print("✅ Variável MPLCONFIGDIR configurada")
    
    # 5. Executar análise
    print("\n5️⃣ Iniciando análise tática...")
    success = run_soccer_analytics()
    
    if success:
        print("\n🎉 SUCESSO! Análise tática concluída!")
        print("📊 Funcionalidades implementadas:")
        print("   ✅ Detecção contínua de jogadores")
        print("   ✅ Times com cores diferentes")
        print("   ✅ Linhas de formação entre jogadores")
        print("   ✅ Polígonos de formação dos times")
        print("   ✅ Rastro visual da bola")
        print("   ✅ Análise de posse de bola")
        print("   ✅ Contagem de passes")
        print("\n🎬 Vídeo de saída: videos/Miami_X_Palmeiras_out.mp4")
    else:
        print("\n❌ Falha na execução. Verifique os erros acima.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)