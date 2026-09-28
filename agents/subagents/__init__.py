# -*- coding: utf-8 -*-
"""
Subagentes especialistas do enxame ProtocoloEdu.
"""

from agents.subagents.media_forensics_agent import MediaForensicsAgent
from agents.subagents.cognitive_ocr_agent import CognitiveOcrAgent
from agents.subagents.mec_compliance_agent import MecComplianceAgent
from agents.subagents.identity_fraud_agent import IdentityFraudAgent
from agents.subagents.custody_archival_agent import CustodyArchivalAgent
from agents.subagents.omnichannel_comms_agent import OmnichannelCommsAgent
from agents.subagents.academic_erp_agent import AcademicErpAgent
from agents.subagents.telemetry_analytics_agent import TelemetryAnalyticsAgent

__all__ = [
    "MediaForensicsAgent",
    "CognitiveOcrAgent",
    "MecComplianceAgent",
    "IdentityFraudAgent",
    "CustodyArchivalAgent",
    "OmnichannelCommsAgent",
    "AcademicErpAgent",
    "TelemetryAnalyticsAgent"
]
