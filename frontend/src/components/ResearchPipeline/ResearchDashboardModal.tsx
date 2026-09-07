import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useResearchStore, type ResearchSectionState } from "@/stores/researchStore";
import config from "../../config";

export function ResearchDashboardModal() {
  const {
    isOpen,
    setOpen,
    activeTaskId,
    setActiveTaskId,
    taskState,
    setTaskState,
    sections,
    setSections,
    sources,
    setSources,
    claims,
    setClaims,
    contradictions,
    setContradictions,
    independence,
    setIndependence,
    network,
    setNetwork,
    devilsAdvocate,
    setDevilsAdvocate,
    decision,
    setDecision,
    actionPlan,
    setActionPlan,
    humanReviews,
    setHumanReviews,
    progressMessage,
    setProgressMessage,
  } = useResearchStore();

  // Setup options
  const [topic, setTopic] = useState("");
  const [depth, setDepth] = useState("deep");
  const [lengthTarget, setLengthTarget] = useState("20_pages");
  const [scope, setScope] = useState("web_local");
  const [template, setTemplate] = useState("research_report");
  const [format, setFormat] = useState("Markdown");
  const [researchMode, setResearchMode] = useState("balanced");
  const [targetAudience, setTargetAudience] = useState("researcher");
  const [humanReviewEnabled, setHumanReviewEnabled] = useState(false);

  // Tab controls
  const [activeTab, setActiveTab] = useState<string>("setup");
  const [editedSections, setEditedSections] = useState<ResearchSectionState[]>([]);
  const [regenInstructions, setRegenInstructions] = useState<Record<number, string>>({});
  const [reviewNotes, setReviewNotes] = useState<Record<number, string>>({});

  // WS or API Polling loop when task is running/queued
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;

    const fetchAllData = async () => {
      if (!activeTaskId) return;
      try {
        const headers: Record<string, string> = {};
        if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

        const urlParams = `${config.backendUrl}/api/v1/research/${activeTaskId}`;
        const resTask = await fetch(urlParams, { headers });
        const dataTask = await resTask.json();
        
        if (dataTask.task) {
          setTaskState(dataTask.task);
          setSections(dataTask.sections || []);
          setSources(dataTask.sources || []);
          
          if (dataTask.task.stage === "awaiting_outline_approval") {
            setEditedSections(dataTask.sections || []);
          }
        }

        // Fetch Claims
        const resClaims = await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/claims`, { headers });
        if (resClaims.ok) setClaims(await resClaims.json());

        // Fetch Contradictions
        const resContra = await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/contradictions`, { headers });
        if (resContra.ok) setContradictions(await resContra.json());

        // Fetch Independence
        const resInd = await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/independence`, { headers });
        if (resInd.ok) setIndependence(await resInd.json());

        // Fetch Network
        const resNet = await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/source-network`, { headers });
        if (resNet.ok) setNetwork(await resNet.json());

        // Fetch DA
        const resDA = await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/devils-advocate`, { headers });
        if (resDA.ok) setDevilsAdvocate(await resDA.json());

        // Fetch Decision
        const resDec = await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/decision`, { headers });
        if (resDec.ok) setDecision(await resDec.json());

        // Fetch Action Plan
        const resPlan = await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/action-plan`, { headers });
        if (resPlan.ok) setActionPlan(await resPlan.json());

        // Fetch Human Reviews
        const resHR = await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/human-review`, { headers });
        if (resHR.ok) setHumanReviews(await resHR.json());

      } catch (err) {
        console.error("Dashboard poll failed", err);
      }
    };

    if (activeTaskId) {
      fetchAllData();
      interval = setInterval(fetchAllData, 3000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeTaskId, setTaskState, setSections, setSources, setClaims, setContradictions, setIndependence, setNetwork, setDevilsAdvocate, setDecision, setActionPlan, setHumanReviews]);

  // If a task is active, jump from setup tab
  useEffect(() => {
    if (taskState && activeTab === "setup") {
      setActiveTab("outline");
    }
  }, [taskState, activeTab]);

  const handleStart = async () => {
    if (!topic.trim()) return;
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

      const res = await fetch(`${config.backendUrl}/api/v1/research`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          topic,
          depth,
          length_target: lengthTarget,
          scope,
          template,
          format,
          research_mode: researchMode,
          target_audience: targetAudience,
          human_review_enabled: humanReviewEnabled ? 1 : 0
        }),
      });
      const data = await res.json();
      if (data.task_id) {
        setActiveTaskId(data.task_id);
        setTaskState({
          id: data.task_id,
          topic,
          status: "queued",
          stage: "planning",
          depth,
          length_target: lengthTarget,
          progress_percent: 0,
          estimated_completion_time: null,
          output_path: null,
          error_message: null,
          research_mode: researchMode,
          target_audience: targetAudience,
          human_review_enabled: humanReviewEnabled ? 1 : 0
        });
        setActiveTab("outline");
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleApproveOutline = async () => {
    if (!activeTaskId) return;
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

      await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/outline/approve`, {
        method: "POST",
        headers,
        body: JSON.stringify({ modified_sections: editedSections }),
      });
      setProgressMessage("Outline approved. Research gathering initiated.");
    } catch (err) {
      console.error(err);
    }
  };

  const handleRegenSection = async (sectionId: number) => {
    if (!activeTaskId) return;
    const inst = regenInstructions[sectionId] || "Elaborate more on this section.";
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

      const res = await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/sections/${sectionId}/regenerate`, {
        method: "POST",
        headers,
        body: JSON.stringify({ instructions: inst }),
      });
      const data = await res.json();
      if (data.success) {
        setSections(sections.map(s => s.id === sectionId ? { ...s, validated_content: data.validated_content } : s));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleHumanReview = async (reviewId: number, decision: "approved" | "rejected" | "flagged") => {
    if (!activeTaskId) return;
    const notes = reviewNotes[reviewId] || "";
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

      await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/human-review/${reviewId}`, {
        method: "POST",
        headers,
        body: JSON.stringify({ decision, notes }),
      });
      setHumanReviews(humanReviews.map(r => r.id === reviewId ? { ...r, status: decision } : r));
    } catch (err) {
      console.error(err);
    }
  };

  const handleExport = async (targetFormat: string) => {
    if (!activeTaskId) return;
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;

      const res = await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/delivery`, {
        method: "POST",
        headers,
        body: JSON.stringify({ format: targetFormat, template }),
      });
      const data = await res.json();
      if (data.file_location) {
        alert(`Export completed!\nFile Location: ${data.file_location}\nReproducibility package created inside package directory.`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#050810]/95 p-4 overflow-y-auto font-sans">
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.97 }}
          className="hud-panel w-full max-w-6xl border border-primary/20 relative flex flex-col h-[90vh] rounded-lg overflow-hidden bg-[#0a0d16]"
          style={{ boxShadow: "0 0 50px rgba(76, 215, 246, 0.12)" }}
        >
          {/* Top Header */}
          <div className="flex justify-between items-center px-6 py-4 border-b border-primary/10 bg-[#0c101c] shrink-0">
            <div className="flex items-center gap-3">
              <span className="w-2.5 h-2.5 rounded-full bg-primary animate-pulse" />
              <h2 className="text-sm font-mono tracking-widest text-[#4cd7f6] uppercase">Decision Intelligence HUD v2.0</h2>
              {progressMessage && (
                <span className="text-[11px] font-mono text-outline px-2 py-0.5 border border-primary/20 bg-primary/5 rounded truncate max-w-xs">
                  {progressMessage}
                </span>
              )}
            </div>
            <button 
              onClick={() => setOpen(false)}
              className="text-outline-variant hover:text-primary transition-colors text-xs font-mono cursor-pointer border border-primary/20 rounded px-2.5 py-1 bg-primary/5"
            >
              [✕ CLOSE]
            </button>
          </div>

          {/* Core HUD Body */}
          <div className="flex flex-1 overflow-hidden">
            
            {/* Sidebar Navigation */}
            <div className="w-48 bg-[#070b12] border-r border-primary/10 flex flex-col shrink-0">
              <div className="p-3 text-[10px] text-outline font-mono border-b border-primary/10 uppercase tracking-wider">
                Control Center
              </div>
              <div className="flex-1 flex flex-col p-2 gap-1 overflow-y-auto">
                <button
                  onClick={() => setActiveTab("setup")}
                  className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-all ${
                    activeTab === "setup" ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-outline hover:bg-surface-container hover:text-primary"
                  }`}
                >
                  1. SETUP & BUDGET
                </button>
                <button
                  disabled={!taskState}
                  onClick={() => setActiveTab("outline")}
                  className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-all disabled:opacity-40 disabled:hover:bg-transparent ${
                    activeTab === "outline" ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-outline hover:bg-surface-container hover:text-primary"
                  }`}
                >
                  2. OUTLINE
                </button>
                <button
                  disabled={!taskState}
                  onClick={() => setActiveTab("claims")}
                  className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-all disabled:opacity-40 disabled:hover:bg-transparent ${
                    activeTab === "claims" ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-outline hover:bg-surface-container hover:text-primary"
                  }`}
                >
                  3. CLAIMS VAULT
                </button>
                <button
                  disabled={!taskState}
                  onClick={() => setActiveTab("contradictions")}
                  className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-all disabled:opacity-40 disabled:hover:bg-transparent ${
                    activeTab === "contradictions" ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-outline hover:bg-surface-container hover:text-primary"
                  }`}
                >
                  4. CONTRADICTIONS
                </button>
                <button
                  disabled={!taskState}
                  onClick={() => setActiveTab("sources")}
                  className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-all disabled:opacity-40 disabled:hover:bg-transparent ${
                    activeTab === "sources" ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-outline hover:bg-surface-container hover:text-primary"
                  }`}
                >
                  5. SOURCE FILES
                </button>
                <button
                  disabled={!taskState}
                  onClick={() => setActiveTab("network")}
                  className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-all disabled:opacity-40 disabled:hover:bg-transparent ${
                    activeTab === "network" ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-outline hover:bg-surface-container hover:text-primary"
                  }`}
                >
                  6. NETWORK GRAPH
                </button>
                <button
                  disabled={!taskState}
                  onClick={() => setActiveTab("advocate")}
                  className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-all disabled:opacity-40 disabled:hover:bg-transparent ${
                    activeTab === "advocate" ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-outline hover:bg-surface-container hover:text-primary"
                  }`}
                >
                  7. SKEPTIC AUDIT
                </button>
                <button
                  disabled={!taskState}
                  onClick={() => setActiveTab("decision")}
                  className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-all disabled:opacity-40 disabled:hover:bg-transparent ${
                    activeTab === "decision" ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-outline hover:bg-surface-container hover:text-primary"
                  }`}
                >
                  8. DECISION BRIEF
                </button>
                <button
                  disabled={!taskState}
                  onClick={() => setActiveTab("action")}
                  className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-all disabled:opacity-40 disabled:hover:bg-transparent ${
                    activeTab === "action" ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-outline hover:bg-surface-container hover:text-primary"
                  }`}
                >
                  9. ACTION ENGINE
                </button>
                <button
                  disabled={!taskState}
                  onClick={() => setActiveTab("reviews")}
                  className={`w-full text-left px-3 py-2 rounded text-xs font-mono transition-all disabled:opacity-40 disabled:hover:bg-transparent relative ${
                    activeTab === "reviews" ? "bg-primary/10 text-primary border-l-2 border-primary" : "text-outline hover:bg-surface-container hover:text-primary"
                  }`}
                >
                  10. HUMAN REVIEW
                  {humanReviews.filter(r => r.status === "pending").length > 0 && (
                    <span className="absolute right-2 top-2.5 w-2 h-2 rounded-full bg-[#ef4444]" />
                  )}
                </button>
              </div>
              
              {/* Task Details panel at sidebar bottom */}
              {taskState && (
                <div className="p-3 border-t border-primary/10 bg-[#080c14] shrink-0">
                  <div className="text-[10px] text-outline font-mono uppercase">Task HUD Status</div>
                  <div className="text-xs text-primary font-bold truncate mt-0.5">{taskState.topic}</div>
                  <div className="w-full bg-[#111827] h-1.5 rounded-sm overflow-hidden mt-2">
                    <div className="bg-primary h-full transition-all duration-300" style={{ width: `${taskState.progress_percent}%` }} />
                  </div>
                  <div className="text-[8px] text-outline font-mono mt-1 flex justify-between">
                    <span>{taskState.progress_percent.toFixed(0)}% Done</span>
                    <span className="uppercase text-primary">{taskState.stage.replace(/_/g, " ")}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Dashboard Content Panel */}
            <div className="flex-1 bg-[#090b11] p-6 overflow-y-auto flex flex-col">
              
              {/* SETUP TAB */}
              {activeTab === "setup" && (
                <div className="flex flex-col gap-6">
                  <div>
                    <h3 className="text-[#4cd7f6] text-sm font-mono tracking-wider mb-1 uppercase">1. Engine Setup & Budget Control</h3>
                    <p className="text-xs text-outline leading-relaxed font-sans">Configure your research objective, select computational constraints, framing metrics, and activate decision parameters.</p>
                  </div>
                  
                  <div className="grid grid-cols-1 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] text-outline font-mono uppercase">Topic or Research Objective</label>
                      <input
                        type="text"
                        value={topic}
                        onChange={(e) => setTopic(e.target.value)}
                        placeholder="e.g., Deep dive analysis of OpenAI GPT-5 architecture, performance, and exits..."
                        className="w-full bg-[#111625] border border-primary/20 rounded px-3 py-2.5 text-xs text-primary focus:outline-none focus:border-primary/50"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] text-outline font-mono uppercase">Computational Mode</label>
                      <select 
                        value={researchMode} 
                        onChange={(e) => setResearchMode(e.target.value)}
                        className="bg-[#111625] border border-primary/20 rounded p-2 text-xs text-secondary focus:outline-none"
                      >
                        <option value="fast">Fast (Cheap, 5 searches/sec, 10k tokens)</option>
                        <option value="balanced">Balanced (Standard, 10 searches/sec, 25k tokens)</option>
                        <option value="thorough">Thorough (Detailed, 20 searches/sec, 60k tokens)</option>
                        <option value="maximum">Maximum Accuracy (Deep, 40 searches/sec, 120k tokens)</option>
                      </select>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] text-outline font-mono uppercase">Target Audience Framing</label>
                      <select 
                        value={targetAudience} 
                        onChange={(e) => setTargetAudience(e.target.value)}
                        className="bg-[#111625] border border-primary/20 rounded p-2 text-xs text-secondary focus:outline-none"
                      >
                        <option value="researcher">Researcher (Scientific / Detail Precision)</option>
                        <option value="investor">Investor (ROI, Runway, exit potentials)</option>
                        <option value="founder">Founder (Strategic pivots, partnership values)</option>
                        <option value="recruiter">Recruiter (Talent signals, candidate red flags)</option>
                        <option value="manager">Manager (Operational risk, resource timelines)</option>
                      </select>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] text-outline font-mono uppercase">Depth Outline</label>
                      <select 
                        value={depth} 
                        onChange={(e) => setDepth(e.target.value)}
                        className="bg-[#111625] border border-primary/20 rounded p-2 text-xs text-secondary focus:outline-none"
                      >
                        <option value="quick">Quick Research</option>
                        <option value="deep">Deep Research (Standard)</option>
                        <option value="comprehensive">Comprehensive Outline</option>
                        <option value="academic">Academic Paper Structure</option>
                      </select>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] text-outline font-mono uppercase">Target Length</label>
                      <select 
                        value={lengthTarget} 
                        onChange={(e) => setLengthTarget(e.target.value)}
                        className="bg-[#111625] border border-primary/20 rounded p-2 text-xs text-secondary focus:outline-none"
                      >
                        <option value="5_pages">5 Pages Brief</option>
                        <option value="10_pages">10 Pages Standard</option>
                        <option value="20_pages">20 Pages Deep</option>
                        <option value="30_pages">30+ Pages Comprehensive</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] text-outline font-mono uppercase">Knowledge Scope</label>
                      <select 
                        value={scope} 
                        onChange={(e) => setScope(e.target.value)}
                        className="bg-[#111625] border border-primary/20 rounded p-2 text-xs text-secondary focus:outline-none"
                      >
                        <option value="web_only">Web Scrapers Only</option>
                        <option value="local_only">Workspace Repository Only</option>
                        <option value="web_local">Hybrid (Web + Local Workspace Files)</option>
                      </select>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] text-outline font-mono uppercase">Output Template</label>
                      <select 
                        value={template} 
                        onChange={(e) => setTemplate(e.target.value)}
                        className="bg-[#111625] border border-primary/20 rounded p-2 text-xs text-secondary focus:outline-none"
                      >
                        <option value="research_report">Executive Report</option>
                        <option value="whitepaper">Whitepaper Document</option>
                        <option value="academic_paper">Scientific Academic Paper</option>
                        <option value="business_report">Prioritized Business Review</option>
                      </select>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-[9px] text-outline font-mono uppercase">Deliverable Format</label>
                      <select 
                        value={format} 
                        onChange={(e) => setFormat(e.target.value)}
                        className="bg-[#111625] border border-primary/20 rounded p-2 text-xs text-secondary focus:outline-none"
                      >
                        <option value="Markdown">Markdown</option>
                        <option value="HTML">HTML Style Report</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 border border-primary/10 rounded p-4 bg-primary/5">
                    <input 
                      type="checkbox"
                      id="human_review_cb"
                      checked={humanReviewEnabled}
                      onChange={(e) => setHumanReviewEnabled(e.target.checked)}
                      className="cursor-pointer accent-primary"
                    />
                    <div>
                      <label htmlFor="human_review_cb" className="text-xs text-primary font-bold cursor-pointer font-mono">ACTIVATE HUMAN EVIDENCE REVIEW GATE</label>
                      <div className="text-[10px] text-outline mt-0.5">When checked, weak claims and hypotheses are queued for manual user review before section drafting begins.</div>
                    </div>
                  </div>

                  <button
                    onClick={handleStart}
                    className="mt-2 py-3 border border-primary text-primary font-mono tracking-widest text-xs hover:bg-primary/10 transition-colors rounded cursor-pointer"
                  >
                    DEPLOY 11-STAGE DECISION PIPELINE
                  </button>
                </div>
              )}

              {/* OUTLINE TAB */}
              {activeTab === "outline" && (
                <div className="flex flex-col gap-4 flex-1">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="text-[#4cd7f6] text-sm font-mono tracking-wider uppercase">2. Document Outline & Section Approval</h3>
                      <div className="text-[10px] text-outline mt-0.5">Approve, edit or override section outlines. Draft validation edit-loops compile sections dynamically.</div>
                    </div>
                    {taskState?.stage === "awaiting_outline_approval" && (
                      <button
                        onClick={handleApproveOutline}
                        className="px-4 py-1.5 border border-warning text-warning hover:bg-warning/10 font-mono text-xs transition-colors rounded"
                      >
                        APPROVE OUTLINE & INITIATE PIPELINE
                      </button>
                    )}
                  </div>

                  <div className="flex-1 flex flex-col gap-3 overflow-y-auto pr-1" style={{ scrollbarWidth: "thin" }}>
                    {sections.map((sec, idx) => (
                      <div key={sec.id} className="border border-primary/10 p-4 bg-[#0e1220]/50 rounded-lg flex flex-col gap-3">
                        <div className="flex justify-between items-center">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-outline">#{idx + 1}</span>
                            {taskState?.stage === "awaiting_outline_approval" ? (
                              <input
                                type="text"
                                value={editedSections[idx]?.title || ""}
                                onChange={(e) => {
                                  const updated = [...editedSections];
                                  if (updated[idx]) {
                                    updated[idx].title = e.target.value;
                                    setEditedSections(updated);
                                  }
                                }}
                                className="bg-[#161a29] border border-primary/20 rounded px-2 py-1 text-xs text-primary font-mono focus:outline-none"
                              />
                            ) : (
                              <span className="text-xs font-bold text-primary font-mono">{sec.title}</span>
                            )}
                          </div>
                          <span className={`text-[8px] font-mono uppercase px-2 py-0.5 border rounded ${
                            sec.status === "completed" ? "border-success/30 text-success bg-success/5" : "border-outline-variant/30 text-outline"
                          }`}>
                            {sec.status}
                          </span>
                        </div>
                        
                        <div className="text-[11px] text-on-surface-variant font-mono leading-relaxed bg-[#0b0e18] p-3 rounded border border-primary/5 whitespace-pre-wrap">
                          {sec.validated_content || sec.content || "Draft section content is compiling..."}
                        </div>

                        {taskState?.stage === "awaiting_draft_approval" && (
                          <div className="flex gap-2 items-center">
                            <input
                              type="text"
                              placeholder="Regen override instructions (e.g. Include exit valuations and competitor list)..."
                              value={regenInstructions[sec.id] || ""}
                              onChange={(e) => setRegenInstructions({ ...regenInstructions, [sec.id]: e.target.value })}
                              className="flex-1 bg-[#121625] border border-primary/20 rounded px-3 py-1.5 text-[10px] text-primary focus:outline-none"
                            />
                            <button
                              onClick={() => handleRegenSection(sec.id)}
                              className="px-3 py-1.5 border border-primary/40 hover:bg-primary/10 text-primary font-mono text-[9px] transition-colors rounded"
                            >
                              REGEN SECTION
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* CLAIMS VAULT TAB */}
              {activeTab === "claims" && (
                <div className="flex flex-col gap-4 flex-1">
                  <div>
                    <h3 className="text-[#4cd7f6] text-sm font-mono tracking-wider uppercase">3. Claim Verification & Forensic Scoreboard</h3>
                    <div className="text-[10px] text-outline mt-0.5">Every factual claim extracted undergoes multi-layered validation, citation audit and confidence calculation.</div>
                  </div>

                  <div className="flex-1 overflow-x-auto">
                    <table className="w-full text-left border-collapse border border-primary/10 bg-[#0e1220]/20 rounded-lg overflow-hidden">
                      <thead>
                        <tr className="bg-[#0b0e18] text-[#4cd7f6] text-[10px] uppercase font-mono border-b border-primary/10">
                          <th className="p-3">Claim Text</th>
                          <th className="p-3">Verification Status</th>
                          <th className="p-3">Confidence</th>
                          <th className="p-3">Source URL</th>
                          <th className="p-3">Quality Score</th>
                        </tr>
                      </thead>
                      <tbody className="text-xs text-outline font-sans">
                        {claims.map((cl) => {
                          let colorClass = "border-outline-variant/30 text-outline";
                          if (cl.verification_status === "Verified") colorClass = "border-success/30 text-[#10b981] bg-[#10b981]/5";
                          else if (cl.verification_status === "Partially Verified") colorClass = "border-[#f59e0b]/30 text-[#f59e0b] bg-[#f59e0b]/5";
                          else if (cl.verification_status === "Contradicted") colorClass = "border-[#ef4444]/30 text-[#ef4444] bg-[#ef4444]/5";
                          else if (cl.verification_status === "Hypothesis") colorClass = "border-[#8b5cf6]/30 text-[#8b5cf6] bg-[#8b5cf6]/5";
                          
                          return (
                            <tr key={cl.id} className="border-b border-primary/5 hover:bg-[#121625]/20 transition-all">
                              <td className="p-3 font-medium text-primary max-w-sm">{cl.claim_text}</td>
                              <td className="p-3">
                                <span className={`px-2 py-0.5 border rounded text-[9px] font-mono font-bold ${colorClass}`}>
                                  {cl.verification_status}
                                </span>
                              </td>
                              <td className="p-3 font-mono font-bold text-primary">{(cl.confidence_score * 100).toFixed(0)}%</td>
                              <td className="p-3 max-w-xs truncate text-primary/60 font-mono"><a href={cl.source_url} target="_blank" rel="noreferrer" className="hover:underline">{cl.source_url}</a></td>
                              <td className="p-3 font-mono">{cl.source_quality_score.toFixed(1)}/10</td>
                            </tr>
                          );
                        })}
                        {claims.length === 0 && (
                          <tr>
                            <td colSpan={5} className="p-6 text-center text-outline-variant font-mono">No claims extracted yet. Status is collecting...</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* CONTRADICTIONS TAB */}
              {activeTab === "contradictions" && (
                <div className="flex flex-col gap-4 flex-1">
                  <div>
                    <h3 className="text-[#4cd7f6] text-sm font-mono tracking-wider uppercase">4. Contradiction & Numerical Conflict Audit</h3>
                    <div className="text-[10px] text-outline mt-0.5">Identifies semantic deviations or numeric values discrepancies &gt; 20% across source nodes.</div>
                  </div>

                  <div className="flex-1 flex flex-col gap-3 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
                    {contradictions.map((co) => (
                      <div key={co.id} className="border border-[#ef4444]/20 p-4 bg-[#ef4444]/5 rounded-lg flex flex-col gap-3">
                        <div className="flex justify-between items-center border-b border-[#ef4444]/10 pb-2">
                          <span className="text-xs font-mono font-bold text-[#ef4444] uppercase">Contradiction Detected // Category: {co.field_type.toUpperCase()}</span>
                          <span className="text-[9px] font-mono text-outline">Penalty applied: -20% Confidence</span>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-sans">
                          <div className="p-3 bg-[#0d0f17] border border-primary/5 rounded">
                            <span className="text-[9px] font-mono text-outline block mb-1">Claim A (ID: {co.claim_a_id})</span>
                            <span className="text-primary">{claims.find(cl => cl.id === co.claim_a_id)?.claim_text || "Source Claim"}</span>
                            <a href={co.source_a_url} target="_blank" rel="noreferrer" className="text-primary/40 block mt-2 font-mono text-[9px] truncate hover:underline">{co.source_a_url}</a>
                          </div>
                          <div className="p-3 bg-[#0d0f17] border border-primary/5 rounded">
                            <span className="text-[9px] font-mono text-outline block mb-1">Claim B (ID: {co.claim_b_id})</span>
                            <span className="text-primary">{claims.find(cl => cl.id === co.claim_b_id)?.claim_text || "Source Claim"}</span>
                            <a href={co.source_b_url} target="_blank" rel="noreferrer" className="text-primary/40 block mt-2 font-mono text-[9px] truncate hover:underline">{co.source_b_url}</a>
                          </div>
                        </div>
                        <div className="p-3 bg-[#111422] rounded border border-[#ef4444]/15">
                          <div className="text-[9px] font-mono text-[#f59e0b] uppercase font-bold mb-1">Engine Possible Explanations:</div>
                          <ul className="list-disc pl-4 text-xs text-outline leading-relaxed flex flex-col gap-1">
                            {co.possible_explanations.map((exp, idx) => (
                              <li key={idx}>{exp}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    ))}
                    {contradictions.length === 0 && (
                      <div className="p-10 text-center text-outline-variant font-mono border border-primary/5 rounded bg-[#0e1220]/10">
                        No contradictions or numeric conflicts detected across sources.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* SOURCES TAB */}
              {activeTab === "sources" && (
                <div className="flex flex-col gap-4 flex-1">
                  <div>
                    <h3 className="text-[#4cd7f6] text-sm font-mono tracking-wider uppercase">5. Evidence Vault & Credibility Index</h3>
                    <div className="text-[10px] text-outline mt-0.5">Permanent archive logs of all raw snapshots and credibility analysis.</div>
                  </div>

                  <div className="flex-1 flex flex-col gap-3 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
                    {sources.map((src) => (
                      <div key={src.id} className="border border-primary/10 p-4 bg-[#0e1220]/45 rounded-lg flex flex-col gap-2 font-sans">
                        <div className="flex justify-between items-start border-b border-primary/5 pb-2">
                          <div>
                            <h4 className="text-xs font-bold text-primary font-mono">{src.title || "Untitled source"}</h4>
                            <a href={src.url} target="_blank" rel="noreferrer" className="text-[9px] text-[#4cd7f6] font-mono hover:underline block mt-0.5 truncate">{src.url}</a>
                          </div>
                          <div className="text-right flex gap-3 items-center">
                            <span className="px-2 py-0.5 bg-primary/5 text-primary text-[8px] font-mono border border-primary/20 uppercase rounded">{src.source_type}</span>
                            <span className="text-xs font-mono font-bold text-primary">{src.credibility_score * 10} / 10</span>
                          </div>
                        </div>
                        <div className="text-[10px] text-outline leading-relaxed italic bg-[#080c14] p-3 border border-primary/5 rounded font-mono">
                          {src.snippet || "No snippet snapshot cached."}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* NETWORK TAB */}
              {activeTab === "network" && (
                <div className="flex flex-col gap-4 flex-1">
                  <div>
                    <h3 className="text-[#4cd7f6] text-sm font-mono tracking-wider uppercase">6. Source Independence & Citation Graph</h3>
                    <div className="text-[10px] text-outline mt-0.5">TF-IDF analysis calculates document similarity metrics to prevent echo-chambers and syndication.</div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
                    {/* Independence Index Table */}
                    <div className="border border-primary/10 rounded p-4 bg-[#0e1220]/10 flex flex-col">
                      <span className="text-xs font-mono text-[#4cd7f6] uppercase border-b border-primary/5 pb-2 block mb-3 font-bold">Source Independence Index</span>
                      <div className="flex-1 overflow-x-auto">
                        <table className="w-full text-left text-xs font-mono">
                          <thead>
                            <tr className="text-outline uppercase text-[9px] border-b border-primary/5">
                              <th className="pb-2">URL</th>
                              <th className="pb-2">Indep. Score</th>
                              <th className="pb-2">Classification</th>
                            </tr>
                          </thead>
                          <tbody>
                            {independence.map((ind) => (
                              <tr key={ind.id} className="border-b border-primary/5">
                                <td className="py-2 pr-2 max-w-[120px] truncate text-primary/80"><a href={ind.url} target="_blank" rel="noreferrer" className="hover:underline">{ind.url}</a></td>
                                <td className="py-2 text-primary font-bold">{ind.independence_score.toFixed(2)}</td>
                                <td className="py-2">
                                  <span className={`px-1.5 py-0.5 text-[8px] rounded uppercase font-bold border ${
                                    ind.duplication_type === "original" ? "border-success/30 text-success bg-success/5" :
                                    ind.duplication_type === "derivative" ? "border-warning/30 text-warning bg-warning/5" : "border-[#ef4444]/30 text-[#ef4444] bg-[#ef4444]/5"
                                  }`}>
                                    {ind.duplication_type}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Network Nodes Graph List */}
                    <div className="border border-primary/10 rounded p-4 bg-[#0e1220]/10 flex flex-col">
                      <span className="text-xs font-mono text-[#4cd7f6] uppercase border-b border-primary/5 pb-2 block mb-3 font-bold">Citation Nodes Summary</span>
                      <div className="flex-1 overflow-x-auto">
                        <table className="w-full text-left text-xs font-mono">
                          <thead>
                            <tr className="text-outline uppercase text-[9px] border-b border-primary/5">
                              <th className="pb-2">URL</th>
                              <th className="pb-2">Claims</th>
                              <th className="pb-2">Chain Depth</th>
                              <th className="pb-2">Echo Chamber Risk</th>
                            </tr>
                          </thead>
                          <tbody>
                            {network.map((n) => (
                              <tr key={n.id} className="border-b border-primary/5">
                                <td className="py-2 pr-2 max-w-[120px] truncate text-primary/80"><a href={n.url} target="_blank" rel="noreferrer" className="hover:underline">{n.url}</a></td>
                                <td className="py-2 text-primary">{n.claim_count}</td>
                                <td className="py-2 text-primary">{n.citation_chain_depth}</td>
                                <td className="py-2 font-bold text-[#ef4444]">{(n.echo_chamber_risk_score * 100).toFixed(0)}%</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ADVOCATE TAB */}
              {activeTab === "advocate" && (
                <div className="flex flex-col gap-4 flex-1">
                  <div>
                    <h3 className="text-[#4cd7f6] text-sm font-mono tracking-wider uppercase">7. Skeptic Audit & Devils Advocate</h3>
                    <div className="text-[10px] text-outline mt-0.5">Audits hidden assumptions, outlines counter-arguments, and explores alternate interpretations.</div>
                  </div>

                  {devilsAdvocate ? (
                    <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
                      
                      <div className="border border-primary/10 rounded p-4 bg-[#0e1220]/20 flex flex-col gap-3 font-sans">
                        <span className="text-xs font-mono text-[#ef4444] border-b border-[#ef4444]/10 pb-2 block font-bold uppercase">Counter Arguments</span>
                        <ul className="list-disc pl-4 text-xs text-outline leading-relaxed flex flex-col gap-2">
                          {devilsAdvocate.counter_arguments.map((arg, idx) => (
                            <li key={idx}>{arg}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="border border-primary/10 rounded p-4 bg-[#0e1220]/20 flex flex-col gap-3 font-sans">
                        <span className="text-xs font-mono text-warning border-b border-warning/10 pb-2 block font-bold uppercase">Alternative Interpretations</span>
                        <ul className="list-disc pl-4 text-xs text-outline leading-relaxed flex flex-col gap-2">
                          {devilsAdvocate.alternative_interpretations.map((alt, idx) => (
                            <li key={idx}>{alt}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="border border-primary/10 rounded p-4 bg-[#0e1220]/20 flex flex-col gap-3 font-sans">
                        <span className="text-xs font-mono text-[#8b5cf6] border-b border-[#8b5cf6]/10 pb-2 block font-bold uppercase">Confidence Risks</span>
                        <ul className="list-disc pl-4 text-xs text-outline leading-relaxed flex flex-col gap-2">
                          {devilsAdvocate.confidence_risks.map((risk, idx) => (
                            <li key={idx}>{risk}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="border border-primary/10 rounded p-4 bg-[#ef4444]/10 flex flex-col gap-3 font-sans">
                        <span className="text-xs font-mono text-[#ef4444] border-b border-[#ef4444]/15 pb-2 block font-bold uppercase">Why We Might Be Wrong</span>
                        <ul className="list-disc pl-4 text-xs text-[#ef4444] leading-relaxed flex flex-col gap-2">
                          {devilsAdvocate.why_wrong.map((ww, idx) => (
                            <li key={idx}>{ww}</li>
                          ))}
                        </ul>
                      </div>

                    </div>
                  ) : (
                    <div className="p-10 text-center text-outline-variant font-mono border border-primary/5 rounded bg-[#0e1220]/10 flex-1 flex items-center justify-center">
                      Devil's Advocate Audit is pending. Compiles after section drafting.
                    </div>
                  )}
                </div>
              )}

              {/* DECISION BRIEF TAB */}
              {activeTab === "decision" && (
                <div className="flex flex-col gap-4 flex-1">
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="text-[#4cd7f6] text-sm font-mono tracking-wider uppercase">8. Decision Intelligence Brief</h3>
                      <div className="text-[10px] text-outline mt-0.5">Audience-framed decision briefs highlight key findings and red flags.</div>
                    </div>
                    {taskState?.status === "completed" && (
                      <div className="flex gap-2">
                        {["PDF", "DOCX", "HTML"].map((fmt) => (
                          <button
                            key={fmt}
                            onClick={() => handleExport(fmt)}
                            className="px-2.5 py-1 border border-primary text-primary font-mono text-[10px] hover:bg-primary/5 rounded transition-all"
                          >
                            EXPORT {fmt}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {decision ? (
                    <div className="flex-1 flex flex-col gap-5 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
                      
                      <div className="border border-primary/15 bg-primary/5 p-4 rounded-lg font-sans">
                        <span className="text-xs font-mono text-primary font-bold block mb-2 uppercase">Executive Decision Summary // Confidence: {(decision.confidence_level * 100).toFixed(0)}%</span>
                        <p className="text-xs text-outline leading-relaxed text-justify">{decision.decision_summary}</p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-sans">
                        <div className="border border-[#10b981]/20 p-4 bg-[#10b981]/5 rounded-lg flex flex-col gap-2">
                          <span className="text-xs font-mono text-[#10b981] font-bold uppercase border-b border-[#10b981]/10 pb-1.5 mb-1 block">Green Flags & Opportunities</span>
                          <ul className="list-disc pl-4 text-xs text-outline leading-relaxed flex flex-col gap-1.5">
                            {decision.green_flags.map((gf, idx) => (
                              <li key={idx}>{gf}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="border border-[#ef4444]/20 p-4 bg-[#ef4444]/5 rounded-lg flex flex-col gap-2">
                          <span className="text-xs font-mono text-[#ef4444] font-bold uppercase border-b border-[#ef4444]/10 pb-1.5 mb-1 block">Red Flags & Critical Risks</span>
                          <ul className="list-disc pl-4 text-xs text-[#ef4444] leading-relaxed flex flex-col gap-1.5">
                            {decision.red_flags.map((rf, idx) => (
                              <li key={idx}>{rf}</li>
                            ))}
                          </ul>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-sans">
                        <div className="border border-primary/10 p-4 bg-[#0e1220]/20 rounded-lg flex flex-col gap-2">
                          <span className="text-xs font-mono text-primary font-bold uppercase border-b border-primary/5 pb-1.5 mb-1 block">Key Findings Summary</span>
                          <ul className="list-disc pl-4 text-xs text-outline leading-relaxed flex flex-col gap-1.5">
                            {decision.key_findings.map((kf, idx) => (
                              <li key={idx}>{kf}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="border border-warning/20 p-4 bg-warning/5 rounded-lg flex flex-col gap-2">
                          <span className="text-xs font-mono text-warning font-bold uppercase border-b border-warning/10 pb-1.5 mb-1 block">Open Gaps & Gaps Register</span>
                          <ul className="list-disc pl-4 text-xs text-outline leading-relaxed flex flex-col gap-1.5">
                            {decision.open_questions.map((oq, idx) => (
                              <li key={idx}>{oq}</li>
                            ))}
                          </ul>
                        </div>
                      </div>

                    </div>
                  ) : (
                    <div className="p-10 text-center text-outline-variant font-mono border border-primary/5 rounded bg-[#0e1220]/10 flex-1 flex items-center justify-center">
                      Decision layer compilation is pending. Completes in stage 10.
                    </div>
                  )}
                </div>
              )}

              {/* ACTION ENGINE TAB */}
              {activeTab === "action" && (
                <div className="flex flex-col gap-4 flex-1">
                  <div>
                    <h3 className="text-[#4cd7f6] text-sm font-mono tracking-wider uppercase">9. Priority-Ranked Executable Action Plans</h3>
                    <div className="text-[10px] text-outline mt-0.5">Actions mapped from Verified evidence. Hypotheses dependencies are flagged Speculative.</div>
                  </div>

                  {actionPlan ? (
                    <div className="flex-1 flex flex-col gap-5 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
                      
                      <div className="border border-primary/10 rounded-lg overflow-hidden">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="bg-[#0b0e18] text-primary font-mono text-[9px] uppercase border-b border-primary/10">
                              <th className="p-3">Priority</th>
                              <th className="p-3">Action Step</th>
                              <th className="p-3">Category</th>
                              <th className="p-3">Impact / Effort</th>
                              <th className="p-3">Timeline</th>
                              <th className="p-3">Speculative</th>
                            </tr>
                          </thead>
                          <tbody>
                            {actionPlan.actions.map((act, idx) => (
                              <tr key={idx} className="border-b border-primary/5 font-sans">
                                <td className="p-3 font-mono font-bold text-[#f59e0b] text-sm">#{act.priority}</td>
                                <td className="p-3 text-primary">
                                  <div className="font-semibold">{act.action}</div>
                                  <div className="text-[10px] text-outline mt-0.5">{act.rationale}</div>
                                </td>
                                <td className="p-3 font-mono text-outline">{act.category}</td>
                                <td className="p-3 font-mono">
                                  <span className="text-primary">{act.estimated_impact}</span> / <span className="text-outline">{act.estimated_effort}</span>
                                </td>
                                <td className="p-3 font-mono text-outline">{act.timeline}</td>
                                <td className="p-3">
                                  {act.speculative ? (
                                    <span className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold border border-[#ef4444]/30 bg-[#ef4444]/5 text-[#ef4444] uppercase animate-pulse">
                                      ⚠️ SPECULATIVE
                                    </span>
                                  ) : (
                                    <span className="text-[10px] text-[#10b981] font-mono">Verified</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-sans">
                        <div className="p-4 border border-primary/10 bg-[#0e1220]/15 rounded-lg flex flex-col gap-2">
                          <span className="text-xs font-mono font-bold text-primary uppercase border-b border-primary/5 pb-1 block">Immediate Next Steps</span>
                          <ul className="list-decimal pl-4 text-xs text-outline leading-relaxed flex flex-col gap-1">
                            {actionPlan.next_steps.map((ns, idx) => (
                              <li key={idx}>{ns}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="p-4 border border-[#10b981]/20 bg-[#10b981]/5 rounded-lg flex flex-col gap-2">
                          <span className="text-xs font-mono font-bold text-[#10b981] uppercase border-b border-[#10b981]/15 pb-1 block">Quick Wins</span>
                          <ul className="list-disc pl-4 text-xs text-outline leading-relaxed flex flex-col gap-1">
                            {actionPlan.quick_wins.map((qw, idx) => (
                              <li key={idx}>{qw}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="p-4 border border-warning/20 bg-warning/5 rounded-lg flex flex-col gap-2">
                          <span className="text-xs font-mono font-bold text-warning uppercase border-b border-warning/15 pb-1 block">Long-Term Goals</span>
                          <ul className="list-disc pl-4 text-xs text-outline leading-relaxed flex flex-col gap-1">
                            {actionPlan.long_term_actions.map((lt, idx) => (
                              <li key={idx}>{lt}</li>
                            ))}
                          </ul>
                        </div>
                      </div>

                    </div>
                  ) : (
                    <div className="p-10 text-center text-outline-variant font-mono border border-primary/5 rounded bg-[#0e1220]/10 flex-1 flex items-center justify-center">
                      Action engine recommendations are pending. Generates in stage 11.
                    </div>
                  )}
                </div>
              )}

              {/* HUMAN REVIEW TAB */}
              {activeTab === "reviews" && (
                <div className="flex flex-col gap-4 flex-1">
                  <div>
                    <h3 className="text-[#4cd7f6] text-sm font-mono tracking-wider uppercase">10. Human-in-the-Loop Review Queue</h3>
                    <div className="text-[10px] text-outline mt-0.5">Suspends pipeline execution to allow manual verification, status overrides and custom annotation.</div>
                  </div>

                  <div className="flex-1 flex flex-col gap-4 overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
                    {humanReviews.map((item) => (
                      <div key={item.id} className={`border p-4 rounded-lg flex flex-col gap-3 font-sans transition-all ${
                        item.status === "pending" ? "border-warning/30 bg-[#f59e0b]/5" :
                        item.status === "approved" ? "border-[#10b981]/25 bg-[#10b981]/5" : "border-outline/20 bg-surface-container/20"
                      }`}>
                        <div className="flex justify-between items-center border-b border-primary/5 pb-2">
                          <span className="text-xs font-mono text-primary font-bold uppercase">Reason: {item.review_reason}</span>
                          <span className={`px-2 py-0.5 text-[8px] font-mono border rounded uppercase font-bold ${
                            item.status === "pending" ? "border-warning text-warning animate-pulse" :
                            item.status === "approved" ? "border-success text-success" : "border-outline text-outline"
                          }`}>{item.status}</span>
                        </div>
                        <div className="text-xs text-primary font-semibold bg-[#0a0d16] p-3 rounded border border-primary/5 font-mono">
                          {claims.find(c => c.id === item.claim_id)?.claim_text || "Source Claim"}
                        </div>
                        <div className="text-[11px] text-outline italic leading-relaxed pl-3 border-l-2 border-primary/20">
                          {item.snapshot_excerpt}
                        </div>
                        
                        {item.status === "pending" && (
                          <div className="flex flex-col gap-2 mt-2">
                            <input
                              type="text"
                              placeholder="Reviewer notes / annotations..."
                              value={reviewNotes[item.id] || ""}
                              onChange={(e) => setReviewNotes({ ...reviewNotes, [item.id]: e.target.value })}
                              className="bg-[#121624] border border-primary/20 rounded px-3 py-2 text-xs text-primary focus:outline-none"
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleHumanReview(item.id, "approved")}
                                className="px-4 py-1.5 bg-[#10b981]/20 hover:bg-[#10b981]/30 border border-[#10b981]/40 text-[#10b981] font-mono text-xs rounded transition-all cursor-pointer"
                              >
                                APPROVE & VERIFY
                              </button>
                              <button
                                onClick={() => handleHumanReview(item.id, "rejected")}
                                className="px-4 py-1.5 bg-[#ef4444]/20 hover:bg-[#ef4444]/30 border border-[#ef4444]/40 text-[#ef4444] font-mono text-xs rounded transition-all cursor-pointer"
                              >
                                REJECT & VOID
                              </button>
                              <button
                                onClick={() => handleHumanReview(item.id, "flagged")}
                                className="px-4 py-1.5 bg-[#8b5cf6]/20 hover:bg-[#8b5cf6]/30 border border-[#8b5cf6]/40 text-[#8b5cf6] font-mono text-xs rounded transition-all cursor-pointer"
                              >
                                FLAG TO TIMEOUT
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                    {humanReviews.length === 0 && (
                      <div className="p-10 text-center text-outline-variant font-mono border border-primary/5 rounded bg-[#0e1220]/10 flex-1 flex items-center justify-center">
                        Human review queue is currently empty. Enable Human Evidence review in setup.
                      </div>
                    )}
                  </div>
                </div>
              )}

            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
