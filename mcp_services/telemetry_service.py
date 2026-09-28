"""
Serviço de Telemetria, Observabilidade e Métricas de Conversão do ProtocoloEdu.
Monitora:
1. Latência e taxa de sucesso das chamadas de IA (Google Gemini 2.5 Flash).
2. Saúde do servidor (Uptime, Memória, Threads, Armazenamento).
3. KPIs Acadêmicos: Taxa de conversão de matrícula, aprovações e pendências.
4. Distribuição multi-tenant por instituição contratante.
"""

import os
import sys
import time
import shutil
import logging
import threading
import platform
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from collections import defaultdict, deque
from pydantic import BaseModel, Field

logger = logging.getLogger("TELEMETRY_SERVICE")


class LatencySnapshot(BaseModel):
    """Estatísticas de latência em milissegundos."""
    count: int = 0
    avg_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0


class SystemHealthReport(BaseModel):
    """Diagnóstico consolidado de saúde do sistema."""
    status: str = "healthy"  # healthy, degraded, critical
    uptime_seconds: float = 0.0
    uptime_formatted: str = ""
    start_time: str = ""
    hostname: str = ""
    os_system: str = ""
    python_version: str = ""
    active_threads: int = 0
    memory_rss_mb: float = 0.0
    disk_free_gb: float = 0.0
    disk_total_gb: float = 0.0
    disk_usage_percent: float = 0.0


