import os
from PIL import Image, ImageDraw

def create_app_icon():
    os.makedirs("assets", exist_ok=True)
    
    # Cria uma imagem de alta resolução (256x256) com fundo transparente
    size = (256, 256)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Desenha fundo quadrado arredondado com gradiente escuro e borda ciano
    # Cantos arredondados simulados
    bg_box = [12, 12, 244, 244]
    draw.rounded_rectangle(bg_box, radius=48, fill=(18, 24, 38, 255), outline=(56, 189, 248, 255), width=6)

    # 2. Círculo interno com brilho gradiente
    inner_box = [32, 32, 224, 224]
    draw.rounded_rectangle(inner_box, radius=38, fill=(15, 23, 42, 255))

    # 3. Lente da Lupa de Busca (Círculo azul/ciano)
    lens_box = [60, 60, 160, 160]
    draw.ellipse(lens_box, outline=(56, 189, 248, 255), width=14, fill=(37, 99, 235, 120))

    # 4. Cabo da Lupa
    draw.line([(140, 140), (195, 195)], fill=(56, 189, 248, 255), width=18)
    draw.line([(142, 142), (193, 193)], fill=(14, 165, 233, 255), width=12)

    # 5. Ícone de Play / Raio no centro da lente
    play_triangle = [(92, 85), (92, 135), (135, 110)]
    draw.polygon(play_triangle, fill=(255, 255, 255, 255))

    # Salva como PNG de alta resolução
    png_path = os.path.join("assets", "icon.png")
    img.save(png_path, format="PNG")

    # Salva como ICO com múltiplos tamanhos (256, 128, 64, 48, 32, 16)
    ico_path = os.path.join("assets", "icon.ico")
    img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])

    print(f"Ícones gerados com sucesso:\n- {png_path}\n- {ico_path}")

if __name__ == "__main__":
    create_app_icon()
