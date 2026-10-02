# -*- coding: utf-8 -*-
"""
Registro Central de Subagentes (AgentRegistry).
Controla o ciclo de vida, descoberta, inventário e observabilidade do enxame de agentes.
"""

from typing import Dict, Any, List, Optional
import logging
from agents.base_agent import BaseSubagent
from agents.models import SubagentRole, SwarmAgentMetadata
from agents.subagents.media_forensics_agent import MediaForensicsAgent
from agents.subagents.cognitive_ocr_agent import CognitiveOcrAgent
from agents.subagents.mec_compliance_agent import MecComplianceAgent
from agents.subagents.identity_fraud_agent import IdentityFraudAgent
from agents.subagents.custody_archival_agent import CustodyArchivalAgent
from agents.subagents.omnichannel_comms_agent import OmnichannelCommsAgent
from agents.subagents.academic_erp_agent import AcademicErpAgent
from agents.subagents.telemetry_analytics_agent import TelemetryAnalyticsAgent

logger = logging.getLogger("AGENT_REGISTRY")


class AgentRegistry:
    """Catálogo central e gerenciador de descoberta de subagentes do ProtocoloEdu."""

    def __init__(self):
        self._agents: Dict[SubagentRole, BaseSubagent] = {}
        self._initialize_default_swarm()

    def register(self, agent: BaseSubagent):
        """Registra um subagente no enxame."""
        self._agents[agent.role] = agent
        logger.info(f"Subagente registrado: [{agent.role.value}] {agent.name}")

    def get(self, role: SubagentRole) -> Optional[BaseSubagent]:
        """Obtém a instância ativa de um subagente pelo seu papel."""
        return self._agents.get(role)

    def list_agents(self) -> List[SwarmAgentMetadata]:
        """Retorna os metadados e estatísticas de todos os subagentes registrados."""
        return [agent.get_metadata() for agent in self._agents.values()]

    def get_swarm_health(self) -> Dict[str, Any]:
        """Verifica a saúde global e a prontidão de todos os agentes do enxame."""
        total = len(self._agents)
        healthy = sum(1 for a in self._agents.values() if a.health_check())
        subagents_dict = {a.role.value: a.get_metadata().model_dump() for a in self._agents.values()}
        return {
            "total_subagents": total,
            "total_registered": total,
            "total_active": healthy,
            "healthy_subagents": healthy,
            "health_percentage": None,
            "health_scope": "Registro local; serviços externos não verificados",
            "status": "REGISTERED_NOT_PROBED" if healthy == total else "LOCAL_AGENT_INACTIVE",
            "subagents": subagents_dict,
            "agents": [a.get_metadata().model_dump() for a in self._agents.values()]
        }

    def _initialize_default_swarm(self):
        """Inicializa e registra os 8 subagentes especialistas padrão do sistema."""
        self.register(MediaForensicsAgent())
        self.register(CognitiveOcrAgent())
        self.register(MecComplianceAgent())
        self.register(IdentityFraudAgent())
        self.register(CustodyArchivalAgent())
        self.register(OmnichannelCommsAgent())
        self.register(AcademicErpAgent())
        self.register(TelemetryAnalyticsAgent())


# Instância singleton global do registro de subagentes
agent_registry = AgentRegistry()
