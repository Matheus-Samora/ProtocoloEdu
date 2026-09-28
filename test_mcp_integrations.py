"""
Suite de Testes Automatizados para Conexões MCP e Integrações Backend do ProtocoloEdu.
Verifica:
1. Validador de Assinaturas Digitais ICP-Brasil / PAdES (Portaria MEC 315/2018).
2. Serviço de Mensageria e Notificações (WhatsApp Cloud, Webhook, E-mail).
3. Conector de ERPs Acadêmicos (Solis, TOTVS Educacional, SophiA).
4. Telemetria de Latência do Gemini e Saúde do Servidor.
5. Servidor MCP Stdio JSON-RPC 2.0.
6. Endpoints REST da API Flask em api_server.py.
"""

import os
import sys
import json
import base64
import binascii
import datetime
import subprocess
import unittest
from io import BytesIO

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.serialization import pkcs7

from mcp_services.pades_validator import PadesSignatureValidator, PadesVerificationReport
from mcp_services.notification_service import (
    NotificationService,
    NotificationChannel,
    NotificationType,
    NotificationStatus
)
from mcp_services.erp_connector import ErpConnector, ErpSyncResult
from mcp_services.telemetry_service import TelemetryService, LatencyTracker
from mcp_services.mcp_server import ProtocoloMcpServer
from core_dossier_models import StudentDossier, DocumentAuditItem, DossierStatus
from core_institution_models import InstitutionProfile, SubscriptionConfig, ErpIntegrationConfig, StorageTopology
import api_server


def generate_test_signed_pdf() -> bytes:
    """Gera um PDF sintético assinado com certificado padrão ICP-Brasil."""
    key = rsa.generate_private_key(65537, 2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'BR'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'ICP-Brasil'),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, 'Autoridade Certificadora SERPRO v4'),
        x509.NameAttribute(NameOID.COMMON_NAME, 'REITORIA OFICIAL:01234567890')
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(
        key.public_key()
    ).serial_number(x509.random_serial_number()).not_valid_before(
        now - datetime.timedelta(days=1)
    ).not_valid_after(
        now + datetime.timedelta(days=365)
    ).sign(key, hashes.SHA256())

    p7 = pkcs7.PKCS7SignatureBuilder().set_data(b'ACERVO ACADEMICO DIGITAL MEC').add_signer(
        cert, key, hashes.SHA256()
    ).sign(serialization.Encoding.DER, options=[pkcs7.PKCS7Options.DetachedSignature])
    p7_hex = binascii.hexlify(p7).decode('ascii')

    part1 = b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n3 0 obj\n<< /Type /Sig /Filter /Adobe.PPKLite /SubFilter /ETSI.CAdES.detached /Name (REITORIA OFICIAL) /ByteRange '
    c_block = f'< {p7_hex} >'.encode('ascii')
    sig_part = b' /Contents ' + c_block + b' >>\nendobj\n'
    part2 = b'trailer\n<< /Root 1 0 R >>\n%%EOF'

    len1 = len(part1) + 24
    offset2 = len1 + len(sig_part)
    len2 = len(part2)

    br_str = f'[{0:06d} {len1:06d} {offset2:06d} {len2:06d}]'.encode('ascii')
    return part1 + br_str + sig_part + part2


