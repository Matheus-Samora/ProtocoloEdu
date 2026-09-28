"""
Servidor MCP Oficial do ProtocoloEdu (Model Context Protocol).
Suporta transporte Stdio e JSON-RPC 2.0 padrão para agentes e assistentes externos.
Expõe ferramentas para:
- Validação de assinaturas digitais ICP-Brasil / PAdES (MEC 315/2018).
- Mensageria multicanal (WhatsApp Cloud, Webhook, E-mail).
- Conectores bidirecionais de ERPs acadêmicos (Solis, TOTVS, Sophia).
- Telemetria de latência do Gemini e conversão de matrículas.
"""

import sys
import json
import logging
import argparse
from typing import Dict, Any, List, Optional

from mcp_services.pades_validator import PadesSignatureValidator
from mcp_services.notification_service import (
    NotificationService,
    NotificationChannel,
    NotificationType,
    notification_service
)
from mcp_services.erp_connector import ErpConnector, erp_connector
from mcp_services.telemetry_service import TelemetryService, telemetry_service

# Garantir UTF-8 obrigatório na comunicação JSON-RPC via Stdio
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stdin, 'reconfigure'):
        sys.stdin.reconfigure(encoding='utf-8')
except Exception:
    pass

# Configuração de log para stderr para nunca poluir a saída stdout (Stdio JSON-RPC)
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format='[MCP_SERVER] [%(levelname)s] %(asctime)s - %(message)s'
)
logger = logging.getLogger("MCP_SERVER")