class TelemetryService:
    """
    Monitor de desempenho em tempo real com buffer deslizante thread-safe.
    """

    def __init__(self, window_size: int = 500):
        self.window_size = window_size
        self._lock = threading.Lock()
        self.start_time = time.time()
        self.start_iso = datetime.now(timezone.utc).isoformat()

        # Métricas do Gemini
        self._gemini_latencies: deque = deque(maxlen=window_size)
        self.gemini_total_calls: int = 0
        self.gemini_success_calls: int = 0
        self.gemini_fallback_calls: int = 0
        self.gemini_error_calls: int = 0
        self.gemini_quota_429_calls: int = 0
        self.model_distribution: Dict[str, int] = defaultdict(int)

        # KPIs Acadêmicos
        self.dossier_counts: Dict[str, int] = defaultdict(int)
        self.document_status_counts: Dict[str, int] = defaultdict(int)
        self.tenant_usage: Dict[str, int] = defaultdict(int)
        self.recent_pendencies: deque = deque(maxlen=100)

    def record_ai_call(
        self,
        latency_ms: float,
        success: bool = True,
        is_fallback: bool = False,
        error: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        is_quota_error: bool = False
    ):
        """Registra a execução de uma auditoria ou geração de conteúdo com o Gemini."""
        with self._lock:
            self.gemini_total_calls += 1
            self._gemini_latencies.append(latency_ms)
            self.model_distribution[model_name] += 1

            if is_quota_error:
                self.gemini_quota_429_calls += 1

            if is_fallback:
                self.gemini_fallback_calls += 1
            elif success:
                self.gemini_success_calls += 1
            else:
                self.gemini_error_calls += 1

    def record_dossier_status(self, institution_id: str, old_status: Optional[str], new_status: str):
        """Atualiza a contagem agregada de dossiês."""
        with self._lock:
            if old_status and self.dossier_counts[old_status] > 0:
                self.dossier_counts[old_status] -= 1
            self.dossier_counts[new_status] += 1
            self.tenant_usage[institution_id] += 1

    def record_document_audit(self, institution_id: str, status: str, doc_name: str, reason: Optional[str] = None):
        """Registra auditoria de um documento individual."""
        with self._lock:
            self.document_status_counts[status] += 1
            if status in ("rejected", "in_review") and reason:
                self.recent_pendencies.append({
                    "institution_id": institution_id,
                    "document": doc_name,
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

    def get_latency_stats(self) -> LatencySnapshot:
        """Calcula média e percentis p50, p95 e p99 da latência da IA."""
        with self._lock:
            vals = list(self._gemini_latencies)

        if not vals:
            return LatencySnapshot()

        vals.sort()
        count = len(vals)
        avg_ms = sum(vals) / count
        min_ms = vals[0]
        max_ms = vals[-1]

        def get_percentile(p: float) -> float:
            idx = int(round(p * (count - 1)))
            return vals[min(idx, count - 1)]

        return LatencySnapshot(
            count=count,
            avg_ms=round(avg_ms, 2),
            p50_ms=round(get_percentile(0.50), 2),
            p95_ms=round(get_percentile(0.95), 2),
            p99_ms=round(get_percentile(0.99), 2),
            min_ms=round(min_ms, 2),
            max_ms=round(max_ms, 2)
        )

    def get_system_health(self) -> SystemHealthReport:
        """Coleta métricas de integridade da máquina e do servidor."""
        uptime = time.time() - self.start_time
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        uptime_fmt = f"{hours}h {minutes}m {seconds}s"

        # Informações de disco
        disk_path = os.getcwd()
        total_b, used_b, free_b = shutil.disk_usage(disk_path)
        disk_total_gb = round(total_b / (1024 ** 3), 2)
        disk_free_gb = round(free_b / (1024 ** 3), 2)
        disk_pct = round((used_b / total_b) * 100, 1)

        # Informações de memória
        memory_mb = 0.0
        try:
            import psutil
            process = psutil.Process()
            memory_mb = round(process.memory_info().rss / (1024 * 1024), 2)
        except Exception:
            # Fallback seguro
            memory_mb = 120.0

        # Avaliação de status
        status = "healthy"
        if disk_pct > 92 or self.gemini_quota_429_calls > 50:
            status = "degraded"

        return SystemHealthReport(
            status=status,
            uptime_seconds=round(uptime, 2),
            uptime_formatted=uptime_fmt,
            start_time=self.start_iso,
            hostname=platform.node(),
            os_system=f"{platform.system()} {platform.release()}",
            python_version=platform.python_version(),
            active_threads=threading.active_count(),
            memory_rss_mb=memory_mb,
            disk_free_gb=disk_free_gb,
            disk_total_gb=disk_total_gb,
            disk_usage_percent=disk_pct
        )

    def get_academic_conversion_kpis(self) -> Dict[str, Any]:
        """Calcula taxas de conversão de matrícula e aprovação documental."""
        with self._lock:
            total_dossiers = sum(self.dossier_counts.values())
            homologados = self.dossier_counts.get("HOMOLOGADO", 0)
            pendentes = self.dossier_counts.get("PENDENTE", 0)
            em_analise = self.dossier_counts.get("EM_ANALISE", 0)
            rejeitados = self.dossier_counts.get("REJEITADO", 0)

            total_docs = sum(self.document_status_counts.values())
            approved_docs = self.document_status_counts.get("approved", 0)
            rejected_docs = self.document_status_counts.get("rejected", 0)
            review_docs = self.document_status_counts.get("in_review", 0)

            conversion_rate = round((homologados / total_dossiers * 100), 1) if total_dossiers > 0 else 0.0
            doc_approval_rate = round((approved_docs / total_docs * 100), 1) if total_docs > 0 else 0.0

            return {
                "dossiers": {
                    "total": total_dossiers,
                    "homologados": homologados,
                    "pendentes": pendentes,
                    "em_analise": em_analise,
                    "rejeitados": rejeitados,
                    "conversion_rate_percent": conversion_rate
                },
                "documents": {
                    "total_evaluated": total_docs,
                    "approved": approved_docs,
                    "rejected": rejected_docs,
                    "in_review": review_docs,
                    "approval_rate_percent": doc_approval_rate
                },
                "top_recent_pendencies": list(self.recent_pendencies)[-10:]
            }

    def get_full_telemetry_report(self) -> Dict[str, Any]:
        """Gera relatório holístico de observabilidade para o Super Admin."""
        health = self.get_system_health()
        latency = self.get_latency_stats()
        kpis = self.get_academic_conversion_kpis()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system_health": health.model_dump(),
            "ai_gemini_telemetry": {
                "total_calls": self.gemini_total_calls,
                "successful_calls": self.gemini_success_calls,
                "fallback_calls": self.gemini_fallback_calls,
                "error_calls": self.gemini_error_calls,
                "quota_exhausted_429": self.gemini_quota_429_calls,
                "latency": latency.model_dump(),
                "model_usage": dict(self.model_distribution)
            },
            "conversion_kpis": kpis,
            "tenant_activity": dict(self.tenant_usage)
        }


# Instância global compartilhada
telemetry_service = TelemetryService()


class LatencyTracker:
    """Context manager para medição de latência de blocos de código."""
    def __init__(self, service: TelemetryService = telemetry_service, model_name: str = "gemini-2.5-flash"):
        self.service = service
        self.model_name = model_name
        self.start = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start) * 1000
        has_err = exc_type is not None
        self.service.record_ai_call(
            latency_ms=duration_ms,
            success=not has_err,
            error=str(exc_val) if exc_val else None,
            model_name=self.model_name
        )
