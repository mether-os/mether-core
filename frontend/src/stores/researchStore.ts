import { create } from "zustand";

export interface ResearchTaskState {
  id: string;
  topic: string;
  status: "queued" | "running" | "paused" | "cancelled" | "completed" | "failed";
  stage: "planning" | "awaiting_outline_approval" | "collecting" | "writing" | "awaiting_draft_approval" | "reviewing" | "awaiting_final_approval" | "exporting" | "completed" | "human_review";
  depth: string;
  length_target: string;
  progress_percent: number;
  estimated_completion_time: number | null;
  output_path: string | null;
  error_message: string | null;
  research_mode: string;
  target_audience: string;
  human_review_enabled: number;
  avg_confidence?: number;
}

export interface ResearchSectionState {
  id: number;
  task_id: string;
  title: string;
  order_idx: number;
  status: "pending" | "in_progress" | "completed" | "failed";
  instructions: string | null;
  content: string | null;
  validated_content: string | null;
}

export interface ResearchSourceState {
  id: number;
  task_id: string;
  url: string;
  title: string | null;
  snippet: string | null;
  source_type: string;
  publication_date: string | null;
  author: string | null;
  domain: string | null;
  credibility_score: number;
  trust_score: number;
  extracted_facts?: string;
}

export interface ResearchClaimState {
  id: number;
  task_id: string;
  section_id: number;
  claim_text: string;
  evidence: string;
  source_url: string;
  verification_status: "Verified" | "Partially Verified" | "Contradicted" | "Hypothesis" | "Unverified";
  confidence_score: number;
  source_quality_score: number;
  cross_validation_count: number;
}

export interface ResearchContradictionState {
  id: number;
  task_id: string;
  claim_a_id: number;
  claim_b_id: number;
  source_a_url: string;
  source_b_url: string;
  field_type: string;
  possible_explanations: string[];
  human_review_recommended: number;
}

export interface SourceIndependenceState {
  id: number;
  task_id: string;
  url: string;
  independence_score: number;
  duplicate_of_url: string | null;
  duplication_type: "original" | "derivative" | "syndicated" | "copied";
  similarity_score: number;
}

export interface SourceNetworkState {
  id: number;
  task_id: string;
  url: string;
  parent_url: string | null;
  claim_count: number;
  echo_chamber_risk_score: number;
  citation_chain_depth: number;
}

export interface DevilsAdvocateState {
  counter_arguments: string[];
  alternative_interpretations: string[];
  confidence_risks: string[];
  why_wrong: string[];
}

export interface DecisionLayerState {
  key_findings: string[];
  green_flags: string[];
  red_flags: string[];
  open_questions: string[];
  risks: string[];
  opportunities: string[];
  decision_summary: string;
  confidence_level: number;
  target_audience: string;
  devils_advocate_summary?: string;
}

export interface RecommendedAction {
  action: string;
  priority: number;
  category: string;
  estimated_impact: "High" | "Medium" | "Low";
  estimated_effort: "High" | "Medium" | "Low";
  rationale: string;
  owner_type: string;
  timeline: string;
  speculative: boolean;
}

export interface ActionPlanState {
  actions: RecommendedAction[];
  next_steps: string[];
  quick_wins: string[];
  long_term_actions: string[];
}

export interface HumanReviewItem {
  id: number;
  task_id: string;
  claim_id: number;
  source_url: string;
  snapshot_excerpt: string;
  review_reason: string;
  status: "pending" | "approved" | "rejected" | "flagged";
  reviewer_notes?: string;
}

interface ResearchStore {
  isOpen: boolean;
  setOpen: (open: boolean) => void;
  activeTaskId: string | null;
  setActiveTaskId: (id: string | null) => void;
  taskState: ResearchTaskState | null;
  setTaskState: (state: ResearchTaskState | null) => void;
  sections: ResearchSectionState[];
  setSections: (sections: ResearchSectionState[]) => void;
  sources: ResearchSourceState[];
  setSources: (sources: ResearchSourceState[]) => void;
  claims: ResearchClaimState[];
  setClaims: (claims: ResearchClaimState[]) => void;
  contradictions: ResearchContradictionState[];
  setContradictions: (contradictions: ResearchContradictionState[]) => void;
  independence: SourceIndependenceState[];
  setIndependence: (independence: SourceIndependenceState[]) => void;
  network: SourceNetworkState[];
  setNetwork: (network: SourceNetworkState[]) => void;
  devilsAdvocate: DevilsAdvocateState | null;
  setDevilsAdvocate: (da: DevilsAdvocateState | null) => void;
  decision: DecisionLayerState | null;
  setDecision: (decision: DecisionLayerState | null) => void;
  actionPlan: ActionPlanState | null;
  setActionPlan: (plan: ActionPlanState | null) => void;
  humanReviews: HumanReviewItem[];
  setHumanReviews: (items: HumanReviewItem[]) => void;
  progressMessage: string;
  setProgressMessage: (msg: string) => void;
}

export const useResearchStore = create<ResearchStore>((set) => ({
  isOpen: false,
  setOpen: (open) => set({ isOpen: open }),
  activeTaskId: null,
  setActiveTaskId: (id) => set({ activeTaskId: id }),
  taskState: null,
  setTaskState: (state) => set({ taskState: state }),
  sections: [],
  setSections: (sections) => set({ sections }),
  sources: [],
  setSources: (sources) => set({ sources }),
  claims: [],
  setClaims: (claims) => set({ claims }),
  contradictions: [],
  setContradictions: (contradictions) => set({ contradictions }),
  independence: [],
  setIndependence: (independence) => set({ independence }),
  network: [],
  setNetwork: (network) => set({ network }),
  devilsAdvocate: null,
  setDevilsAdvocate: (da) => set({ devilsAdvocate: da }),
  decision: null,
  setDecision: (decision) => set({ decision }),
  actionPlan: null,
  setActionPlan: (plan) => set({ actionPlan: plan }),
  humanReviews: [],
  setHumanReviews: (items) => set({ humanReviews: items }),
  progressMessage: "Standby.",
  setProgressMessage: (msg) => set({ progressMessage: msg }),
}));
