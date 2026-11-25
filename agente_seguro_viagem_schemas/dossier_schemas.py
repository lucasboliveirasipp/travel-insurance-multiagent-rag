"""Schemas Pydantic para validação de dossiês técnicos."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class DossierSection(BaseModel):
    """Schema para seção de um dossiê."""
    
    title: str = Field(..., description="Título da seção")
    content: str = Field(..., description="Conteúdo da seção")
    sources: List[str] = Field(
        default_factory=list,
        description="Fontes utilizadas na seção"
    )
    
    class Config:
        extra = "forbid"


class DossierMetadata(BaseModel):
    """Schema para metadados do dossiê."""
    
    query: str = Field(..., description="Consulta original")
    query_intent: str = Field(..., description="Intenção identificada")
    generated_at: datetime = Field(default_factory=datetime.now, description="Data de geração")
    total_sections: int = Field(..., ge=1, description="Número de seções")
    sources_used: List[str] = Field(
        default_factory=list,
        description="Fontes utilizadas"
    )
    processing_time_seconds: Optional[float] = Field(None, description="Tempo de processamento")
    
    class Config:
        extra = "forbid"


class Dossier(BaseModel):
    """Schema para dossiê técnico completo."""
    
    title: str = Field(..., description="Título do dossiê")
    summary: str = Field(..., description="Resumo executivo")
    sections: List[DossierSection] = Field(..., description="Seções do dossiê")
    conclusion: Optional[str] = Field(None, description="Conclusão")
    metadata: DossierMetadata = Field(..., description="Metadados do dossiê")
    
    class Config:
        extra = "forbid"
    
    def to_markdown(self) -> str:
        """Converte dossiê para formato Markdown.
        
        Returns:
            String em formato Markdown
        """
        lines = [
            f"# {self.title}",
            "",
            "## Resumo Executivo",
            "",
            self.summary,
            "",
        ]
        
        for section in self.sections:
            lines.extend([
                f"## {section.title}",
                "",
                section.content,
                "",
            ])
            
            if section.sources:
                lines.append("**Fontes:**")
                for source in section.sources:
                    lines.append(f"- {source}")
                lines.append("")
        
        if self.conclusion:
            lines.extend([
                "## Conclusão",
                "",
                self.conclusion,
                "",
            ])
        
        lines.extend([
            "---",
            "",
            f"*Gerado em: {self.metadata.generated_at.strftime('%d/%m/%Y %H:%M:%S')}*",
        ])
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte dossiê para dicionário.
        
        Returns:
            Dicionário com dados do dossiê
        """
        return {
            "title": self.title,
            "summary": self.summary,
            "sections": [s.dict() for s in self.sections],
            "conclusion": self.conclusion,
            "metadata": self.metadata.dict()
        }

