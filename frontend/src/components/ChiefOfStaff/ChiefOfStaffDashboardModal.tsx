import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useChiefOfStaffStore } from "@/stores/chiefOfStaffStore";
import config from "../../config";

export function ChiefOfStaffDashboardModal() {
  const {
    isOpen,
    setOpen,
    goals,
    setGoals,
    selectedGoal,
    setSelectedGoal,
    daily,
    setDaily,
    review,
    setReview,
    recommendations,
    setRecommendations,
    stats,
    setStats,
    progressMessage,
    setProgressMessage,
    progressPercent,
    setProgressPercent
  } = useChiefOfStaffStore();

  // Create Goal fields
  const [goalTitle, setGoalTitle] = useState("");
  const [goalDesc, setGoalDesc] = useState("");
  const [goalCategory, setGoalCategory] = useState("career");
  const [goalTargetDate, setGoalTargetDate] = useState("");
  const [activeTab, setActiveTab] = useState<"priorities" | "review" | "recommendations">("priorities");

  // Load dashboard stats & lists
  const fetchDashboard = useCallback(async () => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

    try {
      const res = await fetch(`${config.backendUrl}/api/v1/cos/dashboard`, { headers });
      const data = await res.json();
      if (data) {
        setGoals(data.goals || []);
        setDaily(data.daily || null);
        setReview(data.review || null);
        setRecommendations(data.recommendations || "");
        setStats(data.stats || null);
      }
    } catch (err) {
      console.error("Failed to load COS dashboard:", err);
    }
  }, [setGoals, setDaily, setReview, setRecommendations, setStats]);

  // Load detailed goal milestone/task hierarchy
  const selectGoalDetail = useCallback(async (goalId: string) => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

    try {
      const res = await fetch(`${config.backendUrl}/api/v1/cos/goals/${goalId}`, { headers });
      const data = await res.json();
      if (data) {
        setSelectedGoal(data);
      }
    } catch (err) {
      console.error("Failed to fetch goal detail:", err);
    }
  }, [setSelectedGoal]);

  useEffect(() => {
    if (isOpen) {
      fetchDashboard();
    }
  }, [isOpen, fetchDashboard]);

  // Create Goal submit
  const handleCreateGoal = async () => {
    if (!goalTitle.trim()) return;
    setProgressMessage("Initiating Strategic Planner...");
    setProgressPercent(10);
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

      const res = await fetch(`${config.backendUrl}/api/v1/cos/goals`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          title: goalTitle,
          description: goalDesc,
          category: goalCategory,
          target_date: goalTargetDate || null
        })
      });
      const data = await res.json();
      if (data.goal_id) {
        setGoalTitle("");
        setGoalDesc("");
        setGoalTargetDate("");
        fetchDashboard();
      }
    } catch (err) {
      console.error(err);
      setProgressMessage("Plan generation failed.");
      setProgressPercent(0);
    }
  };

  // Toggle subtask status
  const handleToggleSubtask = async (subtaskId: string, currentStatus: string) => {
    const newStatus = currentStatus === "completed" ? "pending" : "completed";
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

      await fetch(`${config.backendUrl}/api/v1/cos/subtasks/${subtaskId}`, {
        method: "PUT",
        headers,
        body: JSON.stringify({ status: newStatus })
      });
      if (selectedGoal) {
        selectGoalDetail(selectedGoal.id);
      }
      fetchDashboard();
    } catch (err) {
      console.error(err);
    }
  };

  // Log Task completion / status updates
  const handleUpdateTaskStatus = async (taskId: string, newStatus: string) => {
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

      await fetch(`${config.backendUrl}/api/v1/cos/tasks/${taskId}`, {
        method: "PUT",
        headers,
        body: JSON.stringify({ status: newStatus })
      });
      if (selectedGoal) {
        selectGoalDetail(selectedGoal.id);
      }
      fetchDashboard();
    } catch (err) {
      console.error(err);
    }
  };

  // Force daily priorities regeneration
  const handleGenerateDaily = async () => {
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

      const res = await fetch(`${config.backendUrl}/api/v1/cos/daily/generate`, { method: "POST", headers });
      const data = await res.json();
      if (data) {
        setDaily(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Force weekly review regeneration
  const handleGenerateWeekly = async () => {
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

      const res = await fetch(`${config.backendUrl}/api/v1/cos/review/generate`, { method: "POST", headers });
      const data = await res.json();
      if (data) {
        setReview(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Log task focus time increment
  const handleLogTaskTime = async (taskId: string, mins: number) => {
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

      // First fetch current task details
      await fetch(`${config.backendUrl}/api/v1/cos/dashboard`, { headers });
      
      await fetch(`${config.backendUrl}/api/v1/cos/tasks/${taskId}`, {
        method: "PUT",
        headers,
        body: JSON.stringify({ time_invested_mins: mins })
      });
      if (selectedGoal) {
        selectGoalDetail(selectedGoal.id);
      }
      fetchDashboard();
    } catch (err) {
      console.error(err);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#050810]/95 p-4 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.96 }}
          className="hud-panel w-full max-w-6xl border border-primary/30 relative flex flex-col max-h-[90vh] overflow-hidden"
          style={{ boxShadow: "0 0 35px rgba(139, 92, 246, 0.15)" }}
        >
          {/* Scanline Overlay */}
          <div className="absolute inset-0 scan-line-overlay pointer-events-none opacity-20" />

          {/* Modal Header */}
          <div className="flex justify-between items-center px-6 py-4 border-b border-primary/10 shrink-0">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-secondary animate-pulse" style={{ boxShadow: "0 0 8px #a78bfa" }} />
              <h2 className="hud-label text-glow-purple text-base">CHIEF OF STAFF EXECUTIVE HUD</h2>
            </div>
            <div className="flex items-center gap-4">
              {progressPercent > 0 && progressPercent < 100 && (
                <div className="flex items-center gap-3 text-[10px] font-mono text-secondary">
                  <span>{progressMessage}</span>
                  <div className="w-24 h-1.5 bg-primary/10 border border-primary/20 rounded-full overflow-hidden">
                    <div className="h-full bg-secondary transition-all duration-300" style={{ width: `${progressPercent}%` }} />
                  </div>
                </div>
              )}
              <button 
                onClick={() => setOpen(false)}
                className="text-outline-variant hover:text-secondary transition-colors text-sm font-mono cursor-pointer"
              >
                [✕ CLOSE DIRECTORY]
              </button>
            </div>
          </div>

          {/* Core Stats Bar */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 border-b border-primary/10 bg-primary/[0.02] shrink-0">
              <div className="px-6 py-3 border-r border-primary/10 flex flex-col justify-center">
                <span className="text-[8px] font-mono text-outline uppercase tracking-widest">Active Objectives</span>
                <span className="text-xl font-bold font-mono text-primary text-glow-cyan leading-tight">{stats.goals_count}</span>
              </div>
              <div className="px-6 py-3 border-r border-primary/10 flex flex-col justify-center">
                <span className="text-[8px] font-mono text-outline uppercase tracking-widest">Active Priorities</span>
                <span className="text-xl font-bold font-mono text-secondary text-glow-purple leading-tight">{stats.pending_tasks_count}</span>
              </div>
              <div className="px-6 py-3 border-r border-primary/10 flex flex-col justify-center">
                <span className="text-[8px] font-mono text-outline uppercase tracking-widest">Overdue Blockers</span>
                <span className={`text-xl font-bold font-mono leading-tight ${stats.overdue_tasks_count > 0 ? "text-error" : "text-primary"}`}>
                  {stats.overdue_tasks_count}
                </span>
              </div>
              <div className="px-6 py-3 flex flex-col justify-center">
                <span className="text-[8px] font-mono text-outline uppercase tracking-widest">Consistency Streak</span>
                <span className="text-xl font-bold font-mono text-success text-glow-green leading-tight">🔥 {stats.current_streak} days</span>
              </div>
            </div>
          )}

          {/* Modal Grid Body */}
          <div className="flex-1 overflow-hidden flex flex-col md:flex-row min-h-0">
            
            {/* Left Column: Objectives List & Detail Tree */}
            <div className="w-full md:w-1/2 border-r border-primary/10 flex flex-col min-h-0 bg-surface/30">
              
              <div className="p-4 border-b border-primary/10 flex items-center justify-between shrink-0">
                <span className="hud-label text-[10px] tracking-widest">GOALS DIRECTORY</span>
                {selectedGoal && (
                  <button 
                    onClick={() => setSelectedGoal(null)}
                    className="text-[9px] font-mono text-outline-variant hover:text-primary"
                  >
                    [◀ BACK TO LIST]
                  </button>
                )}
              </div>

              <div className="flex-1 overflow-y-auto p-4" style={{ scrollbarWidth: "none" }}>
                {!selectedGoal ? (
                  <div className="flex flex-col gap-6">
                    {/* Objectives List */}
                    <div className="flex flex-col gap-3">
                      {goals.length === 0 ? (
                        <div className="text-center py-8 text-outline text-[11px] font-mono">
                          NO ACTIVE STRATEGIC GOALS. BOOTSTRAP A TARGET PLAN BELOW.
                        </div>
                      ) : (
                        goals.map((g) => (
                          <div 
                            key={g.id}
                            onClick={() => selectGoalDetail(g.id)}
                            className="hud-panel p-3 border border-primary/15 hover:border-secondary/40 cursor-pointer transition-all duration-300 relative group"
                            style={{
                              background: "linear-gradient(135deg, rgba(76,215,246,0.01) 0%, rgba(139,92,246,0.04) 100%)",
                            }}
                          >
                            <div className="flex justify-between items-start mb-2">
                              <div className="flex flex-col">
                                <span className="text-[8px] font-mono text-secondary tracking-widest uppercase mb-0.5">Category: {g.category}</span>
                                <h3 className="text-primary font-bold text-xs uppercase tracking-wide group-hover:text-glow-cyan transition-all">{g.title}</h3>
                              </div>
                              <div className="flex flex-col items-end">
                                <span className="text-[11px] font-bold font-mono text-secondary">{Math.round(g.progress || 0)}% Complete</span>
                              </div>
                            </div>
                            
                            <p className="text-[10px] text-on-surface-variant line-clamp-2 mb-3">{g.description}</p>
                            
                            <div className="flex items-center justify-between text-[8px] font-mono text-outline">
                              <span>Health Score: <b className="text-primary">{Math.round(g.health_score)}%</b></span>
                              <span>Consistency Streak: <b className="text-success">🔥 {g.streak} days</b></span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Create New Goal form */}
                    <div className="hud-panel p-4 border border-secondary/25 bg-secondary/[0.01] mt-4 relative">
                      <div className="flex items-center gap-1.5 mb-3">
                        <span className="w-1.5 h-3 bg-secondary" />
                        <span className="hud-label text-[9px] tracking-widest">BOOTSTRAP STRATEGIC PLAN</span>
                      </div>
                      
                      <div className="flex flex-col gap-3">
                        <div className="flex flex-col gap-1">
                          <label className="text-[8px] font-mono text-outline uppercase tracking-wider">Goal / Objective</label>
                          <input 
                            type="text"
                            value={goalTitle}
                            onChange={(e) => setGoalTitle(e.target.value)}
                            placeholder="e.g. Land a blockchain internship in 60 days"
                            className="bg-void border border-primary/20 rounded p-2 text-xs text-primary focus:outline-none focus:border-secondary/40 font-mono uppercase"
                          />
                        </div>

                        <div className="flex flex-col gap-1">
                          <label className="text-[8px] font-mono text-outline uppercase tracking-wider">Context Description</label>
                          <textarea 
                            value={goalDesc}
                            onChange={(e) => setGoalDesc(e.target.value)}
                            placeholder="Describe scope details, target technologies, or key focus areas..."
                            rows={3}
                            className="bg-void border border-primary/20 rounded p-2 text-xs text-secondary focus:outline-none focus:border-secondary/40 font-mono"
                          />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                          <div className="flex flex-col gap-1">
                            <label className="text-[8px] font-mono text-outline uppercase">Category</label>
                            <select 
                              value={goalCategory}
                              onChange={(e) => setGoalCategory(e.target.value)}
                              className="bg-void border border-primary/20 rounded p-1.5 text-xs text-secondary focus:outline-none font-mono"
                            >
                              <option value="career">Career / Academy</option>
                              <option value="finance">Finance</option>
                              <option value="health">Health / Habit</option>
                              <option value="personal">Personal Growth</option>
                            </select>
                          </div>
                          <div className="flex flex-col gap-1">
                            <label className="text-[8px] font-mono text-outline uppercase">Target Due Date</label>
                            <input 
                              type="date"
                              value={goalTargetDate}
                              onChange={(e) => setGoalTargetDate(e.target.value)}
                              className="bg-void border border-primary/20 rounded p-1.5 text-xs text-secondary focus:outline-none font-mono"
                            />
                          </div>
                        </div>

                        <button 
                          onClick={handleCreateGoal}
                          className="hud-button w-full py-2 border-secondary/40 hover:bg-secondary/10 mt-2 text-[9px] tracking-widest font-bold text-secondary text-glow-purple uppercase"
                        >
                          LAUNCH PLANNER AGENT
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  // Goal detailed milestones / task tree
                  <div className="flex flex-col gap-5">
                    <div className="hud-panel p-3 border border-secondary/25 bg-secondary/[0.01]">
                      <h3 className="text-secondary font-bold text-xs uppercase mb-1">{selectedGoal.title}</h3>
                      <p className="text-[10px] text-on-surface-variant mb-3">{selectedGoal.description}</p>
                      
                      <div className="w-full bg-primary/10 h-1.5 rounded-full overflow-hidden mb-2">
                        <div className="h-full bg-secondary transition-all duration-300" style={{ width: `${selectedGoal.progress}%` }} />
                      </div>
                      <div className="flex justify-between items-center text-[8px] font-mono text-outline">
                        <span>Overall Progress: <b>{Math.round(selectedGoal.progress || 0)}%</b></span>
                        <span>Health: <b>{Math.round(selectedGoal.health_score)}%</b></span>
                      </div>
                    </div>

                    <div className="flex flex-col gap-4">
                      {selectedGoal.milestones?.map((m) => (
                        <div key={m.id} className="border-l border-primary/20 pl-4 py-1 relative">
                          {/* Anchor dot */}
                          <span className="absolute -left-[5px] top-1.5 w-2 h-2 rounded-full bg-secondary" style={{ boxShadow: "0 0 6px #a78bfa" }} />
                          
                          <div className="mb-2">
                            <h4 className="text-primary font-bold text-[11px] uppercase tracking-wider">{m.title}</h4>
                            <span className="text-[8px] font-mono text-outline-variant uppercase">Target Offset: {m.due_date}</span>
                          </div>

                          <div className="flex flex-col gap-2.5 mt-2 pl-1">
                            {m.tasks?.map((t) => (
                              <div key={t.id} className="p-2.5 bg-primary/[0.02] border border-primary/10 rounded">
                                <div className="flex items-start justify-between mb-1.5">
                                  <div className="flex items-center gap-2">
                                    <input 
                                      type="checkbox"
                                      checked={t.status === "completed"}
                                      onChange={() => handleUpdateTaskStatus(t.id, t.status === "completed" ? "pending" : "completed")}
                                      className="w-3.5 h-3.5 border border-primary/30 rounded-sm cursor-pointer accent-secondary"
                                    />
                                    <span className={`text-[10px] uppercase font-bold tracking-wide ${t.status === "completed" ? "line-through text-outline-variant" : "text-primary"}`}>
                                      {t.title}
                                    </span>
                                  </div>
                                  <span className={`text-[7px] font-mono px-1 rounded uppercase ${t.priority === "high" ? "bg-error/10 text-error border border-error/20" : (t.priority === "medium" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" : "bg-primary/10 text-primary border border-primary/20")}`}>
                                    {t.priority}
                                  </span>
                                </div>

                                {t.description && (
                                  <p className="text-[9px] text-on-surface-variant mb-2 pl-5">{t.description}</p>
                                )}

                                {/* Subtasks list */}
                                {t.subtasks && t.subtasks.length > 0 && (
                                  <div className="flex flex-col gap-1.5 ml-5 mt-1.5 pl-2 border-l border-primary/10">
                                    {t.subtasks.map((st) => (
                                      <div key={st.id} className="flex items-center gap-2 text-[9px] font-mono">
                                        <input 
                                          type="checkbox"
                                          checked={st.status === "completed"}
                                          onChange={() => handleToggleSubtask(st.id, st.status)}
                                          className="w-3 h-3 border border-primary/20 rounded-sm cursor-pointer accent-secondary"
                                        />
                                        <span className={st.status === "completed" ? "line-through text-outline-variant" : "text-secondary"}>
                                          {st.title}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                )}

                                {/* Log time widget */}
                                <div className="flex items-center justify-between text-[8px] font-mono text-outline mt-2 pt-2 border-t border-primary/5 pl-5">
                                  <span>Time invested: <b className="text-secondary">{t.time_invested_mins} mins</b> (Est: {t.time_estimate_mins} mins)</span>
                                  <div className="flex items-center gap-1.5">
                                    <button 
                                      onClick={() => handleLogTaskTime(t.id, t.time_invested_mins + 15)}
                                      className="px-1 py-0.5 border border-primary/20 hover:border-secondary/40 text-[7px] rounded"
                                    >
                                      +15M
                                    </button>
                                    <button 
                                      onClick={() => handleLogTaskTime(t.id, t.time_invested_mins + 60)}
                                      className="px-1 py-0.5 border border-primary/20 hover:border-secondary/40 text-[7px] rounded"
                                    >
                                      +1H
                                    </button>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: Execution Priorities, Review, and Recommendations */}
            <div className="w-full md:w-1/2 flex flex-col min-h-0 bg-surface/10">
              
              {/* Tab Selector */}
              <div className="flex border-b border-primary/10 shrink-0">
                <button 
                  onClick={() => setActiveTab("priorities")}
                  className={`flex-1 py-3 text-center text-[9px] tracking-widest font-mono font-bold uppercase transition-colors border-r border-primary/10 ${activeTab === "priorities" ? "bg-secondary/10 text-secondary border-b-2 border-b-secondary" : "text-outline hover:text-primary"}`}
                >
                  TODAY'S PRIORITIES
                </button>
                <button 
                  onClick={() => setActiveTab("recommendations")}
                  className={`flex-1 py-3 text-center text-[9px] tracking-widest font-mono font-bold uppercase transition-colors border-r border-primary/10 ${activeTab === "recommendations" ? "bg-secondary/10 text-secondary border-b-2 border-b-secondary" : "text-outline hover:text-primary"}`}
                >
                  ADAPTIVE SUGGESTIONS
                </button>
                <button 
                  onClick={() => setActiveTab("review")}
                  className={`flex-1 py-3 text-center text-[9px] tracking-widest font-mono font-bold uppercase transition-colors ${activeTab === "review" ? "bg-secondary/10 text-secondary border-b-2 border-b-secondary" : "text-outline hover:text-primary"}`}
                >
                  WEEKLY PERFORMANCE
                </button>
              </div>

              {/* Tab Content */}
              <div className="flex-1 overflow-y-auto p-5" style={{ scrollbarWidth: "none" }}>
                {activeTab === "priorities" && (
                  <div className="flex flex-col gap-4">
                    <div className="flex justify-between items-center mb-1">
                      <div className="flex flex-col">
                        <span className="text-[8px] font-mono text-outline uppercase tracking-wider">Focus Theme</span>
                        <span className="text-primary font-bold text-xs uppercase tracking-wide text-glow-cyan">{daily?.focus_area || "General Progression"}</span>
                      </div>
                      <button 
                        onClick={handleGenerateDaily}
                        className="hud-chip hud-chip--primary text-[8px] font-mono cursor-pointer uppercase"
                      >
                        [REGENERATE AGENDA]
                      </button>
                    </div>

                    <div className="flex flex-col gap-3">
                      <div className="flex items-center gap-1.5 mb-1 mt-2">
                        <span className="w-1.5 h-3 bg-primary" />
                        <span className="hud-label text-[8px] tracking-widest uppercase">AGENDA TARGETS</span>
                      </div>

                      {!daily?.priorities || daily.priorities.length === 0 ? (
                        <div className="text-center py-6 text-outline text-[10px] font-mono">
                          NO ACTIVE PRIORITIES FOR TODAY. GENERATE FROM ACTIVE GOALS.
                        </div>
                      ) : (
                        daily.priorities.map((item, idx) => (
                          <div key={idx} className="p-3 bg-primary/[0.02] border border-primary/10 rounded-sm">
                            <span className="text-[8px] font-mono text-secondary tracking-widest uppercase mb-1 block">Priority #{idx+1}</span>
                            <span className="text-[10px] text-primary uppercase font-bold tracking-wide block mb-1.5">{item.task_id}</span>
                            <p className="text-[9.5px] text-on-surface-variant font-mono leading-relaxed">{item.reason}</p>
                          </div>
                        ))
                      )}

                      {/* Active Blocker Warnings */}
                      {daily?.blockers && daily.blockers.length > 0 && (
                        <div className="flex flex-col gap-2 mt-4 bg-error/5 border border-error/25 p-3 rounded-sm">
                          <div className="flex items-center gap-1.5 text-error mb-1">
                            <span className="w-1.5 h-3 bg-error animate-pulse" />
                            <span className="hud-label text-[8px] tracking-widest uppercase font-bold text-glow-red">CRITICAL OPERATIONAL BLOCKERS</span>
                          </div>
                          {daily.blockers.map((b, idx) => (
                            <div key={idx} className="text-[9px] font-mono text-error/95 flex flex-col gap-1 border-b border-error/10 pb-2 last:border-b-0 last:pb-0">
                              <span>⚠️ Task: <b>{b.task_id}</b></span>
                              <span>Issue: {b.issue}</span>
                              <span className="text-primary font-bold">Solution: {b.recommendation}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {activeTab === "recommendations" && (
                  <div className="flex flex-col gap-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="hud-label text-[9px] tracking-widest uppercase">AGENT RECOMMENDATION STREAM</span>
                    </div>

                    <div className="hud-panel p-4 border border-secondary/20 bg-secondary/[0.01] relative">
                      {/* Monospace layout for suggestions */}
                      <div className="text-[10.5px] font-mono text-secondary leading-relaxed whitespace-pre-wrap">
                        {recommendations}
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "review" && (
                  <div className="flex flex-col gap-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="hud-label text-[9px] tracking-widest uppercase">WEEKLY REVIEW SYNOPSIS</span>
                      <button 
                        onClick={handleGenerateWeekly}
                        className="hud-chip hud-chip--primary text-[8px] font-mono cursor-pointer uppercase"
                      >
                        [GENERATE REVIEW]
                      </button>
                    </div>

                    {!review || !review.week_start ? (
                      <div className="text-center py-10 text-outline text-[10px] font-mono">
                        NO WEEKLY REVIEW CACHED. TRIGGER ANALYSIS ABOVE.
                      </div>
                    ) : (
                      <div className="flex flex-col gap-4">
                        <span className="text-[8px] font-mono text-outline uppercase tracking-wider block">
                          REVIEW CYCLE: {review.week_start} // {review.week_end}
                        </span>

                        <div className="flex flex-col gap-3">
                          <div className="hud-panel p-3 border border-success/20 bg-success/[0.01]">
                            <span className="text-[8.5px] font-mono text-success uppercase tracking-wider font-bold mb-1.5 block">Accomplishments</span>
                            <div className="text-[10px] font-mono text-primary leading-relaxed whitespace-pre-wrap">{review.accomplishments}</div>
                          </div>

                          <div className="hud-panel p-3 border border-amber-500/20 bg-amber-500/[0.01]">
                            <span className="text-[8.5px] font-mono text-amber-400 uppercase tracking-wider font-bold mb-1.5 block">Delayed Targets</span>
                            <div className="text-[10px] font-mono text-secondary leading-relaxed whitespace-pre-wrap">{review.missed_targets}</div>
                          </div>

                          <div className="hud-panel p-3 border border-error/20 bg-error/[0.01]">
                            <span className="text-[8.5px] font-mono text-error uppercase tracking-wider font-bold mb-1.5 block">Operational Risks</span>
                            <div className="text-[10px] font-mono text-error/90 leading-relaxed whitespace-pre-wrap">{review.risks}</div>
                          </div>

                          <div className="hud-panel p-3 border border-primary/20 bg-primary/[0.01]">
                            <span className="text-[8.5px] font-mono text-primary uppercase tracking-wider font-bold mb-1.5 block">Strategic Recommendations</span>
                            <div className="text-[10px] font-mono text-secondary leading-relaxed whitespace-pre-wrap">{review.recommendations}</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
