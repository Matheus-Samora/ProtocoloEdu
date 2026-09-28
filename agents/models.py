# -*- coding: utf-8 -*-
"""
Modelos de dados, contratos de tarefas e estados do Sistema Multi-Agentes (ProtocoloEdu MAS).
Define a comunicação estruturada, eventos e resultados entre os Subagentes Especialistas.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class SubagentRole(str, Enum):
    """Papéis dos Subagentes Especialistas no Enxame."""
    MASTER_ORCHESTRATOR = "master_orchestrator"
    MEDIA_FORENSICS = "media_forensics"
    COGNITIVE_OCR = "cognitive_ocr"
    MEC_COMPLIANCE = "mec_compliance"
    IDENTITY_FRAUD = "identity_fraud"
    CUSTODY_ARCHIVAL = "custody_archival"
    OMNICHANNEL_COMMS = "omnichannel_comms"
    ACADEMIC_ERP = "academic_erp"
    TELEMETRY_ANALYTICS = "telemetry_analytics"


class WorkflowStage(str, Enum):
    """Estágios do Ciclo de Vida do Dossiê Acadêmico."""
    SUBMITTED = "SUBMITTED"
    PREPROCESSED = "PREPROCESSED"
    OCR_EXTRACTED = "OCR_EXTRACTED"
    COMPLIANCE_EVALUATED = "COMPLIANCE_EVALUATED"
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    DECISION_CONSOLIDATED = "DECISION_CONSOLIDATED"
    CUSTODY_FINALIZED = "CUSTODY_FINALIZED"
    DISPATCHED = "DISPATCHED"
    ERP_SYNCHRONIZED = "ERP_SYNCHRONIZED"
    FAILED = "FAILED"


class AgentTaskStatus(str, Enum):
    """Status de execução de uma tarefa por um Subagente."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AgentTask(BaseModel):
    """Definição de uma tarefa delegada a um Subagente."""
    task_id: str = Field(..., description="Identificador único da tarefa")
    role: SubagentRole = Field(..., description="Papel do subagente responsável")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Dados de entrada da tarefa")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_seconds: float = Field(60.0, description="Tempo máximo permitido de execução")


def make_json_safe(obj: Any) -> Any:
    """Sanitiza recursivamente dados para serialização JSON, omitindo bytes binários pesados."""
    if isinstance(obj, bytes):
        return f"<{len(obj)} bytes>"
    elif isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items() if k not in ("content_bytes", "raw_files")}
    elif isinstance(obj, (list, tuple, set)):
        return [make_json_safe(item) for item in obj]
    elif hasattr(obj, "model_dump"):
        return make_json_safe(obj.model_dump(mode="python"))
    elif hasattr(obj, "dict"):
        return make_json_safe(obj.dict())
    elif hasattr(obj, "__dict__"):
        return make_json_safe(vars(obj))
    return obj


class AgentResult(BaseModel):
    """Resultado retornado por um Subagente após processamento."""
    task_id: str
    role: SubagentRole
    status: AgentTaskStatus
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict, description="Dados de negócio produzidos pelo subagente")
    summary: str = Field("", description="Resumo explicativo do parecer do subagente")
    diagnostics: Optional[str] = Field(None, description="Diagnóstico técnico administrativo (protegido)")
    latency_ms: float = Field(0.0, description="Tempo de execução do subagente em milissegundos")
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return make_json_safe(self.model_dump(mode="python"))


class SwarmAgentMetadata(BaseModel):
    """Metadados e métricas ao vivo de um Subagente registrado."""
    role: SubagentRole
    name: str
    description: str
    is_active: bool = True
    tasks_executed: int = 0
    tasks_failed: int = 0
    average_latency_ms: float = 0.0
    last_active_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return make_json_safe(self.model_dump(mode="python"))


class SwarmExecutionTrace(BaseModel):
    """Trilha de auditoria da orquestração multi-agentes para um documento."""
    document_id: str
    student_id: str
    institution_id: str
    current_stage: WorkflowStage
    subagent_results: Dict[str, AgentResult] = Field(default_factory=dict)
    is_approved: bool = False
    final_reason: str = ""
    admin_diagnostic: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return make_json_safe(self.model_dump(mode="python"))
