"""
Módulo de Análise e Tratamento de PDFs para o Protocolo.
Suporte a contagem de páginas, verificação de senha/criptografia e extração de texto.
"""

import io
import logging
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger("PDF_HANDLER")

# Tentativa segura de importar fitz (PyMuPDF) e PyPDF2
PYMUPDF_AVAILABLE = False
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    pass

PYPDF2_AVAILABLE = False
try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    pass


class PDFHandler:
    """Manipulador e validador de arquivos PDF."""

    @staticmethod
    def is_pdf(file_bytes: bytes, filename_hint: str = "") -> bool:
        """Verifica se os bytes correspondem a um arquivo PDF válido (inspeção de magic bytes)."""
        if not file_bytes or len(file_bytes) < 4:
            return False
        # Verifica se começa com %PDF ou tem nos primeiros 1024 bytes
        return file_bytes.startswith(b'%PDF') or (b'%PDF' in file_bytes[:1024])

    @classmethod
    def inspect_pdf(cls, file_bytes: bytes) -> Dict[str, Any]:
        """
        Inspeciona metadados, contagem de páginas e segurança do PDF.

        Returns:
            Dict contendo: is_encrypted, page_count, has_text, extracted_text
        """
        result = {
            "is_valid_pdf": True,
            "is_encrypted": False,
            "page_count": 0,
            "has_embedded_text": False,
            "extracted_text_preview": ""
        }

        if not file_bytes.startswith(b'%PDF'):
            # Procura marcador %PDF nos primeiros 1024 bytes (alguns scanners colocam cabeçalhos antes)
            idx = file_bytes[:1024].find(b'%PDF')
            if idx == -1:
                result["is_valid_pdf"] = False
                return result

        # 1. Tenta com PyMuPDF (Mais rápido e confiável)
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                if doc.is_encrypted:
                    result["is_encrypted"] = True
                    doc.close()
                    return result

                result["page_count"] = len(doc)
                all_text = []
                for page in doc:
                    txt = page.get_text()
                    if txt:
                        all_text.append(txt)

                full_text = " ".join(all_text).strip()
                if full_text:
                    result["has_embedded_text"] = True
                    result["extracted_text_preview"] = full_text[:500]

                doc.close()
                return result
            except Exception as e:
                logger.warning(f"PyMuPDF falhou ao ler PDF, tentando PyPDF2: {e}")

        # 2. Fallback com PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                stream = io.BytesIO(file_bytes)
                reader = PdfReader(stream)
                if reader.is_encrypted:
                    result["is_encrypted"] = True
                    return result

                result["page_count"] = len(reader.pages)
                all_text = []
                for p in reader.pages:
                    txt = p.extract_text() or ""
                    if txt:
                        all_text.append(txt)

                full_text = " ".join(all_text).strip()
                if full_text:
                    result["has_embedded_text"] = True
                    result["extracted_text_preview"] = full_text[:500]

                return result
            except Exception as e:
                logger.error(f"PyPDF2 falhou ao ler PDF: {e}")

        # Se nenhuma biblioteca externa conseguiu abrir mas o header era %PDF
        result["page_count"] = 1
        return result
