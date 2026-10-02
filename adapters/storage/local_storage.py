"""
Módulo de Armazenamento Local Particionado (Local Disk Storage Provider).
Implementa a arquitetura de pastas por Letra (A a Z), Nome do Aluno e Subpastas ('DOC' e 'Outros Docs').
Remove completamente a dependência de serviços externos como Google Drive para a custódia local de arquivos.
"""

import os
import re
import string
import logging
import unicodedata
from security.storage import component, contained, write_document, read_document
from typing import Optional, List, Dict, Any, Tuple

from adapters.storage.base import StorageProvider, StoredFileInfo
from media.models import ProcessedMedia
from core_criteria_models import DocumentSpecification

logger = logging.getLogger("LOCAL_STORAGE")


def normalize_initial_letter(student_name: str) -> str:
    """
    Extrai a letra inicial normalizada (A-Z) desconsiderando acentuações.
    Ex: 'Álvaro' -> 'A', 'Érica' -> 'E', 'Ícaro' -> 'I'.
    Se o primeiro caractere não for uma letra, retorna 'OUTROS'.
    """
    if not student_name:
        return "OUTROS"
    stripped = str(student_name).strip()
    if not stripped:
        return "OUTROS"
    first_char = stripped[0]
    nfkd = unicodedata.normalize('NFKD', first_char)
    ascii_clean = nfkd.encode('ASCII', 'ignore').decode('utf-8')
    if ascii_clean.isalpha():
        letter = ascii_clean.upper()
        if 'A' <= letter <= 'Z':
            return letter
    return "OUTROS"


def sanitize_folder_or_file_name(name: str) -> str:
    """
    Higieniza o nome para pastas e arquivos seguros em Windows e Linux,
    preservando legibilidade para seres humanos.
    """
    if not name:
        return "SEM_NOME"
    # Remove caracteres reservados em sistemas de arquivos: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', '', str(name)).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip('. ')
    if not cleaned or cleaned.upper().split('.')[0] in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        raise ValueError('Invalid storage name')
    return cleaned


