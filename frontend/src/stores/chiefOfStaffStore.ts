import { create } from "zustand";

export interface GoalState {
  id: string;
  title: string;
  description: string | null;
  category: string;
  target_date: string | null;
  status: "pending" | "in_progress" | "completed" | "failed";
  health_score: number;
  streak: number;
  progress?: number;
  created_at: number;
  updated_at: number;
}

export interface MilestoneState {
  id: string;
  goal_id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  status: "pending" | "in_progress" | "completed";
  order_idx: number;
  created_at: number;
  tasks?: TaskState[];
}

export interface TaskState {
  id: string;
  milestone_id: string;
  goal_id: string;
  title: string;
  description: string | null;
  priority: "high" | "medium" | "low";
  status: "pending" | "in_progress" | "completed";
  due_date: string | null;
  time_estimate_mins: number;
  time_invested_mins: number;
  created_at: number;
  updated_at: number;
  subtasks?: SubtaskState[];
}

export interface SubtaskState {
  id: string;
  task_id: string;
  title: string;
  status: "pending" | "completed";
  created_at: number;
}

export interface DailyPrioritiesState {
  date: string;
  priorities: { task_id: string; reason: string }[];
  blockers: { task_id: string; issue: string; recommendation: string }[];
  focus_area: string;
}

export interface WeeklyReviewState {
  id: string;
  week_start: string;
  week_end: string;
  accomplishments: string;
  missed_targets: string;
  risks: string;
  recommendations: string;
  generated_at: number;
}

export interface DashboardStatsState {
  goals_count: number;
  pending_tasks_count: number;
  overdue_tasks_count: number;
  current_streak: number;
}

interface ChiefOfStaffStore {
  isOpen: boolean;
  setOpen: (open: boolean) => void;
  goals: GoalState[];
  setGoals: (goals: GoalState[]) => void;
  selectedGoal: (GoalState & { milestones?: MilestoneState[] }) | null;
  setSelectedGoal: (goal: (GoalState & { milestones?: MilestoneState[] }) | null) => void;
  daily: DailyPrioritiesState | null;
  setDaily: (daily: DailyPrioritiesState | null) => void;
  review: WeeklyReviewState | null;
  setReview: (review: WeeklyReviewState | null) => void;
  recommendations: string;
  setRecommendations: (recs: string) => void;
  stats: DashboardStatsState | null;
  setStats: (stats: DashboardStatsState | null) => void;
  progressMessage: string;
  setProgressMessage: (msg: string) => void;
  progressPercent: number;
  setProgressPercent: (percent: number) => void;
}

export const useChiefOfStaffStore = create<ChiefOfStaffStore>((set) => ({
  isOpen: false,
  setOpen: (open) => set({ isOpen: open }),
  goals: [],
  setGoals: (goals) => set({ goals }),
  selectedGoal: null,
  setSelectedGoal: (goal) => set({ selectedGoal: goal }),
  daily: null,
  setDaily: (daily) => set({ daily }),
  review: null,
  setReview: (review) => set({ review }),
  recommendations: "Standby.",
  setRecommendations: (recs) => set({ recommendations: recs }),
  stats: null,
  setStats: (stats) => set({ stats }),
  progressMessage: "Ready.",
  setProgressMessage: (msg) => set({ progressMessage: msg }),
  progressPercent: 0,
  setProgressPercent: (percent) => set({ progressPercent: percent }),
}));
