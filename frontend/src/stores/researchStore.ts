import { create } from "zustand";

export interface ResearchTaskState {
  id: string;
  topic: string;
  status: "queued" | "running" | "paused" | "cancelled" | "completed" | "failed";
  stage: "planning" | "awaiting_outline_approval" | "collecting" | "writing" | "awaiting_draft_approval" | "reviewing" | "awaiting_final_approval" | "exporting" | "completed";
  depth: string;
  length_target: string;
  progress_percent: number;
  estimated_completion_time: number | null;
  output_path: string | null;
  error_message: string | null;
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
  progressMessage: "Standby.",
  setProgressMessage: (msg) => set({ progressMessage: msg }),
}));