class ProtocoloMcpServer:
    """Implementação do servidor Model Context Protocol via Stdio."""

    def __init__(self, service_mode: str = "all"):
        self.service_mode = service_mode.lower()
        self.pades_validator = PadesSignatureValidator()
        self.notifier = notification_service
        self.erp = erp_connector
        self.telemetry = telemetry_service

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Gera a lista de especificações de ferramentas com schema JSON."""
        tools = []

        # 1. Validador ICP-Brasil / PAdES
        if self.service_mode in ("all", "gateway", "icp-validator", "icp-brasil-validator"):
            tools.append({
                "name": "verify_pades_signature",
                "description": "Valida assinaturas digitais ICP-Brasil e conformidade com Portaria MEC 315/2018 e Diploma Digital em PDFs acadêmicos.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Caminho absoluto do arquivo PDF no servidor."
                        },
                        "file_base64": {
                            "type": "string",
                            "description": "Conteúdo do PDF codificado em Base64 (caso o arquivo não esteja no disco)."
                        },
                        "filename": {
                            "type": "string",
                            "description": "Nome original do documento (ex: 'diploma_digital.pdf')."
                        }
                    }
                }
            })

        # 2. Despachante de Notificações
        if self.service_mode in ("all", "gateway", "notification-dispatcher"):
            tools.append({
                "name": "send_student_notification",
                "description": "Dispara notificações acadêmicas oficiais para o estudante via WhatsApp Cloud API, Webhook ou E-mail.",
                "inputSchema": {
                    "type": "object",
                    "required": ["institution_id", "student_id", "student_name", "recipient"],
                    "properties": {
                        "institution_id": {"type": "string", "description": "Slug da instituição contratante (ex: 'imes')."},
                        "student_id": {"type": "string", "description": "CPF ou Matrícula do estudante."},
                        "student_name": {"type": "string", "description": "Nome completo do estudante."},
                        "recipient": {"type": "string", "description": "Telefone com DDD ou e-mail do aluno."},
                        "notification_type": {
                            "type": "string",
                            "enum": ["pendency", "homologation", "receipt", "custom"],
                            "description": "Tipo de comunicado."
                        },
                        "channel": {
                            "type": "string",
                            "enum": ["whatsapp", "webhook", "email"],
                            "description": "Canal de envio (padrão: whatsapp)."
                        },
                        "custom_message": {"type": "string", "description": "Mensagem livre caso notification_type seja 'custom'."},
                        "pending_docs": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "display_name": {"type": "string"},
                                    "reason": {"type": "string"}
                                }
                            },
                            "description": "Lista de documentos pendentes ou reprovados."
                        },
                        "course_name": {"type": "string", "description": "Nome do curso (para homologação)."},
                        "protocol_number": {"type": "string", "description": "Número do protocolo homologado."}
                    }
                }
            })

        # 3. Conector de ERP Acadêmico
        if self.service_mode in ("all", "gateway", "academic-erp-sync"):
            tools.extend([
                {
                    "name": "search_erp_student",
                    "description": "Consulta estudante ou candidato no ERP conectado da instituição (Solis, TOTVS Educacional, SophiA).",
                    "inputSchema": {
                        "type": "object",
                        "required": ["institution_id", "identifier"],
                        "properties": {
                            "institution_id": {"type": "string", "description": "ID da instituição contratante."},
                            "identifier": {"type": "string", "description": "CPF ou número de matrícula."}
                        }
                    }
                },
                {
                    "name": "sync_dossier_to_erp",
                    "description": "Envia o dossiê homologado do estudante e metadados de documentos para o ERP acadêmico.",
                    "inputSchema": {
                        "type": "object",
                        "required": ["institution_id", "student_id"],
                        "properties": {
                            "institution_id": {"type": "string", "description": "ID da instituição contratante."},
                            "student_id": {"type": "string", "description": "Identificador do estudante."},
                            "force_sync": {"type": "boolean", "description": "Forçar sincronização mesmo se houver pendências."}
                        }
                    }
                }
            ])

        # 4. Telemetria e Monitoramento de Latência
        if self.service_mode in ("all", "gateway", "system-telemetry"):
            tools.append({
                "name": "get_system_telemetry",
                "description": "Obtém métricas em tempo real de latência da IA (Gemini 2.5 Flash), integridade do servidor e taxas de conversão de matrícula.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "institution_id": {"type": "string", "description": "Opcional: filtrar dados por contratante."}
                    }
                }
            })

        return tools

    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executa a ferramenta MCP solicitada."""
        logger.info(f"Executando ferramenta MCP: '{tool_name}' com argumentos: {list(arguments.keys())}")

        try:
            if tool_name == "verify_pades_signature":
                pdf_input = arguments.get("file_path") or arguments.get("file_base64")
                if not pdf_input:
                    return {"isError": True, "content": [{"type": "text", "text": "Erro: Forneça 'file_path' ou 'file_base64'."}]}
                filename = arguments.get("filename", "documento.pdf")
                report = self.pades_validator.verify_pdf(pdf_input, filename=filename)
                return {"isError": False, "content": [{"type": "text", "text": json.dumps(report.model_dump(), indent=2, ensure_ascii=False)}]}

            elif tool_name == "send_student_notification":
                inst_id = arguments.get("institution_id", "imes")
                student_id = arguments.get("student_id")
                student_name = arguments.get("student_name")
                recipient = arguments.get("recipient")
                n_type = arguments.get("notification_type", "custom")
                channel = NotificationChannel(arguments.get("channel", "whatsapp"))

                if n_type == "pendency":
                    msg = self.notifier.notify_pendencies(
                        institution_id=inst_id,
                        institution_name=inst_id.upper(),
                        student_id=student_id,
                        student_name=student_name,
                        recipient_phone_or_email=recipient,
                        pending_items=arguments.get("pending_docs", []),
                        channel=channel,
                        async_dispatch=False
                    )
                elif n_type == "homologation":
                    msg = self.notifier.notify_homologation(
                        institution_id=inst_id,
                        institution_name=inst_id.upper(),
                        student_id=student_id,
                        student_name=student_name,
                        course_name=arguments.get("course_name", "Graduação"),
                        protocol_number=arguments.get("protocol_number", f"PROT-{student_id}"),
                        recipient_phone_or_email=recipient,
                        channel=channel,
                        async_dispatch=False
                    )
                else:
                    msg = self.notifier.notify_custom(
                        institution_id=inst_id,
                        institution_name=inst_id.upper(),
                        student_id=student_id,
                        student_name=student_name,
                        recipient_phone_or_email=recipient,
                        subject=arguments.get("subject", "Aviso Secretaria"),
                        custom_message=arguments.get("custom_message", "Aviso importante da secretaria."),
                        channel=channel,
                        async_dispatch=False
                    )

                return {"isError": False, "content": [{"type": "text", "text": json.dumps(msg.model_dump(), indent=2, ensure_ascii=False)}]}

            elif tool_name == "search_erp_student":
                inst_id = arguments.get("institution_id", "imes")
                identifier = arguments.get("identifier")
                # Carrega instituição do coordenador
                from services.protocol_coordinator import ProtocolCoordinator
                coord = ProtocolCoordinator()
                inst = coord.get_institution(inst_id)
                if not inst:
                    return {"isError": True, "content": [{"type": "text", "text": f"Instituição '{inst_id}' não localizada."}]}

                profile = self.erp.search_student(inst, identifier)
                if not profile:
                    return {"isError": False, "content": [{"type": "text", "text": f"Estudante '{identifier}' não localizado no ERP {inst.erp.erp_type}."}]}
                return {"isError": False, "content": [{"type": "text", "text": json.dumps(profile.model_dump(), indent=2, ensure_ascii=False)}]}

            elif tool_name == "sync_dossier_to_erp":
                inst_id = arguments.get("institution_id", "imes")
                student_id = arguments.get("student_id")
                force = arguments.get("force_sync", False)

                from services.protocol_coordinator import ProtocolCoordinator
                coord = ProtocolCoordinator()
                inst = coord.get_institution(inst_id)
                dossier = coord.dossier_repo.get_dossier(inst_id, student_id)
                if not dossier:
                    return {"isError": True, "content": [{"type": "text", "text": f"Dossiê do aluno '{student_id}' não encontrado."}]}

                result = self.erp.sync_dossier_to_erp(inst, dossier, force_sync=force)
                if result.success:
                    coord.dossier_repo.save_dossier(dossier)
                return {"isError": not result.success, "content": [{"type": "text", "text": json.dumps(result.model_dump(), indent=2, ensure_ascii=False)}]}

            elif tool_name == "get_system_telemetry":
                report = self.telemetry.get_full_telemetry_report()
                return {"isError": False, "content": [{"type": "text", "text": json.dumps(report, indent=2, ensure_ascii=False)}]}

            else:
                return {"isError": True, "content": [{"type": "text", "text": f"Ferramenta desconhecida: '{tool_name}'."}]}

        except Exception as e:
            logger.error(f"Erro ao processar ferramenta {tool_name}: {e}", exc_info=True)
            return {"isError": True, "content": [{"type": "text", "text": f"Erro interno ao executar '{tool_name}': {str(e)}"}]}

    def run_stdio_loop(self):
        """Loop principal do protocolo Stdio JSON-RPC 2.0."""
        logger.info(f"Servidor MCP ProtocoloEdu inicializado (Modo: '{self.service_mode}'). Aguardando comandos via Stdio...")

        for line in sys.stdin:
            line_str = line.strip()
            if not line_str:
                continue

            try:
                request = json.loads(line_str)
            except Exception as e:
                logger.error(f"Mensagem JSON inválida recebida: {e}")
                self._send_error(None, -32700, "Parse error")
                continue

            msg_id = request.get("id")
            method = request.get("method")
            params = request.get("params", {})

            # Trata notificações (sem ID de resposta obrigatório)
            if method == "notifications/initialized":
                logger.info("Notificação do cliente recebida: client initialized.")
                continue

            if method == "initialize":
                self._send_response(msg_id, {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": f"protocolo-edu-{self.service_mode}",
                        "version": "2.1.0"
                    }
                })

            elif method == "tools/list":
                tools = self.get_tool_definitions()
                self._send_response(msg_id, {"tools": tools})

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                tool_result = self.handle_tool_call(tool_name, arguments)
                self._send_response(msg_id, tool_result)

            elif method == "ping":
                self._send_response(msg_id, {})

            else:
                logger.warning(f"Método não suportado: {method}")
                self._send_error(msg_id, -32601, f"Method '{method}' not found")

    def _send_response(self, msg_id: Any, result: Any):
        """Envia resposta JSON-RPC formatada para stdout e força flush."""
        payload = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def _send_error(self, msg_id: Any, code: int, message: str, data: Any = None):
        """Envia erro JSON-RPC para stdout."""
        payload = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message,
                "data": data
            }
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="Servidor MCP Stdio para o ProtocoloEdu")
    parser.add_argument("--service", default="all", help="Modo do serviço (gateway, icp-validator, notification-dispatcher, academic-erp-sync, system-telemetry)")
    parser.add_argument("--server", action="store_true", help="Atalho para iniciar em modo servidor stdio")
    args = parser.parse_args()

    server = ProtocoloMcpServer(service_mode=args.service)
    server.run_stdio_loop()


if __name__ == '__main__':
    main()