class TestMcpIntegrations(unittest.TestCase):
    """Bateria de testes automatizados de infraestrutura e serviços MCP."""

    @classmethod
    def setUpClass(cls):
        cls.signed_pdf = generate_test_signed_pdf()
        cls.unsigned_pdf = b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF'

    # --------------------------------------------------------------------------
    # 1. TESTES DO VALIDADOR ICP-BRASIL / PADES
    # --------------------------------------------------------------------------
    def test_pades_validator_unsigned_pdf(self):
        validator = PadesSignatureValidator()
        report = validator.verify_pdf(self.unsigned_pdf, filename="unsigned.pdf")
        self.assertFalse(report.has_digital_signature)
        self.assertFalse(report.is_icp_brasil_certified)
        self.assertEqual(report.mec_315_status, "NAO_CONFORME")

    def test_pades_validator_signed_icp_brasil(self):
        validator = PadesSignatureValidator()
        report = validator.verify_pdf(self.signed_pdf, filename="diploma_digital.pdf")
        self.assertTrue(report.has_digital_signature)
        self.assertTrue(report.is_pades_compliant)
        self.assertTrue(report.is_icp_brasil_certified)
        self.assertIn(report.mec_315_status, ("CONFORME", "CONFORME_COM_RESSALVA"))
        self.assertEqual(len(report.signatures), 1)
        sig = report.signatures[0]
        self.assertEqual(len(sig.signers), 1)
        signer = sig.signers[0]
        self.assertTrue(signer.is_icp_brasil)
        self.assertEqual(signer.cpf_titular, "01234567890")
        self.assertTrue(signer.is_valid_time_window)

    # --------------------------------------------------------------------------
    # 2. TESTES DO SERVIÇO DE NOTIFICAÇÕES (MENSAGERIA MULTICANAL)
    # --------------------------------------------------------------------------
    def test_notification_service_pendency(self):
        service = NotificationService()
        msg = service.notify_pendencies(
            institution_id="imes",
            institution_name="IMES Mercosul",
            student_id="11122233344",
            student_name="Carlos Silva",
            recipient_phone_or_email="5531988887777",
            pending_items=[{"display_name": "Histórico Escolar", "reason": "Falta carimbo"}],
            channel=NotificationChannel.WHATSAPP,
            async_dispatch=False
        )
        self.assertEqual(msg.student_id, "11122233344")
        self.assertIn(msg.status, (NotificationStatus.SENT, NotificationStatus.SIMULATED))
        self.assertEqual(msg.notification_type, NotificationType.PENDENCY_ALERT)
        self.assertIn("Histórico Escolar", msg.body_text)

        # Checa histórico
        history = service.get_history(institution_id="imes", student_id="11122233344")
        self.assertTrue(len(history) >= 1)

    def test_notification_service_homologation(self):
        service = NotificationService()
        msg = service.notify_homologation(
            institution_id="imes",
            institution_name="IMES Mercosul",
            student_id="55566677788",
            student_name="Mariana Lima",
            course_name="Medicina",
            protocol_number="PROT-2026-MED-001",
            recipient_phone_or_email="5511977776666",
            channel=NotificationChannel.WHATSAPP,
            async_dispatch=False
        )
        self.assertEqual(msg.notification_type, NotificationType.HOMOLOGATION_SUCCESS)
        self.assertIn("PROT-2026-MED-001", msg.body_text)
        self.assertIn("HOMOLOGADA", msg.body_text)

    # --------------------------------------------------------------------------
    # 3. TESTES DO CONECTOR DE ERP ACADÊMICO
    # --------------------------------------------------------------------------
    def test_erp_connector_sync_homologated_dossier(self):
        connector = ErpConnector()
        inst = InstitutionProfile(
            id="test_inst",
            name="Faculdade Teste",
            institution_type="FACULDADE",
            subscription=SubscriptionConfig(admin_access_key="test-key"),
            storage=StorageTopology(provider="local_disk", root_folder_id="LOCAL_ROOT"),
            erp=ErpIntegrationConfig(erp_type="mock")
        )
        dossier = StudentDossier(
            institution_id=inst.id,
            student_id="99988877766",
            student_name="Estudante Homologado",
            course_name="Direito",
            status=DossierStatus.COMPLETO,
            documents={
                "rg": DocumentAuditItem(document_id="rg", status="approved", display_name="RG"),
                "historico": DocumentAuditItem(document_id="historico", status="approved", display_name="Histórico")
            }
        )

        res = connector.sync_dossier_to_erp(inst, dossier)
        self.assertTrue(res.success)
        self.assertEqual(res.documents_synced_count, 2)
        self.assertTrue(res.erp_protocol.startswith("ERP-MOCK"))
        self.assertTrue(dossier.metadata.get("erp_synced"))

    def test_erp_connector_reject_pending_dossier_without_force(self):
        connector = ErpConnector()
        inst = InstitutionProfile(
            id="test_inst",
            name="Faculdade Teste",
            institution_type="FACULDADE",
            subscription=SubscriptionConfig(admin_access_key="test-key"),
            storage=StorageTopology(provider="local_disk", root_folder_id="LOCAL_ROOT"),
            erp=ErpIntegrationConfig(erp_type="mock")
        )
        dossier = StudentDossier(
            institution_id=inst.id,
            student_id="123",
            student_name="Aluno Pendente",
            course_name="Direito",
            status=DossierStatus.PENDENTE
        )
        res = connector.sync_dossier_to_erp(inst, dossier, force_sync=False)
        self.assertFalse(res.success)
        self.assertIn("Apenas dossiês homologados", res.message)


    # --------------------------------------------------------------------------
    # 4. TESTES DO SERVIÇO DE TELEMETRIA
    # --------------------------------------------------------------------------
    def test_telemetry_service(self):
        telemetry = TelemetryService()
        telemetry.record_ai_call(latency_ms=1200.0, success=True, model_name="gemini-2.5-flash")
        telemetry.record_ai_call(latency_ms=1800.0, success=True, model_name="gemini-2.5-flash")
        telemetry.record_ai_call(latency_ms=2500.0, success=False, is_quota_error=True)
        telemetry.record_dossier_status("imes", None, "HOMOLOGADO")
        telemetry.record_document_audit("imes", "approved", "RG")

        stats = telemetry.get_latency_stats()
        self.assertEqual(stats.count, 3)
        self.assertTrue(stats.avg_ms > 0)

        health = telemetry.get_system_health()
        self.assertEqual(health.status, "healthy")
        self.assertTrue(health.uptime_seconds >= 0)

        report = telemetry.get_full_telemetry_report()
        self.assertIn("system_health", report)
        self.assertIn("ai_gemini_telemetry", report)
        self.assertIn("conversion_kpis", report)

    # --------------------------------------------------------------------------
    # 5. TESTES DO SERVIDOR MCP STDIO / JSON-RPC
    # --------------------------------------------------------------------------
    def test_mcp_server_tools_list_and_call(self):
        server = ProtocoloMcpServer(service_mode="gateway")
        tools = server.get_tool_definitions()
        tool_names = [t["name"] for t in tools]
        self.assertIn("verify_pades_signature", tool_names)
        self.assertIn("send_student_notification", tool_names)
        self.assertIn("sync_dossier_to_erp", tool_names)
        self.assertIn("search_erp_student", tool_names)
        self.assertIn("get_system_telemetry", tool_names)

        # Chama telemetria via tool handler
        res = server.handle_tool_call("get_system_telemetry", {})
        self.assertFalse(res.get("isError"))
        content = json.loads(res["content"][0]["text"])
        self.assertIn("system_health", content)

        # Chama validação PAdES via base64
        b64_pdf = base64.b64encode(self.signed_pdf).decode('ascii')
        sig_res = server.handle_tool_call("verify_pades_signature", {"file_base64": b64_pdf})
        self.assertFalse(sig_res.get("isError"))
        sig_data = json.loads(sig_res["content"][0]["text"])
        self.assertTrue(sig_data["has_digital_signature"])
        self.assertTrue(sig_data["is_icp_brasil_certified"])

    # --------------------------------------------------------------------------
    # 6. TESTES DOS ENDPOINTS DA API REST FLASK
    # --------------------------------------------------------------------------
    def test_api_verify_signature_endpoint(self):
        client = api_server.app.test_client()
        # Upload multipart do PDF assinado
        data = {
            'file': (BytesIO(self.signed_pdf), 'diploma_icp.pdf')
        }
        res = client.post('/api/documents/verify-signature', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data["success"])
        self.assertTrue(json_data["report"]["has_digital_signature"])
        self.assertTrue(json_data["report"]["is_icp_brasil_certified"])

    def test_api_notify_student_endpoint_auth(self):
        client = api_server.app.test_client()
        # Sem chave de autenticação -> 401
        res_unauth = client.post('/api/admin/notify-student', json={"student_id": "123"})
        self.assertEqual(res_unauth.status_code, 401)

        # Com chave do Super Admin
        headers = {"X-Admin-Key": api_server.SUPER_ADMIN_KEY}
        payload = {
            "student_id": "99988877700",
            "type": "pendency",
            "channel": "whatsapp",
            "recipient": "5511999998888",
            "pending_docs": [{"display_name": "RG", "reason": "Foto ilegível"}]
        }
        res_auth = client.post('/api/admin/notify-student?institution_id=imes', json=payload, headers=headers)
        self.assertEqual(res_auth.status_code, 200)
        data = res_auth.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["notification"]["channel"], "whatsapp")

    def test_api_erp_sync_endpoint_auth(self):
        client = api_server.app.test_client()
        # Sem chave de autenticação -> 401
        res_unauth = client.post('/api/admin/erp/sync', json={"student_id": "123"})
        self.assertEqual(res_unauth.status_code, 401)

        # Com chave administrativa
        headers = {"X-Admin-Key": api_server.SUPER_ADMIN_KEY}
        # Cria ou simula dossiê
        dossier = api_server.coordinator.get_student("imes", "99988877700")
        payload = {
            "student_id": "99988877700",
            "force_sync": True
        }
        res_auth = client.post('/api/admin/erp/sync?institution_id=imes', json=payload, headers=headers)
        self.assertIn(res_auth.status_code, (200, 400))
        data = res_auth.get_json()
        if res_auth.status_code == 200:
            self.assertTrue(data["success"])
            self.assertIn("ERP-", data["sync_result"]["erp_protocol"])

    def test_api_health_telemetry_endpoint(self):
        client = api_server.app.test_client()
        res = client.get('/api/system/health-telemetry')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("telemetry", data)
        self.assertIn("system_health", data["telemetry"])
        self.assertIn("ai_gemini_telemetry", data["telemetry"])
        self.assertIn("conversion_kpis", data["telemetry"])


if __name__ == '__main__':
    unittest.main()
