export interface ExecutiveSummaryData {
  primaryFinding: string;
  briefing: string;
  overallHealth?: string;
  momChange?: number;
}

export interface MarketAnalysisData {
  pricesTrajectory: string;
  consumptionSeasonality: string;
  rootCauseAttribution: string;
}

export interface CostBreakdownData {
  totalRatePerKwh: number;
  currency?: string;
  unit?: string;
  generationPct: number;
  transmissionPct: number;
  distributionPct: number;
  taxesFeesPct: number;
}

export type RiskSeverity = 'Low' | 'Medium' | 'High';

export interface RiskItem {
  category: string;
  severity: RiskSeverity;
  justification: string;
}

export interface RiskAssessmentData {
  risks: RiskItem[];
}

export interface ForecastHorizon {
  horizon: string;
  confidence: string;
  change: string;
  assumptions: string[];
}

export interface ForecastOutlookData {
  shortTerm: ForecastHorizon;
  mediumTerm: ForecastHorizon;
  longTerm: ForecastHorizon;
}

export interface ReportHeaderMeta {
  title?: string;
  date?: string;
  referenceNo?: string;
  state?: string;
  utility?: string;
}

// --- Extended Sections 6-14 Interfaces ---

export interface DriverItem {
  title: string;
  impact: string;
  description: string;
}
export interface DriversBehindTrendData {
  drivers: DriverItem[];
}

export interface GeographicMetric {
  location: string;
  avgRate: string;
  status: string;
  notes: string;
}
export interface GeographicIntelligenceData {
  summary: string;
  metrics: GeographicMetric[];
}

export interface CustomerConsumptionData {
  monthlyUsageKwh: number;
  peakDemandKw: number;
  loadFactorPct: number;
  seasonalBehavior: string;
  peerComparison: string;
  anomaliesObserved: string;
}

export interface EconomicImpactItem {
  sector: 'Residential' | 'Commercial' | 'Industrial' | 'Utilities' | 'Grid Operators';
  billImpact: string;
  operationalImpact: string;
  savingsOpportunity: string;
}
export interface EconomicImpactData {
  impacts: EconomicImpactItem[];
}

export interface WeatherMetric {
  metric: string;
  value: string;
  billImpact: string;
}
export interface WeatherClimateData {
  summary: string;
  metrics: WeatherMetric[];
}

export interface ForecastDriverItem {
  factor: string;
  contributionPct: number;
  confidencePct: number;
  supportingEvidence: string;
}
export interface ForecastDriversData {
  drivers: ForecastDriverItem[];
}

export interface RecommendationItem {
  target: 'Customer' | 'Business' | 'Utility' | 'Grid Operator' | 'Regulator';
  action: string;
  expectedOutcome: string;
}
export interface ReportRecommendationsData {
  recommendations: RecommendationItem[];
}

export interface ConfidenceAssessmentData {
  overallConfidencePct: number;
  dataCompletenessPct: number;
  modelAgreementPct: number;
  qualityScore: string;
  availableDatasets: string[];
  missingDatasets: string[];
}

export interface DataSourceItem {
  name: string;
  dateRange: string;
  updateFrequency: string;
  model: string;
}
export interface DataSourcesData {
  sources: DataSourceItem[];
  limitations: string;
}

export interface ExecutiveReportData {
  header?: ReportHeaderMeta;
  executiveSummary: ExecutiveSummaryData;
  marketAnalysis: MarketAnalysisData;
  costBreakdown: CostBreakdownData;
  riskAssessment: RiskAssessmentData;
  forecastOutlook: ForecastOutlookData;
  driversBehindTrend?: DriversBehindTrendData;
  geographicIntelligence?: GeographicIntelligenceData;
  customerConsumption?: CustomerConsumptionData;
  economicImpact?: EconomicImpactData;
  weatherClimate?: WeatherClimateData;
  forecastDrivers?: ForecastDriversData;
  recommendations?: ReportRecommendationsData;
  confidenceAssessment?: ConfidenceAssessmentData;
  dataSources?: DataSourcesData;
}

export interface ExecutiveEnergyIntelligenceReportProps {
  report?: ExecutiveReportData;
  reportData?: any;
  contextInfo?: {
    state?: string;
    utility?: string;
    region?: string;
    timePeriod?: string;
    zipCode?: string;
  };
  onStateChange?: (state: string) => void;
  onNavigateSubTab?: (tabId: string) => void;
  onRegenerate?: () => void;
  isGenerating?: boolean;
}
