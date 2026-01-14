#!/usr/bin/env python3
"""
Gera ícones PNG para a extensão do navegador.
Requer: pip install Pillow
"""

from PIL import Image, ImageDraw
import os

# Diretório dos ícones
ICONS_DIR = os.path.join(os.path.dirname(__file__), 'icons')
os.makedirs(ICONS_DIR, exist_ok=True)

# Tamanhos dos ícones
SIZES = [16, 32, 48, 128]

# Cores
BG_COLOR = (102, 126, 234)  # #667eea
ARROW_COLOR = (255, 255, 255)

def create_icon(size):
    """Cria um ícone de download com o tamanho especificado."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fundo circular com gradiente simulado
    padding = size // 8
    draw.ellipse(
        [padding, padding, size - padding, size - padding],
        fill=BG_COLOR
    )

    # Desenha seta de download
    center_x = size // 2
    center_y = size // 2

    # Tamanho proporcional
    arrow_width = size // 4
    arrow_height = size // 3
    line_width = max(1, size // 10)

    # Linha vertical da seta
    draw.line(
        [(center_x, center_y - arrow_height // 2),
         (center_x, center_y + arrow_height // 4)],
        fill=ARROW_COLOR,
        width=line_width
    )

    # Ponta da seta (triângulo)
    triangle_size = arrow_width // 2
    points = [
        (center_x - triangle_size, center_y),
        (center_x + triangle_size, center_y),
        (center_x, center_y + arrow_height // 2)
    ]
    draw.polygon(points, fill=ARROW_COLOR)

    # Linha horizontal (bandeja)
    tray_y = center_y + arrow_height // 2 + line_width
    draw.line(
        [(center_x - arrow_width, tray_y),
         (center_x + arrow_width, tray_y)],
        fill=ARROW_COLOR,
        width=line_width
    )

    return img

def main():
    print("Gerando ícones da extensão...")

    for size in SIZES:
        icon = create_icon(size)
        filepath = os.path.join(ICONS_DIR, f'icon{size}.png')
        icon.save(filepath, 'PNG')
        print(f"  Criado: icon{size}.png")

    print(f"\nÍcones salvos em: {ICONS_DIR}")
    print("Extensão pronta para ser carregada no navegador!")

if __name__ == '__main__':
    main()
