# Módulo para processar diferentes tipos de arquivo (PDF, Imagens e Word).
# VERSÃO ADAPTADA PARA NUVEM: As funções agora recebem o conteúdo do arquivo em memória.
# ATUALIZADO: Inclui sanitização de imagens e suporte a iPhone (HEIC) para evitar erro 400.

import os
import fitz  # PyMuPDF
from PyPDF2 import PdfReader
from PIL import Image, ImageOps
import io
import docx
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='[DOC_PROCESSOR] [%(levelname)s] %(message)s')

# --- SUPORTE A HEIC (IPHONE) ---
# Sem isto, fotos de iPhone vão dar erro 400 na API da Google.
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORT = True
    logging.info("Suporte a imagens HEIC (iPhone) ativado.")
except ImportError:
    HEIC_SUPPORT = False
    logging.warning("ATENÇÃO: Biblioteca 'pillow-heif' não encontrada. Fotos de iPhone (.HEIC) irão falhar.")

# --- NOVAS IMPORTAÇÕES PARA INTEGRAÇÃO COM DRIVE ---
import tempfile
import file_organizer  # Importa o nosso módulo organizador
import config_manager  # Para obter o ID do Drive


def sanitize_image_for_api(file_content):
    """
    Função CRUCIAL: Converte qualquer imagem (HEIC, PNG, BMP, JPG sujo)
    para um fluxo de bytes JPEG padrão e limpo (RGB).
    
    Isso resolve o erro '400 Unsupported mime type' ao converter HEIC para JPG.
    
    Returns:
        tuple: (bytes_io_obj, mime_type_str)
    """
    try:
        # Reseta o ponteiro do arquivo para garantir leitura do início
        file_content.seek(0)
        
        # Tenta abrir a imagem. Se for HEIC e não tiver pillow-heif, vai dar erro aqui.
        try:
            img = Image.open(file_content)
        except Exception as e_open:
            if not HEIC_SUPPORT:
                logging.error("Falha ao abrir imagem. Pode ser HEIC sem suporte instalado. Instale 'pip install pillow-heif'.")
            raise e_open

        # Corrige orientação baseada no EXIF (comum em fotos de celular que ficam deitadas)
        img = ImageOps.exif_transpose(img)
        
        # Converte para RGB (remove canal Alpha de PNGs que a API do Google as vezes rejeita)
        # E converte modos CMYK ou P para RGB padrão.
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        # Salva como JPEG limpo em memória
        output_stream = io.BytesIO()
        img.save(output_stream, format="JPEG", quality=85, optimize=True)
        output_stream.seek(0)
        
        return output_stream, "image/jpeg"

    except Exception as e:
        logging.error(f"Erro ao sanitizar imagem: {e}")
        # Se falhar a conversão (ex: arquivo corrompido), retorna o original
        # mas avisa que pode dar erro na API.
        file_content.seek(0)
        return file_content, "application/octet-stream"


def prepare_file_for_api(file_content, filename_hint=""):
    """
    FUNÇÃO NOVA: Use isto ANTES de chamar a API do Google Document AI.
    Ela decide se o arquivo precisa de conversão (HEIC -> JPG) ou se passa direto (PDF).
    
    Args:
        file_content (io.BytesIO): O conteúdo bruto do upload.
        filename_hint (str): O nome do arquivo (opcional) para ajudar a detetar PDF.
    
    Returns:
        tuple: (conteudo_pronto_bytes, mime_type_string)
    """
    file_content.seek(0)
    header = file_content.read(4)
    file_content.seek(0)
    
    # 1. Verifica se é PDF (assinatura %PDF)
    if header.startswith(b'%PDF') or (filename_hint and filename_hint.lower().endswith('.pdf')):
        return file_content, "application/pdf"
    
    # 2. Se não é PDF, assumimos que é Imagem (incluindo HEIC) e convertemos para JPG
    return sanitize_image_for_api(file_content)


def _process_image(file_content):
    """
    Função interna para extração de texto local (OCR simples).
    """
    try:
        clean_content, _ = sanitize_image_for_api(file_content)
        with Image.open(clean_content) as image:
            image.load()
            return "", image.copy(), None
    except Exception as e:
        return None, None, f"Não foi possível ler o arquivo de imagem: {e}"


def _process_pdf(file_content):
    """
    Função interna para extração de texto de PDF.
    """
    try:
        file_content.seek(0)
        file_bytes = file_content.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        if doc.is_encrypted:
            doc.close()
            return None, None, "O arquivo PDF está protegido por senha."

        text = "".join(page.get_text() for page in doc)
        image = None
        if len(doc) > 0:
            pix = doc[0].get_pixmap(dpi=150)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
        
        doc.close()
        return text, image, None
    
    except Exception:
        # Fallback com PyPDF2...
        try:
            file_content.seek(0)
            reader = PdfReader(file_content)
            if reader.is_encrypted:
                return None, None, "PDF Protegido."
            
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text, None, None
        except Exception as e:
            return None, None, f"Erro ao ler PDF: {e}"


def _process_word(file_content):
    try:
        file_content.seek(0)
        document = docx.Document(file_content)
        text = "\n".join([para.text for para in document.paragraphs])
        return text, None, None
    except Exception as e:
        return None, None, f"Erro ao ler Word: {e}"


def process_document_file(file_content, file_name):
    """
    Função legada de extração de texto.
    """
    _, file_extension = os.path.splitext(file_name)
    ext = file_extension.lower()

    if ext == '.pdf':
        return _process_pdf(file_content)
    elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.heic', '.webp']:
        return _process_image(file_content)
    elif ext == '.docx':
        return _process_word(file_content)
    else:
        return None, None, f"Tipo de arquivo '{ext}' não é suportado."


# =======================================================================
# FUNÇÃO DE ORQUESTRAÇÃO PARA SALVAR NO DRIVE
# =======================================================================

def process_and_save_document(tenant_id, student_name, doc_key, file_name, file_content):
    logging.info(f"Processando save para: {student_name} - {doc_key}")

    drive_id = config_manager.get_drive_id_for_tenant(tenant_id, student_name=student_name)
    if not drive_id:
        return {"status": "error", "message": "ID do Drive não encontrado."}

    standard_name = file_organizer.STANDARD_FILENAMES.get(doc_key, "Documento")
    _, file_extension = os.path.splitext(file_name)
    ext = file_extension.lower()
    
    content_to_save = file_content
    final_extension = file_extension

    # --- AQUI JÁ USAMOS A LIMPEZA PARA O DRIVE ---
    # Se for imagem (incluindo HEIC), converte para JPG antes de salvar
    if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.heic', '.webp']:
        clean_bytes, mime = sanitize_image_for_api(file_content)
        content_to_save = clean_bytes
        final_extension = ".jpg"
        logging.info(f"Imagem convertida para JPG antes de salvar no Drive.")

    final_file_name = f"{standard_name}{final_extension}"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=final_file_name) as temp_file:
            content_to_save.seek(0)
            temp_file.write(content_to_save.read())
            temp_file_path = temp_file.name
        
        success = file_organizer.save_document_to_drive(student_name, temp_file_path, drive_id)

        if success:
            return {"status": "success", "message": f"Salvo: {final_file_name}"}
        else:
            return {"status": "error", "message": "Erro no upload para o Drive."}

    except Exception as e:
        return {"status": "error", "message": f"Erro interno: {e}"}
    finally:
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)