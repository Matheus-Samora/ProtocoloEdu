"""
Módulo de Sanitização e Otimização de Imagens para o Protocolo.
Suporte total a fotos de celular (iPhone HEIC, Android JPG/PNG) e correção de orientação.
"""

import io
import logging
from typing import Tuple, Dict, Any, Optional
from PIL import Image, ImageOps

logger = logging.getLogger("MEDIA_SANITIZER")

# Tentativa segura de registro do suporte HEIC (iPhones da Apple)
HEIC_SUPPORTED = False
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORTED = True
    logger.info("Suporte nativo a imagens HEIC (Apple iPhone) ativado com sucesso.")
except ImportError:
    logger.warning("Biblioteca 'pillow-heif' não encontrada. Imagens .HEIC precisarão ser convertidas previamente.")

# Proteção contra Decompression Bomb DoS (limite de 50 Megapixels)
Image.MAX_IMAGE_PIXELS = 50_000_000
MAX_OCR_DIMENSION = 2500  # pixels
JPEG_QUALITY = 85         # Excelente balanço entre qualidade nítida e tamanho reduzido


class ImageSanitizer:
    """Sanitiza, rotaciona e converte qualquer imagem para JPEG limpo (RGB)."""

    @staticmethod
    def is_heic(header_bytes: bytes, filename_hint: str = "") -> bool:
        """Verifica se o arquivo é do formato HEIC/HEIF (inspeção de assinatura ISO-BMFF)."""
        if len(header_bytes) >= 12:
            brand = header_bytes[4:12]
            if any(sig in brand for sig in (b'ftypheic', b'ftypheix', b'ftypmif1', b'ftypmsf1', b'ftyphevc')):
                return True
        return False

    @classmethod
    def sanitize_image(cls, file_bytes: bytes, filename_hint: str = "") -> Tuple[bytes, str, Dict[str, Any]]:
        """
        Recebe bytes de imagem em qualquer formato e produz um JPEG otimizado e rotacionado.

        Returns:
            Tuple[bytes_limpos, mime_type, metadados]
        """
        metadata = {
            "original_size": len(file_bytes),
            "converted_from": filename_hint.split('.')[-1].lower() if '.' in filename_hint else "unknown",
            "heic_detected": False,
            "was_resized": False
        }

        header = file_bytes[:16]
        if cls.is_heic(header, filename_hint):
            metadata["heic_detected"] = True
            if not HEIC_SUPPORTED:
                raise ValueError("Arquivo HEIC detectado, mas a biblioteca 'pillow-heif' não está instalada no servidor.")

        try:
            stream_in = io.BytesIO(file_bytes)
            with Image.open(stream_in) as img:
                # 1. Corrige orientação EXIF (comum em celulares que salvam foto na vertical com tag de rotação)
                img = ImageOps.exif_transpose(img) or img

                # 2. Converte modos de cor exóticos para RGB padrão
                if img.mode not in ("RGB", "L"):
                    # Remove canal Alpha (RGBA) preenchendo fundo branco
                    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode != "RGBA":
                            img = img.convert("RGBA")
                        bg.paste(img, mask=img.split()[3])
                        img = bg
                    else:
                        img = img.convert("RGB")
                elif img.mode == "L":
                    # Grayscale para RGB
                    img = img.convert("RGB")

                width, height = img.size
                metadata["original_dimensions"] = (width, height)

                # 3. Redimensionamento inteligente se foto for gigantesca (ex: 8000x6000)
                if max(width, height) > MAX_OCR_DIMENSION:
                    scale = MAX_OCR_DIMENSION / max(width, height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    metadata["was_resized"] = True
                    metadata["final_dimensions"] = (new_width, new_height)
                else:
                    metadata["final_dimensions"] = (width, height)

                # 4. Exporta como JPEG otimizado
                stream_out = io.BytesIO()
                img.save(stream_out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
                clean_bytes = stream_out.getvalue()
                metadata["final_size"] = len(clean_bytes)

                logger.info(
                    f"Imagem sanitizada: {metadata['original_size']} bytes -> {metadata['final_size']} bytes "
                    f"(dimensões: {metadata['final_dimensions']})"
                )
                return clean_bytes, "image/jpeg", metadata

        except Exception as e:
            logger.error(f"Erro ao sanitizar imagem '{filename_hint}': {e}", exc_info=True)
            raise ValueError(f"Não foi possível processar a imagem enviada. Certifique-se de que é uma imagem válida: {e}") from e
