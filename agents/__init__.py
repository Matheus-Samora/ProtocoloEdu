# -*- coding: utf-8 -*-
"""
Pacote de Subagentes Especialistas do ProtocoloEdu (Multi-Agent System).
"""

from agents.models import SubagentRole, WorkflowStage, AgentTask, AgentResult
from agents.base_agent import BaseSubagent
from agents.registry import agent_registry, AgentRegistry
from agents.master_orchestrator import master_orchestrator, MasterOrchestratorAgent

__all__ = [
    "SubagentRole",
    "WorkflowStage",
    "AgentTask",
    "AgentResult",
    "BaseSubagent",
    "agent_registry",
    "AgentRegistry",
    "master_orchestrator",
    "MasterOrchestratorAgent"
]
