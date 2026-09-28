# -*- coding: utf-8 -*-
"""
Subagente Especialista 6: Agente de Atendimento & Comunicação Estudantil (OmnichannelCommsAgent).
Responsável pelo despacho humanizado de notificações via WhatsApp Cloud API, E-mail e Webhooks.
Mascaramento total de jargões técnicos e falhas de sistema, transformando exigências em orientações claras para o estudante.
"""

from typing import Dict, Any, List, Optional
from agents.base_agent import BaseSubagent
from agents.models import SubagentRole, AgentTask
from mcp_services.notification_service import (
    NotificationService,
    NotificationChannel,
    NotificationType,
    notification_service
)


class OmnichannelCommsAgent(BaseSubagent):
    """Subagente responsável pelo relacionamento empático, acolhimento e comunicação com o estudante."""

    def __init__(self, service: NotificationService = None):
        super().__init__(
            role=SubagentRole.OMNICHANNEL_COMMS,
            name="Agente de Atendimento & Comunicação Estudantil",
            description="Dispara orientações humanizadas via WhatsApp e E-mail, mitigando a evasão no funil de matrícula."
        )
        self.notification_service = service or notification_service

    def _run(self, task: AgentTask) -> Dict[str, Any]:
        institution_id: str = task.payload.get("institution_id", "imes")
        institution_name: str = task.payload.get("institution_name", "Faculdade IMES")
        student_id: str = task.payload.get("student_id", "")
        student_name: str = task.payload.get("student_name", "Estudante")
        recipient: str = task.payload.get("recipient", "5511999999999")
        notification_type: str = task.payload.get("notification_type", "pendency")
        channel_str: str = task.payload.get("channel", "whatsapp")
        pending_items: List[Dict[str, str]] = task.payload.get("pending_items", [])
        course_name: str = task.payload.get("course_name", "Graduação")
        protocol_number: str = task.payload.get("protocol_number", f"PROT-{student_id}")

        channel = NotificationChannel(channel_str.lower())

        if notification_type == "homologation":
            res = self.notification_service.notify_homologation(
                institution_id=institution_id,
                institution_name=institution_name,
                student_id=student_id,
                student_name=student_name,
                course_name=course_name,
                protocol_number=protocol_number,
                recipient_phone_or_email=recipient,
                channel=channel
            )
        elif notification_type == "pendency":
            # Humaniza motivos técnicos se houver
            humanized_items = []
            for item in pending_items:
                raw_reason = item.get("reason", "Documento pendente de regularização.")
                clean_reason = self._humanize_reason(raw_reason)
                humanized_items.append({
                    "display_name": item.get("display_name", "Documento"),
                    "reason": clean_reason
                })

            res = self.notification_service.notify_pendencies(
                institution_id=institution_id,
                institution_name=institution_name,
                student_id=student_id,
                student_name=student_name,
                recipient_phone_or_email=recipient,
                pending_items=humanized_items,
                channel=channel
            )
        else:
            custom_msg = task.payload.get("custom_message", "Comunicado da Secretaria Acadêmica.")
            res = self.notification_service.notify_custom(
                institution_id=institution_id,
                institution_name=institution_name,
                student_id=student_id,
                student_name=student_name,
                recipient_phone_or_email=recipient,
                subject=f"[{institution_name}] Comunicado Acadêmico",
                custom_message=custom_msg,
                channel=channel
            )

        dispatch_ok = res.status in ("queued", "sent", "simulated") or res.status in (NotificationStatus.QUEUED, NotificationStatus.SENT, NotificationStatus.SIMULATED)
        return {
            "success": dispatch_ok,
            "message_id": res.message_id,
            "channel": channel.value,
            "recipient": recipient,
            "dispatch_status": res.status.value if hasattr(res.status, "value") else str(res.status),
            "summary": f"Notificação despachada via {channel.value.upper()} para {recipient} (Status: {res.status})."
        }

    def _humanize_reason(self, raw_reason: str) -> str:
        """Converte termos técnicos e pareceres internos em linguagem acolhedora e explicativa."""
        if not raw_reason:
            return "Por favor, providencie o reenvio deste documento conforme as orientações do portal."

        # Remove diagnósticos internos de sistema
        if "[EXCEÇÃO" in raw_reason or "[FALHA" in raw_reason or "500" in raw_reason:
            return "Identificamos uma instabilidade temporária na leitura do arquivo. Por favor, reenvie uma foto nítida e bem iluminada."

        if "titularidade" in raw_reason.lower() or "não coincide" in raw_reason.lower():
            return "O documento enviado parece estar em nome de outra pessoa. Por favor, anexe um documento oficial emitido em seu próprio nome."

        if "verso" in raw_reason.lower():
            return "O documento enviado não contém o verso ou carimbo escolar legível. Envie uma foto frente e verso do documento original."

        return raw_reason
