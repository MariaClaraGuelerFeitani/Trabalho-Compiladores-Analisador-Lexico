from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
TAMANHOS = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
LADO_MAXIMO = max(lado for lado, _ in TAMANHOS)


def main() -> int:
    origem = RAIZ / "img" / "racoon.png"
    destino = RAIZ / "img" / "racoon.ico"

    imagem = Image.open(origem).convert("RGBA")
    recorte = imagem.crop(imagem.getbbox())
    recorte.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.Resampling.LANCZOS)

    deslocamento = ((LADO_MAXIMO - recorte.width) // 2, (LADO_MAXIMO - recorte.height) // 2)
    quadrado = Image.new("RGBA", (LADO_MAXIMO, LADO_MAXIMO), (0, 0, 0, 0))
    quadrado.alpha_composite(recorte, deslocamento)

    quadrado.save(destino, format="ICO", sizes=TAMANHOS)
    print(
        f"{destino.name}: {quadrado.size[0]}x{quadrado.size[1]} "
        f"(arte {recorte.size[0]}x{recorte.size[1]}), {len(TAMANHOS)} tamanhos"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
