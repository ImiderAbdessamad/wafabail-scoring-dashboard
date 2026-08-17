"""Schémas jobs d'analyse scoring — extraction v10 + ratios + workspace UI."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

JobStatus = Literal["queued", "processing", "completed", "failed"]

RCC_ELEMENTS: list[tuple[int, str, str, str]] = [
    (1, "ACTIFS_IMMOBILISES", "Actifs immobilisés", "Bilan Actif"),
    (2, "TOTAL_BILAN", "Total bilan", "Bilan Actif"),
    (3, "CHIFFRE_AFFAIRES", "Chiffre d'affaires", "CPC"),
    (4, "CA_EXPORT", "Chiffre d'affaires à l'export", "CPC"),
    (5, "DETTES_BANCAIRES_MLT", "Dettes bancaires MLT", "Bilan Passif"),
    (6, "DETTES_BANCAIRES_CT", "Dettes bancaires CT", "Bilan Passif"),
    (7, "PASSIF_CIRCULANT", "Passif circulant", "Bilan Passif"),
    (8, "DETTES_FOURNISSEURS", "Dettes fournisseurs", "Bilan Passif"),
    (9, "COMPTE_COURANT_ASSOCIES", "Compte courant d'associés", "Bilan"),
    (10, "TRESORERIE_PASSIF", "Trésorerie passif", "Bilan Passif"),
    (11, "ACTIF_CIRCULANT", "Actif circulant", "Bilan Actif"),
    (12, "CREANCES_CLIENTS", "Créances clients", "Bilan Actif"),
    (13, "TRESORERIE_ACTIF", "Trésorerie actif", "Bilan Actif"),
    (14, "CAISSE", "Caisse actif", "Bilan Actif"),
    (15, "ACHATS_REVENDUS", "Achats revendus", "CPC"),
    (16, "ACHATS_CONSOMMES", "Achats consommés", "CPC"),
    (17, "AUTRES_CHARGES_EXTERNES", "Autres charges externes", "CPC"),
    (18, "CHARGES_INTERETS", "Charges d'intérêts", "CPC"),
    (19, "RESULTAT_NET", "Résultat net", "CPC"),
    (20, "TYPE_RESULTAT", "Type de résultat", "Dérivé"),
]

SCORING_EXTRA_ELEMENTS: list[tuple[int, str, str, str]] = [
    (21, "FONDS_PROPRES", "Fonds propres", "Bilan Passif"),
    (22, "STOCKS", "Stocks", "Bilan Actif"),
    (23, "RESULTAT_EXPLOITATION", "Résultat d'exploitation", "CPC"),
    (24, "DOTATIONS_EXPLOITATION", "Dotations d'exploitation", "CPC"),
    (25, "DETTES_FINANCIERES", "Dettes financières (MLT+CT)", "Dérivé"),
    (26, "ENDETTEMENT_TERME", "Endettement à terme", "Dérivé"),
    (27, "TRESORERIE_NETTE", "Trésorerie nette", "Dérivé"),
    (28, "FDR", "Fonds de roulement", "Dérivé"),
    (29, "BFR", "Besoin en fonds de roulement", "Dérivé"),
    (30, "CAF", "Capacité d'autofinancement", "Dérivé"),
]


class CompanyInfo(BaseModel):
    raison_sociale: str | None = None
    identifiant_fiscal: str | None = None
    ice: str | None = None
    rc: str | None = None
    adresse: str | None = None
    ville: str | None = None


class ExerciseInfo(BaseModel):
    debut: str | None = None
    fin: str | None = None
    label: str | None = None


class FinancialPageAudit(BaseModel):
    page_number: int
    detected_type: str
    orientation: int = 0
    extraction_status: str = "empty"
    extraction_strategy: str = ""
    candidates_count: int = 0
    error: str | None = None


class DocumentSummary(BaseModel):
    filename: str
    pages_total: int
    pages_processed: int
    pages_skipped: int
    pages_failed: int
    document_type: str = "LIASSE_FISCALE"
    company: CompanyInfo = Field(default_factory=CompanyInfo)
    exercise: ExerciseInfo = Field(default_factory=ExerciseInfo)


class ExtractionSummary(BaseModel):
    model: str
    page_audit: list[FinancialPageAudit] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FieldEvidence(BaseModel):
    page_number: Optional[int] = None
    raw_label: Optional[str] = None
    raw_value: Optional[str] = None
    column_name: Optional[str] = None
    page_type: Optional[str] = None
    confidence: Optional[float] = None
    source_excerpt: Optional[str] = None


class ExtractedField(BaseModel):
    number: int
    code: str
    label: str
    value: Optional[float] = None
    unit: str = "MAD"
    source: str
    status: str = "missing"
    note: Optional[str] = None
    confidence: float = 0.0
    value_n1: Optional[float] = None
    evidence: list[FieldEvidence] = Field(default_factory=list)


class AccountingControlView(BaseModel):
    code: str
    status: str
    label: str
    expected: Optional[float] = None
    observed: Optional[float] = None
    difference: Optional[float] = None
    tolerance: Optional[float] = None
    affected_fields: list[str] = Field(default_factory=list)
    message: str = ""


class YearsBlock(BaseModel):
    labels: list[str] = Field(default_factory=lambda: ["—", "N-1", "N"])
    years: list[int | None] = Field(default_factory=lambda: [None, None, None])
    available_count: int = 0
    series: dict[str, list[Optional[float]]] = Field(default_factory=dict)


class ScoringAnalysisResult(BaseModel):
    document: DocumentSummary
    extraction: ExtractionSummary
    fields: list[ExtractedField]
    completeness_pct: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    controls: list[AccountingControlView] = Field(default_factory=list)
    ratio_inputs: dict[str, Optional[float]] = Field(default_factory=dict)
    ratios: dict[str, Any] = Field(default_factory=dict)
    axes: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    years: YearsBlock = Field(default_factory=YearsBlock)


class AnalyseJobProgress(BaseModel):
    job_id: str
    dossier_id: str | None = None
    status: JobStatus
    progress_pct: int = 0
    current_step: str = "queued"
    current_page: int | None = None
    pages_total: int | None = None
    pages_financial: int = 0
    pages_skipped: int = 0
    pages_failed: int = 0
    message: str = ""
    error: str | None = None
    stream_url: str | None = None
    result_url: str | None = None
    filename: str | None = None


class AnalyseJobCreateResponse(BaseModel):
    job_id: str
    dossier_id: str
    status: JobStatus = "queued"
    stream_url: str
    result_url: str
    filename: str


class AnalyseStateResponse(BaseModel):
    dossier_id: str
    job: AnalyseJobProgress | None = None
    workspace: dict[str, Any] | None = None
    error: str | None = None


class DossierSyntheseResponse(BaseModel):
    dossier_id: str
    status: str
    job_id: str | None = None
    points_forts: list[str] = Field(default_factory=list)
    points_vigilance: list[str] = Field(default_factory=list)
    score_final: str | None = None
    score: int | None = None
    classe: str | None = None
    decision: str | None = None
    recommandation: str | None = None
    message: str | None = None


class CopilotHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class CopilotChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[CopilotHistoryMessage] = Field(default_factory=list)


class CopilotChatResponse(BaseModel):
    reply: str
    model: str
