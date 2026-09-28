"""
Modelos de dados para Gestão Multi-Instituição de Ensino (White-Label).
Permite parametrizar qualquer Escola Básica, Colégio, Faculdade ou Universidade,
com controle de planos de assinatura, limites mensais de uso e chaves de acesso isoladas.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class InstitutionType(str, Enum):
    """Categorias de instituições de ensino suportadas."""
    ESCOLA_BASICA = "ESCOLA_BASICA"          # Educação Infantil e Ensino Fundamental
    COLEGIO = "COLEGIO"                      # Ensino Fundamental e Ensino Médio
    ESCOLA_TECNICA = "ESCOLA_TECNICA"        # Cursos Técnicos e Profissionalizantes
    FACULDADE = "FACULDADE"                  # Graduação e Pós-Graduação
    UNIVERSIDADE = "UNIVERSIDADE"            # Graduação, Pós, Mestrado e Doutorado
    CURSOS_LIVRES = "CURSOS_LIVRES"          # Extensão, Idiomas e Treinamentos


class PlanTier(str, Enum):
    """Níveis de planos para instituições contratantes."""
    STARTER = "STARTER"              # Ex: até 150 auditorias/mês
    PROFISSIONAL = "PROFISSIONAL"    # Ex: até 500 auditorias/mês
    ENTERPRISE = "ENTERPRISE"        # Ilimitado / Alta volumetria


class SubscriptionConfig(BaseModel):
    """Controle do Plano, Limites Mensais e Acesso do Contratante."""
    plan_tier: PlanTier = Field(PlanTier.PROFISSIONAL, description="Nível do plano contratado")
    plan_name: str = Field("Plano Profissional", description="Nome descritivo exibido no painel da instituição")
    monthly_limit: int = Field(500, description="Limite mensal de análises de documentos (0 = Ilimitado)")
    current_month_usage: int = Field(0, description="Quantidade de análises consumidas no mês atual")
    is_active: bool = Field(True, description="Status da assinatura: True=Ativo, False=Suspenso")
    admin_access_key: str = Field("secretaria-2026", description="Chave secreta exclusiva da secretaria daquela instituição")
    billing_day: int = Field(1, description="Dia do mês do fechamento/renovação do ciclo")


class BrandingConfig(BaseModel):
    """Configurações visuais personalizadas para a instituição."""
    logo_url: str = Field("/static/images/logo.png", description="Caminho ou URL do logo")
    primary_color: str = Field("#0a2351", description="Cor primária (Hex)")
    secondary_color: str = Field("#fdb913", description="Cor secundária / destaque (Hex)")
    portal_title: str = Field("Portal de Envio de Documentos", description="Título exibido na aba e cabeçalho")


class StorageTopology(BaseModel):
    """Configuração de armazenamento local ou em nuvem para a instituição."""
    provider: str = Field("local", description="Provedor (local, google_drive, s3)")
    base_path: str = Field("storage", description="Caminho base no disco local para salvar arquivos")
    drive_id: Optional[str] = Field(None, description="ID do Drive Compartilhado (legado)")
    root_folder_id: Optional[str] = Field("storage_root", description="ID da pasta raiz")
    partitioning_mode: str = Field("ALPHABETICAL_A_Z", description="Tipo de divisão: 'ALPHABETICAL_A_Z' (pastas de A a Z), 'COURSE_SPLIT' ou 'FLAT'")
    partitions: Dict[str, str] = Field(default_factory=dict, description="Mapeamento de partições")


class ErpIntegrationConfig(BaseModel):
    """Configuração do ERP acadêmico da instituição."""
    erp_type: str = Field("solis", description="Tipo do ERP: 'solis', 'totvs', 'sophia', 'mock'")
    api_url: Optional[str] = Field(None, description="URL base da API do ERP")
    jwt_token_env_var: Optional[str] = Field(None, description="Nome da variável de ambiente com o token")
    reports_map: Dict[str, str] = Field(default_factory=dict, description="IDs dos relatórios no ERP por funcionalidade")


class InstitutionProfile(BaseModel):
    """Perfil completo e independente de uma instituição de ensino cadastrada no sistema."""
    id: str = Field(..., description="Slug único da instituição (ex: 'imes', 'colegio_sao_jose')")
    name: str = Field(..., description="Nome oficial da instituição")
    institution_type: InstitutionType = Field(..., description="Tipo de instituição de ensino")
    branding: BrandingConfig = Field(default_factory=BrandingConfig)
    storage: StorageTopology
    erp: ErpIntegrationConfig = Field(default_factory=ErpIntegrationConfig)
    enabled_courses: List[str] = Field(default_factory=list, description="Lista dos cursos/níveis ativos nesta instituição")
    require_student_cpf: bool = Field(True, description="Se False, permite busca por Matrícula ou Certidão de Nascimento (útil para crianças)")
    subscription: SubscriptionConfig = Field(default_factory=SubscriptionConfig, description="Plano, cotas e chave de acesso da instituição")
