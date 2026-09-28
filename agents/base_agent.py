# -*- coding: utf-8 -*-
"""
Classe Base Abstrata para os Subagentes Especialistas do ProtocoloEdu.
Implementa ciclo de vida padronizado, telemetria, medição de latência e resiliência a falhas.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from agents.models import (
    SubagentRole,
    AgentTask,
    AgentResult,
    AgentTaskStatus,
    SwarmAgentMetadata
)

logger = logging.getLogger("SUBAGENT_SYSTEM")


class BaseSubagent(ABC):
    """Contrato e infraestrutura base para cada Subagente Especialista."""

    def __init__(self, role: SubagentRole, name: str, description: str):
        self.role = role
        self.name = name
        self.description = description
        self.is_active = True
        self.tasks_executed = 0
        self.tasks_failed = 0
        self.total_latency_ms = 0.0
        self.last_active_at: Optional[datetime] = None
        self.logger = logging.getLogger(f"SUBAGENT.{role.value.upper()}")

    @abstractmethod
    def _run(self, task: AgentTask) -> Dict[str, Any]:
        """
        Lógica de execução especializada do subagente.
        Deve retornar um dicionário com os dados resultantes ou levantar exceção em caso de erro crítico.
        """
        pass

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Invoca o subagente com medição precisa de tempo, isolamento de exceções e telemetria.
        """
        t_start = time.perf_counter()
        self.last_active_at = datetime.now(timezone.utc)
        self.tasks_executed += 1

        try:
            self.logger.info(f"[{self.name}] Iniciando tarefa '{task.task_id}'...")
            output_data = self._run(task)
            lat_ms = (time.perf_counter() - t_start) * 1000.0
            self.total_latency_ms += lat_ms

            summary = output_data.get("summary", f"{self.name} concluído com sucesso.")
            diagnostics = output_data.get("diagnostics")

            self.logger.info(f"[{self.name}] Tarefa '{task.task_id}' concluída com sucesso em {lat_ms:.2f}ms.")
            return AgentResult(
                task_id=task.task_id,
                role=self.role,
                status=AgentTaskStatus.SUCCESS,
                success=output_data.get("success", True),
                data=output_data,
                summary=summary,
                diagnostics=diagnostics,
                latency_ms=lat_ms
            )

        except Exception as e:
            lat_ms = (time.perf_counter() - t_start) * 1000.0
            self.total_latency_ms += lat_ms
            self.tasks_failed += 1
            err_msg = f"{type(e).__name__}: {str(e)}"
            self.logger.error(f"[{self.name}] Falha na execução da tarefa '{task.task_id}': {err_msg}", exc_info=True)

            return AgentResult(
                task_id=task.task_id,
                role=self.role,
                status=AgentTaskStatus.FAILED,
                success=False,
                data={"error": err_msg},
                summary=f"Falha técnica na execução de {self.name}.",
                diagnostics=f"[FALHA SUBAGENTE {self.role.value}]: {err_msg}",
                latency_ms=lat_ms
            )

    def get_metadata(self) -> SwarmAgentMetadata:
        """Retorna os metadados e estatísticas de desempenho do subagente."""
        avg_lat = (self.total_latency_ms / self.tasks_executed) if self.tasks_executed > 0 else 0.0
        return SwarmAgentMetadata(
            role=self.role,
            name=self.name,
            description=self.description,
            is_active=self.is_active,
            tasks_executed=self.tasks_executed,
            tasks_failed=self.tasks_failed,
            average_latency_ms=round(avg_lat, 2),
            last_active_at=self.last_active_at
        )

    def health_check(self) -> bool:
        """Verifica prontidão do subagente."""
        return self.is_active
