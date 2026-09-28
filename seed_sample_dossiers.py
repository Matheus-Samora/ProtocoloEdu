import os
from datetime import datetime, timezone
from core_dossier_models import StudentDossier, DocumentAuditItem, DossierStatus
from adapters.database.dossier_repository import DossierRepository

repo = DossierRepository()

# 1. Lucas Gabriel Mendonça
lucas = StudentDossier(
    institution_id="imes",
    student_id="12345678900",
    student_name="LUCAS GABRIEL MENDONCA",
    course_name="1ª Graduação (Administração)",
    cpf="123.456.789-00",
    status=DossierStatus.COM_PENDENCIA,
    documents={
        "RG": DocumentAuditItem(
            document_id="RG",
            display_name="Carteira de Identidade (RG / CIN)",
            status="approved",
            reason="Documento autêntico com frente e verso nítidos. CPF validado na base cadastral.",
            extracted_data={
                "nome": "LUCAS GABRIEL MENDONÇA",
                "cpf": "123.456.789-00",
                "rg": "23.315.673-0",
                "orgao_emissor": "SSP/SP",
                "filiacao": "MARIA HELENA MENDONÇA"
            },
            file_name="RG_Lucas_Gabriel.pdf"
        ),
        "HISTORICO_ENSINO_MEDIO": DocumentAuditItem(
            document_id="HISTORICO_ENSINO_MEDIO",
            display_name="Histórico Escolar do Ensino Médio",
            status="rejected",
            reason="O arquivo enviado contém apenas a página frontal de notas. É obrigatório constar o verso com o carimbo e assinatura da direção da escola.",
            extracted_data={"escola": "Colégio Estadual Central"},
            file_name="Historico_Incompleto.pdf"
        ),
        "COMPROVANTE_RESIDENCIA": DocumentAuditItem(
            document_id="COMPROVANTE_RESIDENCIA",
            display_name="Comprovante de Residência Atualizado",
            status="pending",
            reason="Aguardando anexo do aluno."
        )
    }
)
repo.save_dossier(lucas)

# 2. Ana Paula Souza
ana = StudentDossier(
    institution_id="imes",
    student_id="07143203033",
    student_name="ANA PAULA SOUZA",
    course_name="1ª Graduação (Direito)",
    cpf="071.432.030-33",
    status=DossierStatus.COMPLETO,
    documents={
        "RG": DocumentAuditItem(
            document_id="RG",
            display_name="Carteira de Identidade (RG)",
            status="approved",
            reason="Documento validado com sucesso.",
            extracted_data={"nome": "ANA PAULA SOUZA", "cpf": "071.432.030-33"}
        ),
        "HISTORICO_ENSINO_MEDIO": DocumentAuditItem(
            document_id="HISTORICO_ENSINO_MEDIO",
            display_name="Histórico Escolar do Ensino Médio",
            status="approved",
            reason="Histórico completo e assinado pela direção escolar."
        ),
        "CERTIDAO_NASCIMENTO_CASAMENTO": DocumentAuditItem(
            document_id="CERTIDAO_NASCIMENTO_CASAMENTO",
            display_name="Certidão de Nascimento",
            status="approved",
            reason="Certidão legível com averbação regular."
        ),
        "COMPROVANTE_RESIDENCIA": DocumentAuditItem(
            document_id="COMPROVANTE_RESIDENCIA",
            display_name="Comprovante de Residência",
            status="approved",
            reason="Conta de consumo com menos de 30 dias."
        )
    }
)
repo.save_dossier(ana)

# 3. Carlos Eduardo Mendes
carlos = StudentDossier(
    institution_id="imes",
    student_id="07129702931",
    student_name="CARLOS EDUARDO MENDES",
    course_name="1ª Graduação (Engenharia de Software)",
    cpf="071.297.029-31",
    status=DossierStatus.PENDENTE,
    documents={
        "RG": DocumentAuditItem(
            document_id="RG",
            display_name="Carteira de Identidade (RG)",
            status="approved",
            reason="Aprovado."
        )
    }
)
repo.save_dossier(carlos)

# 4. Mariana Ferreira Lima
mariana = StudentDossier(
    institution_id="imes",
    student_id="07132208201",
    student_name="MARIANA FERREIRA LIMA",
    course_name="Pós-Graduação (Gestão Escolar)",
    cpf="071.322.082-01",
    status=DossierStatus.EM_ANALISE,
    documents={
        "DIPLOMA_GRADUACAO": DocumentAuditItem(
            document_id="DIPLOMA_GRADUACAO",
            display_name="Diploma de Graduação",
            status="pending",
            reason="Aguardando análise da mesa acadêmica."
        )
    }
)
repo.save_dossier(mariana)

print("4 Dossiês de exemplo inseridos com sucesso na base central!")
