"""Módulo de Conectores de ERP Educacionais."""
from adapters.erp.base import StudentDataProvider, StudentProfile
from adapters.erp.solis_adapter import SolisERPAdapter
from adapters.erp.generic_rest_adapter import GenericRestERPAdapter, MockERPAdapter
from adapters.erp.factory import ERPFactory

__all__ = [
    "StudentDataProvider",
    "StudentProfile",
    "SolisERPAdapter",
    "GenericRestERPAdapter",
    "MockERPAdapter",
    "ERPFactory"
]
