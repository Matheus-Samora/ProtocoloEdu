"""
Motor Universal de Exportação de Dados e Documentos (Universal Export Engine).
Permite às secretarias escolares e universitárias exportar os dados capturados
em Planilha (CSV/Excel), Arquivo ZIP estruturado ou JSON para alimentação de ERPs externos.
"""

import io
import csv
import json
import zipfile
import logging
import re
import os
from typing import List, Dict, Any, Optional

from core_dossier_models import StudentDossier, DossierStatus

logger = logging.getLogger("EXPORT_ENGINE")


def sanitize_csv_value(val: Any) -> str:
    """Prevenção contra CSV Formula Injection (CWE-1236). Desarma fórmulas perigosas (=, +, -, @)."""
    if val is None:
        return ""
    s = str(val).strip()
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{s}"
    return s


class UniversalExportEngine:
    """Motor de geração de relatórios e pacotes de exportação de documentos."""

    @staticmethod
    def export_to_csv(dossiers: List[StudentDossier]) -> str:
        """
        Gera uma planilha CSV com delimitador ';' e encoding UTF-8-SIG (compatível nativamente com Excel).
        Consolida todas as informações cadastrais extraídas pela IA de todos os documentos.
        """
        output = io.StringIO()
        # Escreve BOM UTF-8 para o Excel abrir com acentuação correta
        output.write('\ufeff')

        headers = [
            "ID_Aluno",
            "Nome_Completo",
            "CPF",
            "Curso_Nivel",
            "Status_Documental",
            "Data_Cadastro",
            "Data_Ultima_Atualizacao",
            # Dados Pessoais e RG
            "RG_Numero",
            "RG_Orgao_Expedidor",
            "Data_Nascimento",
            "Filiacao",
            "Naturalidade",
            # Endereço
            "Endereco_Completo",
            "CEP",
            "Cidade",
            "UF",
            # Acadêmico
            "Escola_Origem",
            "Ano_Conclusao",
            "IES_Graduacao",
            "Curso_Graduacao",
            # Outros Documentos
            "Titulo_Eleitor",
            "Documento_Militar",
            # Resumo de Status por Documento
            "Status_RG",
            "Status_CPF",
            "Status_Comprovante_Residencia",
            "Status_Diploma_Certificado",
            "Status_Historico",
            "Motivos_Pendencias"
        ]

        writer = csv.DictWriter(output, fieldnames=headers, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()

        for d in dossiers:
            row = {
                "ID_Aluno": d.student_id,
                "Nome_Completo": d.student_name,
                "CPF": d.cpf or "",
                "Curso_Nivel": d.course_name,
                "Status_Documental": d.status.value,
                "Data_Cadastro": d.created_at.strftime("%d/%m/%Y %H:%M") if d.created_at else "",
                "Data_Ultima_Atualizacao": d.updated_at.strftime("%d/%m/%Y %H:%M") if d.updated_at else "",
            }

            # Consolida dados extraídos de cada documento
            extracted_all: Dict[str, Any] = {}
            pendencias = []

            for doc_key, doc_item in d.documents.items():
                if doc_item.extracted_data:
                    extracted_all.update(doc_item.extracted_data)
                if doc_item.status == "rejected" and doc_item.reason:
                    pendencias.append(f"{doc_key}: {doc_item.reason}")

            row["RG_Numero"] = extracted_all.get("numero_rg", "")
            row["RG_Orgao_Expedidor"] = extracted_all.get("orgao_expedidor", "")
            row["Data_Nascimento"] = extracted_all.get("data_nascimento", "")
            row["Filiacao"] = extracted_all.get("filiacao", "")
            row["Naturalidade"] = extracted_all.get("naturalidade", "")

            row["Endereco_Completo"] = extracted_all.get("endereco_completo", "")
            row["CEP"] = extracted_all.get("cep", "")
            row["Cidade"] = extracted_all.get("cidade", "")
            row["UF"] = extracted_all.get("estado_uf", "")

            row["Escola_Origem"] = extracted_all.get("instituicao_ensino", "")
            row["Ano_Conclusao"] = extracted_all.get("data_conclusao", "")
            row["IES_Graduacao"] = extracted_all.get("instituicao_ensino", "") if "GRADUACAO" in d.course_name.upper() else ""
            row["Curso_Graduacao"] = extracted_all.get("nome_curso", "")

            row["Titulo_Eleitor"] = extracted_all.get("numero_titulo_eleitor", "")
            row["Documento_Militar"] = extracted_all.get("numero_documento_militar", "")

            # Status de conferência rápida
            row["Status_RG"] = d.documents.get("RG", d.documents.get("CNH", None)).status if ("RG" in d.documents or "CNH" in d.documents) else "NÃO ENVIADO"
            row["Status_CPF"] = d.documents.get("CPF", None).status if "CPF" in d.documents else "INCLUSO NO RG/CNH"
            row["Status_Comprovante_Residencia"] = d.documents.get("COMPROVANTE_RESIDENCIA", None).status if "COMPROVANTE_RESIDENCIA" in d.documents else "NÃO ENVIADO"
            
            diploma_item = d.documents.get("DIPLOMA_GRADUACAO", d.documents.get("CERTIFICADO_ENSINO_MEDIO", None))
            row["Status_Diploma_Certificado"] = diploma_item.status if diploma_item else "NÃO ENVIADO"
            
            hist_item = d.documents.get("HISTORICO_GRADUACAO", d.documents.get("HISTORICO_ENSINO_MEDIO", None))
            row["Status_Historico"] = hist_item.status if hist_item else "NÃO ENVIADO"

            row["Motivos_Pendencias"] = " | ".join(pendencias)

            # Aplica sanitização contra injeção de fórmulas no Excel em todos os campos
            clean_row = {k: sanitize_csv_value(v) for k, v in row.items()}
            writer.writerow(clean_row)

        return output.getvalue()

    @staticmethod
    def export_to_json(dossiers: List[StudentDossier]) -> str:
        """Gera payload JSON estruturado de exportação em lote."""
        data = [d.model_dump(mode='json',exclude={'metadata':{'portal_access_hash'}}) for d in dossiers]
        return json.dumps({
            "export_version": "2.0.0",
            "total_records": len(data),
            "records": data
        }, indent=2, ensure_ascii=False)

    @staticmethod
    def create_batch_zip(
        dossiers: List[StudentDossier],
        file_fetcher_fn=None
    ) -> bytes:
        """
        Cria um arquivo ZIP consolidado contendo:
        1. A planilha 'relatorio_geral_alunos.csv' na raiz.
        2. Uma subpasta organizada para cada aluno contendo seus arquivos e seu prontuário JSON.
        """
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Adiciona a planilha CSV consolidada
            csv_content = UniversalExportEngine.export_to_csv(dossiers)
            zf.writestr("relatorio_geral_alunos.csv", csv_content.encode('utf-8-sig'))

            # 2. Adiciona o prontuário de cada aluno com nomes estritamente higienizados (Anti Zip Slip)
            for d in dossiers:
                clean_student_name = "".join(c for c in d.student_name if c.isalnum() or c in (' ', '_', '-')).strip()
                clean_student_id = "".join(c for c in str(d.student_id) if c.isalnum() or c in ('_', '-')).strip()
                folder_name = f"{clean_student_id} - {clean_student_name}".strip(' -_')

                # Salva o resumo JSON individual do aluno
                student_json = json.dumps(d.model_dump(mode='json',exclude={'metadata':{'portal_access_hash'}}), indent=2, ensure_ascii=False)
                zf.writestr(f"{folder_name}/prontuario_auditoria.json", student_json.encode('utf-8'))

                # Se houver função para recuperar bytes dos arquivos do storage
                if file_fetcher_fn:
                    for doc_key, doc_item in d.documents.items():
                        if doc_item.file_name and doc_item.status == "approved":
                            file_bytes = file_fetcher_fn(d, doc_item)
                            if file_bytes:
                                safe_file_name = os.path.basename(doc_item.file_name)
                                safe_file_name = re.sub(r'[^a-zA-Z0-9._-]', '_', safe_file_name).strip('_')
                                if safe_file_name:
                                    zf.writestr(f"{folder_name}/{safe_file_name}", file_bytes)

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
