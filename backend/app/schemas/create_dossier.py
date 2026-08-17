from pydantic import BaseModel, Field


class EntreprisePayload(BaseModel):
    ice: str
    raisonSociale: str
    rc: str = ""
    secteur: str = ""
    documentNames: list[str] = Field(default_factory=list)


class FinancementPayload(BaseModel):
    nature: str
    montantDemande: float
    valeurBien: float
    dureeMois: int
    apport: float
    urgence: str


class FournisseurBienPayload(BaseModel):
    fournisseur: str
    proformaReference: str
    proformaFileName: str | None = None
    natureBien: str
    etat: str
    valeurHt: float
    valeurTtc: float


class CreateDossierPayload(BaseModel):
    entreprise: EntreprisePayload
    financement: FinancementPayload
    fournisseurBien: FournisseurBienPayload


class CreateDossierResponse(BaseModel):
    id: str
    status: str
    message: str
    job_id: str | None = None
    stream_url: str | None = None
    result_url: str | None = None
    synthese_url: str | None = None
    filename: str | None = None


class StoredFileMeta(BaseModel):
    name: str
    objectKey: str
    size: int
    contentType: str
    category: str


class StoredDossierRecord(BaseModel):
    id: str
    name: str
    sector: str
    amount: int
    duration: int
    score: int = 0
    status: str = "pending"
    analyst: str
    receivedDaysAgo: int = 0
    date: str
    urgency: str | None = None
    receivedLabel: str | None = None
    ice: str
    rc: str = ""
    nature: str
    valeurBien: float
    apport: float
    fournisseur: str
    proformaReference: str
    natureBien: str
    etat: str
    valeurHt: float
    valeurTtc: float
    files: list[StoredFileMeta] = Field(default_factory=list)
    decisionDate: str | None = None
    analyseJobId: str | None = None
    analyseStatus: str | None = None
    analyse: dict | None = None
