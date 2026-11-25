"""Schemas Pydantic para validação de consultas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal


class UserQuery(BaseModel):
    """Schema para consulta do usuário."""
    
    query: str = Field(..., description="Texto da consulta do usuário")
    context: Optional[str] = Field(None, description="Contexto adicional da consulta")
    user_id: Optional[str] = Field(None, description="ID do usuário")
    
    class Config:
        extra = "forbid"


class QueryIntent(BaseModel):
    """Schema para intenção identificada da consulta."""
    
    intent: Literal[
        "simple_query",
        "comparison",
        "coverage_detail",
        "complex_analysis",
        "product_info",
        "other"
    ] = Field(..., description="Tipo de intenção identificada")
    
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confiança na classificação")
    
    requires_analysis: bool = Field(
        False,
        description="Se requer análise do agente analista"
    )
    
    query_type: Optional[str] = Field(None, description="Tipo específico de consulta")
    
    entities: List[str] = Field(
        default_factory=list,
        description="Entidades identificadas na consulta"
    )
    
    class Config:
        extra = "forbid"


class DocumentChunk(BaseModel):
    """Schema para chunk de documento."""
    
    id: str = Field(..., description="ID do chunk")
    content: str = Field(..., description="Conteúdo do chunk")
    page_number: int = Field(..., ge=1, description="Número da página")
    score: float = Field(..., ge=0.0, le=1.0, description="Score de relevância")
    metadata: dict = Field(default_factory=dict, description="Metadados adicionais")
    
    class Config:
        extra = "forbid"

