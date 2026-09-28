"""
Serviço de Mensageria e Notificações Institucionais do ProtocoloEdu.
Suporte multicanal para comunicação com estudantes:
- WhatsApp Business Cloud API (Meta Graph API)
- Webhooks institucionais (Zapier, Evolution API, Z-API, n8n, CRMs)
- E-mail institucional (SMTP / Provedor Transacional)
- Modo Simulação / Sandbox para desenvolvimento e testes
"""

import os
import re
import time
import uuid
import logging
import threading
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import requests
from pydantic import BaseModel, Field

logger = logging.getLogger("NOTIFICATION_SERVICE")


class NotificationChannel(str, Enum):
    WHATSAPP = "whatsapp"
    WEBHOOK = "webhook"
    EMAIL = "email"


class NotificationType(str, Enum):
    PENDENCY_ALERT = "pendency"
    HOMOLOGATION_SUCCESS = "homologation"
    RECEIPT_CONFIRMATION = "receipt"
    CUSTOM = "custom"


class NotificationStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    SIMULATED = "simulated"
    FAILED = "failed"


class NotificationMessage(BaseModel):
    """Registro auditável de uma notificação enviada."""
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    institution_id: str
    student_id: str
    student_name: str
    recipient: str
    channel: NotificationChannel
    notification_type: NotificationType
    subject: str
    body_text: str
    status: NotificationStatus = NotificationStatus.QUEUED
    external_id: Optional[str] = None
    error_message: Optional[str] = None
    sent_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationService:
    """
    Despachante assíncrono de notificações de matrícula e conferência documental.
    """

    def __init__(self, max_history: int = 500):
        self.max_history = max_history
        self._history: List[NotificationMessage] = []
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="NotifyWorker")

        # Configurações globais de provedores via variáveis de ambiente
        self.whatsapp_token = os.environ.get("WHATSAPP_CLOUD_TOKEN") or os.environ.get("WHATSAPP_TOKEN")
        self.whatsapp_phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or os.environ.get("WHATSAPP_PHONE_ID")
        self.whatsapp_api_version = os.environ.get("WHATSAPP_API_VERSION", "v19.0")
        self.default_webhook_url = os.environ.get("GLOBAL_NOTIFICATION_WEBHOOK_URL")

    def notify_pendencies(
        self,
        institution_id: str,
        institution_name: str,
        student_id: str,
        student_name: str,
        recipient_phone_or_email: str,
        pending_items: List[Dict[str, str]],
        portal_base_url: str = "https://protocolo.edu.br",
        channel: NotificationChannel = NotificationChannel.WHATSAPP,
        async_dispatch: bool = True
    ) -> NotificationMessage:
        """
        Notifica o aluno sobre documentos pendentes ou reprovados que exigem reenvio.
        """
        portal_url = f"{portal_base_url.rstrip('/')}/portal/{institution_id}"
        items_summary = []
        for item in pending_items:
            doc_name = item.get("display_name") or item.get("document_id") or "Documento"
            reason = item.get("reason") or "Documento em desconformidade"
            items_summary.append(f"• *{doc_name}*: {reason}")

        items_str = "\n".join(items_summary) if items_summary else "• Documentos obrigatórios pendentes de envio."

        subject = f"[{institution_name}] Pendência Documental na sua Matrícula"
        body = (
            f"Olá, *{student_name}*!\n\n"
            f"A Secretaria Acadêmica da *{institution_name}* identificou pendências no seu protocolo de envio de documentos.\n\n"
            f"📋 *Itens que necessitam de atenção:*\n{items_str}\n\n"
            f"Para regularizar sua situação e garantir sua vaga, acesse o portal institucional:\n"
            f"🔗 {portal_url}\n\n"
            f"Caso já tenha providenciado o reenvio, desconsidere esta mensagem."
        )

        message = NotificationMessage(
            institution_id=institution_id,
            student_id=student_id,
            student_name=student_name,
            recipient=recipient_phone_or_email,
            channel=channel,
            notification_type=NotificationType.PENDENCY_ALERT,
            subject=subject,
            body_text=body,
            metadata={"pending_count": len(pending_items), "portal_url": portal_url}
        )

        return self._dispatch_message(message, async_dispatch=async_dispatch)

    def notify_homologation(
        self,
        institution_id: str,
        institution_name: str,
        student_id: str,
        student_name: str,
        course_name: str,
        protocol_number: str,
        recipient_phone_or_email: str,
        channel: NotificationChannel = NotificationChannel.WHATSAPP,
        async_dispatch: bool = True
    ) -> NotificationMessage:
        """
        Notifica o estudante sobre o deferimento e homologação completa do prontuário.
        """
        subject = f"[{institution_name}] Parabéns! Documentos Homologados com Sucesso"
        body = (
            f"🎉 Parabéns, *{student_name}*!\n\n"
            f"Informamos que toda a sua documentação para o curso *{course_name}* na *{institution_name}* "
            f"foi auditada, validada e *HOMOLOGADA* com sucesso pela Secretaria Acadêmica!\n\n"
            f"📄 *Protocolo Institucional de Matrícula:* `{protocol_number}`\n"
            f"Data de Homologação: {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n\n"
            f"Sua vaga está garantida. Em breve você receberá as orientações de início das aulas e acesso aos sistemas acadêmicos.\n"
            f"Seja muito bem-vindo(a)!"
        )

        message = NotificationMessage(
            institution_id=institution_id,
            student_id=student_id,
            student_name=student_name,
            recipient=recipient_phone_or_email,
            channel=channel,
            notification_type=NotificationType.HOMOLOGATION_SUCCESS,
            subject=subject,
            body_text=body,
            metadata={"protocol_number": protocol_number, "course": course_name}
        )

        return self._dispatch_message(message, async_dispatch=async_dispatch)

    def notify_custom(
        self,
        institution_id: str,
        institution_name: str,
        student_id: str,
        student_name: str,
        recipient_phone_or_email: str,
        subject: str,
        custom_message: str,
        channel: NotificationChannel = NotificationChannel.WHATSAPP,
        async_dispatch: bool = True
    ) -> NotificationMessage:
        """Envia aviso customizado redigido pela secretaria."""
        formatted_body = (
            f"*{institution_name} - Secretaria Acadêmica*\n"
            f"Prezado(a) *{student_name}*,\n\n"
            f"{custom_message}\n\n"
            f"Atenciosamente,\nEquipe de Matrículas e Protocolo."
        )

        message = NotificationMessage(
            institution_id=institution_id,
            student_id=student_id,
            student_name=student_name,
            recipient=recipient_phone_or_email,
            channel=channel,
            notification_type=NotificationType.CUSTOM,
            subject=subject or f"[{institution_name}] Comunicado Acadêmico",
            body_text=formatted_body
        )

        return self._dispatch_message(message, async_dispatch=async_dispatch)

    def _dispatch_message(self, message: NotificationMessage, async_dispatch: bool = True) -> NotificationMessage:
        """Executa o envio síncrono ou programa na fila da thread pool."""
        self._record_history(message)

        if async_dispatch:
            self._executor.submit(self._execute_send, message)
            return message
        else:
            self._execute_send(message)
            return message

    def _execute_send(self, message: NotificationMessage):
        """Executa a chamada HTTP real ou simulação segura."""
        try:
            if message.channel == NotificationChannel.WHATSAPP:
                self._send_whatsapp(message)
            elif message.channel == NotificationChannel.WEBHOOK:
                self._send_webhook(message)
            elif message.channel == NotificationChannel.EMAIL:
                self._send_email(message)
            else:
                self._simulate_dispatch(message)
        except Exception as e:
            logger.error(f"Erro no envio da notificação {message.message_id}: {e}", exc_info=True)
            message.status = NotificationStatus.FAILED
            message.error_message = str(e)

    def _send_whatsapp(self, message: NotificationMessage):
        """Envia via WhatsApp Cloud API ou simula se não houver credenciais ativas."""
        clean_phone = re.sub(r'\D', '', message.recipient)
        # Garante DDI 55 do Brasil se faltar
        if len(clean_phone) in (10, 11):
            clean_phone = f"55{clean_phone}"

        if not self.whatsapp_token or not self.whatsapp_phone_id:
            # Modo Simulação / Sandbox Seguro
            logger.info(
                f"[WHATSAPP SIMULADO] Mensagem para {clean_phone} ({message.student_name}):\n{message.body_text[:120]}..."
            )
            message.status = NotificationStatus.SIMULATED
            message.external_id = f"sim_wa_{uuid.uuid4().hex[:8]}"
            return

        # Chamada real à API Meta Graph
        url = f"https://graph.facebook.com/{self.whatsapp_api_version}/{self.whatsapp_phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.whatsapp_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": message.body_text
            }
        }

        res = requests.post(url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        data = res.json()
        message.status = NotificationStatus.SENT
        messages_resp = data.get("messages", [])
        if messages_resp:
            message.external_id = messages_resp[0].get("id")
        logger.info(f"Notificação WhatsApp enviada com sucesso para {clean_phone} (ID: {message.external_id}).")

    def _send_webhook(self, message: NotificationMessage):
        """Envia payload para webhook institucional configurado."""
        webhook_url = message.metadata.get("webhook_url") or self.default_webhook_url
        if not webhook_url:
            logger.info(f"[WEBHOOK SIMULADO] Nenhum webhook configurado. Notificação registrada localmente.")
            message.status = NotificationStatus.SIMULATED
            message.external_id = f"sim_wh_{uuid.uuid4().hex[:8]}"
            return

        payload = {
            "event": "student_notification",
            "message_id": message.message_id,
            "institution_id": message.institution_id,
            "student_id": message.student_id,
            "student_name": message.student_name,
            "recipient": message.recipient,
            "type": message.notification_type.value,
            "subject": message.subject,
            "body": message.body_text,
            "timestamp": message.sent_at,
            "metadata": message.metadata
        }

        res = requests.post(webhook_url, json=payload, headers={"User-Agent": "ProtocoloEdu-Notifier/2.0"}, timeout=15)
        res.raise_for_status()
        message.status = NotificationStatus.SENT
        message.external_id = f"wh_{res.status_code}"
        logger.info(f"Notificação Webhook entregue com sucesso em {webhook_url}.")

    def _send_email(self, message: NotificationMessage):
        """Dispara e-mail ou registra em log em ambiente simulado."""
        # Se houver configuração SMTP ativa no ambiente:
        smtp_host = os.environ.get("SMTP_HOST")
        if not smtp_host:
            logger.info(f"[EMAIL SIMULADO] Para: {message.recipient} | Assunto: {message.subject}")
            message.status = NotificationStatus.SIMULATED
            message.external_id = f"sim_em_{uuid.uuid4().hex[:8]}"
            return

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        sender_email = os.environ.get("SMTP_SENDER", "nao-responda@protocolo.edu.br")
        smtp_port = int(os.environ.get("SMTP_PORT", 587))
        smtp_user = os.environ.get("SMTP_USER", "")
        smtp_pass = os.environ.get("SMTP_PASS", "")

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = message.recipient
        msg['Subject'] = message.subject
        msg.attach(MIMEText(message.body_text, 'plain', 'utf-8'))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if smtp_user and smtp_pass:
                server.starttls()
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        message.status = NotificationStatus.SENT
        message.external_id = f"em_{uuid.uuid4().hex[:8]}"
        logger.info(f"E-mail institucional enviado com sucesso para {message.recipient}.")

    def _simulate_dispatch(self, message: NotificationMessage):
        """Simulação padrão."""
        message.status = NotificationStatus.SIMULATED
        message.external_id = f"sim_{uuid.uuid4().hex[:8]}"

    def _record_history(self, message: NotificationMessage):
        """Armazena registro na lista thread-safe com limite de tamanho."""
        with self._lock:
            self._history.insert(0, message)
            if len(self._history) > self.max_history:
                self._history.pop()

    def get_history(
        self,
        institution_id: Optional[str] = None,
        student_id: Optional[str] = None,
        limit: int = 50
    ) -> List[NotificationMessage]:
        """Consulta histórico recente de notificações filtradas."""
        with self._lock:
            filtered = self._history
            if institution_id:
                filtered = [m for m in filtered if m.institution_id == institution_id]
            if student_id:
                filtered = [m for m in filtered if m.student_id == student_id]
            return filtered[:limit]


# Instância global compartilhada
notification_service = NotificationService()
