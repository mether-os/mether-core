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

interface ResearchStore {
  isOpen: boolean;
  setOpen: (open: boolean) => void;
  activeTaskId: string | null;
  setActiveTaskId: (id: string | null) => void;
  taskState: ResearchTaskState | null;
  setTaskState: (state: ResearchTaskState | null) => void;
  sections: any[];
  setSections: (sections: any[]) => void;
  sources: any[];
  setSources: (sources: any[]) => void;
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
