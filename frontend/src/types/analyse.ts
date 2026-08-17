import type { DossierStatus } from '@/types/dossier'


export type AnalyseTabId =
  | 'synthese'
  | 'bien'
  | 'ratios'
  | 'factorielle'
  | 'comportement'
  | 'benchmark'
  | 'memo'

export type DecisionKind = 'approve' | 'reserve' | 'reject'

export type RatioStatus = 'GOOD' | 'WARN' | 'BAD'
export type TraceLineType = 'in' | 'ok' | 'warn' | 'res'
export type SignalTone = 'ok' | 'warn'

export interface AnalyseHeader {
  id: string
  shortCode: string
  companyName: string
  subtitle: string
  status: DossierStatus
  statusLabel: string
  analyst: string
  amountFinanced: number
  assetValue: number
  durationMonths: number
  apportPct: number
  location: string
}

export interface PipelineStepMeta {
  label: string
  meta: string
}

export interface PipelineTraceLine {
  type: TraceLineType
  text: string
  step: number
}

export interface PipelineData {
  policyVersion: string
  steps: PipelineStepMeta[]
  
  fullTrace: PipelineTraceLine[]
  initialStep: number
  initialScore: number
}

export interface DocumentItem {
  id: string
  name: string
  meta: string
  confidence: number
  uploadName?: string
}

export interface MissingDocument {
  id: string
  name: string
  meta: string
}

export interface ExtractedField {
  label: string
  value: string
  source: string
  confidence: number
}

export interface DocumentExtraction {
  title: string
  flag: string
  fields: ExtractedField[]
}

export interface DocumentsBlock {
  present: number
  total: number
  completenessPct: number
  items: DocumentItem[]
  missing: MissingDocument[]
  
  extractions: Record<string, DocumentExtraction>
  defaultDocId: string
}

export interface ScoreFactor {
  label: string
  impact: number
}

export interface ScoringAttention {
  pointsForts: string[]
  pointsVigilance: string[]
  scoreFinal: string
}

export interface TrendYear {
  year: string
  caLabel: string
  caHeightPct: number
  rnHeightPct: number
}

export interface ScoringBlock {
  score: number
  classe?: string
  recommendation: string
  riskLabel: string
  summary: string
  modelConfidencePct?: number
  ratiosOk: number
  ratiosTotal: number
  dossierCompletenessPct: number
  factors: ScoreFactor[]
  trend: TrendYear[]
  trendCaption: string
  attention: ScoringAttention
}

export interface RatioItem {
  label: string
  formula: string
  value: string
  status: RatioStatus
  barPct: number
  interpretation: string
}

export interface FiscalKpi {
  label: string
  value: string
  tone: 'neutral' | 'warn' | 'ok'
}

export interface RatiosBlock {
  calcTime: string
  conformCount: number
  watchCount: number
  items: RatioItem[]
  fiscal: FiscalKpi[]
}

export interface BienUnit {
  qty: string
  designation: string
  marque: string
  modele: string
  annee: string
  valeur: string
}

export interface BienBlock {
  title: string
  subtitle: string
  assetValueLabel: string
  financedLabel: string
  durationLabel: string
  residualLabel: string
  units: BienUnit[]
  totalTtcLabel: string
  specs: Array<{ key: string; value: string }>
  schedule: Array<{ label: string; count: string; amount: string; highlight?: boolean }>
  totalCostLabel: string
  creditCostLabel: string
  guarantees: Array<{ ok: boolean; title: string; detail: string }>
}

export interface FactorAxisRow {
  label: string
  y1: string
  y2: string
  y3: string
  variation: string
  variationTone: 'up' | 'flat' | 'down'
}

export interface FactorAxisRatio {
  label: string
  value: string
  status: RatioStatus
}

export interface FactorAxis {
  num: string
  title: string
  unit: string
  yearLabels?: [string, string, string] | string[]
  rows: FactorAxisRow[]
  ratios: FactorAxisRatio[]
}

export interface BehaviourMetric {
  label: string
  value: string
  tone: 'neutral' | 'ok' | 'warn'
  sub: string
}

export interface BehaviourMonth {
  label: string
  valueK: number
}

export interface BehaviourSignal {
  tone: SignalTone
  title: string
  detail: string
}

export interface BehaviourBlock {
  score: number
  profileLabel: string
  summary: string
  metrics: BehaviourMetric[]
  months: BehaviourMonth[]
  signals: BehaviourSignal[]
}

export interface BenchmarkRow {
  label: string
  client: string
  median: string
  clientPct: number
  medianPct: number
  tone: 'ok' | 'bad'
  percentile: string
}

export interface ComparableCase {
  id: string
  name: string
  score: number
  decision: string
  decisionTone: 'ok' | 'warn'
  date: string
}

export interface BenchmarkBlock {
  sectorLabel: string
  sampleSize: number
  caption: string
  rows: BenchmarkRow[]
  aboveMedianLabel: string
  comparables: ComparableCase[]
}

export interface MemoSection {
  title: string
  paragraphs?: string[]
  table?: { headers: string[]; rows: string[][] }
  tableNote?: string
  chips?: Array<{ ok: boolean; label: string; value: string }>
  risks?: Array<{ tone: 'warn' | 'info'; text: string }>
  conditions?: string[]
  conclusionBanner?: string
}

export interface MemoBlock {
  title: string
  subtitle: string
  refLine: string
  recommendation: string
  scoreLine: string
  clientGrid: Array<{ label: string; value: string }>
  sections: MemoSection[]
  signerName: string
  signerRole: string
  signedAt: string
}

export interface CopilotQa {
  pourquoi: string
  risque: string
  complet: string
  secteur: string
  fallback: string
}

export interface CopilotBlock {
  welcomeMessage: string
  chips: Array<{ label: string; intent: keyof Omit<CopilotQa, 'fallback'> }>
  qa: CopilotQa
}


export interface AnalyseWorkspace {
  header: AnalyseHeader
  pipeline: PipelineData
  documents: DocumentsBlock
  scoring: ScoringBlock
  ratios: RatiosBlock
  bien: BienBlock
  factorielle: FactorAxis[]
  yearLabels?: [string, string, string] | string[]
  comportement: BehaviourBlock
  benchmark: BenchmarkBlock
  memo: MemoBlock
  copilot: CopilotBlock
}

export type AnalyseDecisionPayload = {
  decision: DecisionKind
  comment?: string
}