class LocalDiskStorageProvider(StorageProvider):
    """
    Provedor de Armazenamento em Disco Local no servidor da aplicação.
    
    Hierarquia de Diretórios:
    storage/
      └── {institution_id}/
          ├── A/
          │   └── {NOME_DO_ALUNO}/
          │       ├── DOC/          <- Documentos pessoais do aluno (RG, CPF, Histórico, etc.)
          │       └── Outros Docs/  <- Contratos de curso, termos e documentos institucionais
          ├── B/
          ...
          └── Z/
    """

    def __init__(
        self,
        base_directory: str = "storage",
        institution_id: str = "imes",
        precreate_alphabet: bool = True
    ):
        self.base_dir = os.path.abspath(base_directory)
        self.institution_id = component(institution_id).lower()
        self.institution_dir = str(contained(self.base_dir,self.institution_id))
        os.makedirs(self.institution_dir, exist_ok=True)

        # Pré-criação da estrutura de pastas A a Z para organização instantânea
        if precreate_alphabet:
            self._precreate_alphabet_structure()

    def _precreate_alphabet_structure(self):
        """Garante que as 26 pastas de A a Z existam na raiz da instituição."""
        for letter in string.ascii_uppercase:
            letter_folder = os.path.join(self.institution_dir, letter)
            os.makedirs(letter_folder, exist_ok=True)

    def get_student_paths(self, student_name: str) -> Dict[str, str]:
        """
        Localiza ou cria a estrutura de diretórios para o estudante dentro da letra correspondente.
        Cria automaticamente as subpastas 'DOC' e 'Outros Docs'.
        """
        letter = normalize_initial_letter(student_name)
        letter_dir = os.path.join(self.institution_dir, letter)
        os.makedirs(letter_dir, exist_ok=True)

        clean_name = sanitize_folder_or_file_name(student_name)

        # Busca pasta existente tolerando pequenas variações de maiúsculas/minúsculas
        target_student_dir = None
        if os.path.exists(letter_dir):
            with os.scandir(letter_dir) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False) and entry.name.upper() == clean_name.upper():
                        target_student_dir = entry.path
                        clean_name = entry.name
                        break


        if not target_student_dir:
            target_student_dir = str(contained(self.institution_dir,letter,clean_name))
            os.makedirs(target_student_dir, exist_ok=True)

        # Cria as subpastas obrigatórias
        doc_dir = str(contained(self.institution_dir,letter,clean_name,"DOC"))
        outros_docs_dir = str(contained(self.institution_dir,letter,clean_name,"Outros Docs"))
        os.makedirs(doc_dir, exist_ok=True)
        os.makedirs(outros_docs_dir, exist_ok=True)

        return {
            "letter": letter,
            "student_dir": target_student_dir,
            "student_name": clean_name,
            "doc_dir": doc_dir,
            "outros_docs_dir": outros_docs_dir
        }

    def _resolve_target_subfolder(self, spec: DocumentSpecification, paths: Dict[str, str]) -> Tuple[str, str]:
        """
        Determina se o documento deve ser gravado em 'DOC' ou 'Outros Docs'.
        """
        target_sub = getattr(spec, "target_drive_folder", "DOC") or "DOC"
        sub_upper = str(target_sub).strip().upper()
        spec_id_upper = str(getattr(spec, "id", "")).upper()

        if (
            sub_upper in ("OUTROS DOCS", "OUTROS_DOCS", "OUTROSDOCS")
            or "CONTRATO" in spec_id_upper
            or "TERMO" in spec_id_upper
            or "REQUERIMENTO" in spec_id_upper
        ):
            return paths["outros_docs_dir"], "Outros Docs"

        return paths["doc_dir"], "DOC"

    def store_document(
        self,
        student_name: str,
        spec: DocumentSpecification,
        media: ProcessedMedia,
        suffix: str = ""
    ) -> Optional[StoredFileInfo]:
        """
        Armazena o documento no disco local na subpasta correta ('DOC' ou 'Outros Docs')
        dentro da pasta do aluno e da letra inicial (A-Z).
        """
        paths = self.get_student_paths(student_name)
        target_dir, subfolder_label = self._resolve_target_subfolder(spec, paths)
        clean_student = paths["student_name"]

        # Monta nome oficial: ALUNO - NOME_DOC [SUFIXO].ext
        pattern = getattr(spec, "target_filename_pattern", "{aluno_nome} - {ext}")
        try:
            target_name = pattern.format(
                aluno_nome=clean_student,
                sufixo_pagina=suffix,
                ext=media.extension,
                tipo_certidao_especifico="CERTIDAO"
            )
        except Exception:
            doc_id_clean = getattr(spec, "id", "DOC")
            target_name = f"{clean_student} - {doc_id_clean}{suffix}{media.extension}"

        target_name = sanitize_folder_or_file_name(target_name)
        file_path = os.path.join(target_dir, target_name)

        file_path = str(contained(self.institution_dir, os.path.relpath(file_path,self.institution_dir)))
        write_document(self.base_dir,file_path,media.content_bytes)

        rel_key = os.path.relpath(file_path, self.base_dir).replace("\\", "/")
        storage_url = (
            f"/api/storage/file/{self.institution_id}/{paths['letter']}/"
            f"{clean_student}/{subfolder_label}/{target_name}"
        )

        logger.debug(f"[LOCAL STORAGE] Arquivo gravado com sucesso: '{file_path}' ({len(media.content_bytes)} bytes)")

        return StoredFileInfo(
            file_id=rel_key,
            filename=target_name,
            storage_url=storage_url,
            provider="local",
            size_bytes=len(media.content_bytes)
        )

    def list_student_documents(self, student_name: str) -> List[str]:
        """
        Retorna a lista combinada de arquivos presentes em 'DOC' e 'Outros Docs' do aluno.
        """
        paths = self.get_student_paths(student_name)
        all_files = []

        for folder in (paths["doc_dir"], paths["outros_docs_dir"]):
            if os.path.exists(folder):
                for f_name in os.listdir(folder):
                    full_p = os.path.join(folder, f_name)
                    if os.path.isfile(full_p):
                        all_files.append(f_name)

        return all_files

    def get_file_bytes(self, student_name: str, filename: str) -> Optional[bytes]:
        """
        Lê e retorna os bytes de um arquivo armazenado do estudante.
        Procura primeiro em 'DOC' e depois em 'Outros Docs'.
        """
        paths = self.get_student_paths(student_name)
        for folder in (paths["doc_dir"], paths["outros_docs_dir"]):
            if filename != os.path.basename(filename) or '\\' in filename: raise ValueError('Invalid filename')
            file_path = str(contained(self.institution_dir,os.path.relpath(folder,self.institution_dir),filename))
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return read_document(self.base_dir,file_path)
        return None

    def get_file_absolute_path(self, student_name: str, filename: str) -> Optional[str]:
        """Retorna o caminho absoluto do arquivo no disco caso exista."""
        paths = self.get_student_paths(student_name)
        for folder in (paths["doc_dir"], paths["outros_docs_dir"]):
            if filename != os.path.basename(filename) or '\\' in filename: raise ValueError('Invalid filename')
            file_path = str(contained(self.institution_dir,os.path.relpath(folder,self.institution_dir),filename))
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return file_path
        return None

    def delete_document(self, student_name: str, filename: str) -> bool:
        """
        Remove um arquivo específico das pastas de custódia do aluno ('DOC' ou 'Outros Docs').
        Garante conformidade institucional: documentos invalidados ou rejeitados são expurgados do disco.
        """
        if not filename:
            return False
        paths = self.get_student_paths(student_name)
        deleted = False
        for folder in (paths["doc_dir"], paths["outros_docs_dir"]):
            if filename != os.path.basename(filename) or '\\' in filename: raise ValueError('Invalid filename')
            file_path = str(contained(self.institution_dir,os.path.relpath(folder,self.institution_dir),filename))
            if os.path.exists(file_path) and os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"[LOCAL STORAGE] Arquivo excluído da custódia com sucesso: '{file_path}'")
                    deleted = True
                except Exception as e:
                    logger.error("Operation failed; inspect restricted security events")
        return deleted

