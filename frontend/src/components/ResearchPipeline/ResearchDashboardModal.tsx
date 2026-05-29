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
    progressMessage,
  } = useResearchStore();

  // Scope configurations
  const [topic, setTopic] = useState("");
  const [depth, setDepth] = useState("deep");
  const [lengthTarget, setLengthTarget] = useState("20_pages");
  const [scope, setScope] = useState("web_local");
  const [template, setTemplate] = useState("research_report");
  const [format, setFormat] = useState("Markdown");
  
  // Section edit helper
  const [editedSections, setEditedSections] = useState<ResearchSectionState[]>([]);
  const [regenInstructions, setRegenInstructions] = useState<Record<number, string>>({});

  useEffect(() => {
    if (taskState?.stage === "awaiting_outline_approval") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEditedSections([...sections]);
    }
  }, [sections, taskState?.stage]);

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
        });
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
        // Update section content inline
        setSections(sections.map(s => s.id === sectionId ? { ...s, validated_content: data.validated_content } : s));
      }
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
        alert(`Export completed!\nFile Location: ${data.file_location}`);
      }
    } catch (err) {
      console.error(err);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#050810]/90 p-4 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="hud-panel w-full max-w-4xl border border-primary/30 relative flex flex-col max-h-[85vh] overflow-hidden"
          style={{ boxShadow: "0 0 35px rgba(76, 215, 246, 0.15)" }}
        >
          {/* Scanline Overlay */}
          <div className="absolute inset-0 scan-line-overlay pointer-events-none opacity-20" />

          {/* Modal Header */}
          <div className="flex justify-between items-center px-6 py-4 border-b border-primary/10 shrink-0">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-primary animate-pulse" />
              <h2 className="hud-label text-glow-cyan text-base">RESEARCH & SYNTHESIS CONTROL</h2>
            </div>
            <button 
              onClick={() => setOpen(false)}
              className="text-outline-variant hover:text-primary transition-colors text-sm font-mono cursor-pointer"
            >
              [✕ CLOSE]
            </button>
          </div>

          {/* Modal Body */}
          <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6" style={{ scrollbarWidth: "none" }}>
            
            {/* STAGE A: Configure New Job */}
            {!taskState && (
              <div className="flex flex-col gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-data-mono text-[10px] text-outline uppercase tracking-wider">Research Topic / Objective</label>
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g., Prepare a detailed research report on Quantum Computing architectures..."
                    className="w-full bg-surface border border-outline/25 rounded px-3 py-2 text-sm text-primary focus:outline-none focus:border-primary/50"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Depth */}
                  <div className="flex flex-col gap-1">
                    <label className="text-data-mono text-[9px] text-outline uppercase">Research Depth</label>
                    <select 
                      value={depth} 
                      onChange={(e) => setDepth(e.target.value)}
                      className="bg-surface border border-outline/20 rounded p-1.5 text-xs text-secondary focus:outline-none"
                    >
                      <option value="quick">Quick Research</option>
                      <option value="deep">Deep Research</option>
                      <option value="comprehensive">Comprehensive Research</option>
                      <option value="academic">Academic Research</option>
                    </select>
                  </div>

                  {/* Length */}
                  <div className="flex flex-col gap-1">
                    <label className="text-data-mono text-[9px] text-outline uppercase">Target Length</label>
                    <select 
                      value={lengthTarget} 
                      onChange={(e) => setLengthTarget(e.target.value)}
                      className="bg-surface border border-outline/20 rounded p-1.5 text-xs text-secondary focus:outline-none"
                    >
                      <option value="5_pages">5 Pages</option>
                      <option value="20_pages">20 Pages</option>
                      <option value="50_pages">50 Pages</option>
                      <option value="100_pages">100 Pages</option>
                    </select>
                  </div>

                  {/* Knowledge Scope */}
                  <div className="flex flex-col gap-1">
                    <label className="text-data-mono text-[9px] text-outline uppercase">Scope</label>
                    <select 
                      value={scope} 
                      onChange={(e) => setScope(e.target.value)}
                      className="bg-surface border border-outline/20 rounded p-1.5 text-xs text-secondary focus:outline-none"
                    >
                      <option value="web_only">Web Only</option>
                      <option value="local_only">Workspace Files Only</option>
                      <option value="web_local">Web + Workspace Files</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Template */}
                  <div className="flex flex-col gap-1">
                    <label className="text-data-mono text-[9px] text-outline uppercase">Template</label>
                    <select 
                      value={template} 
                      onChange={(e) => setTemplate(e.target.value)}
                      className="bg-surface border border-outline/20 rounded p-1.5 text-xs text-secondary focus:outline-none"
                    >
                      <option value="research_report">Research Report</option>
                      <option value="whitepaper">Whitepaper</option>
                      <option value="academic_paper">Academic Paper</option>
                      <option value="business_report">Business Report</option>
                    </select>
                  </div>

                  {/* Default Format */}
                  <div className="flex flex-col gap-1">
                    <label className="text-data-mono text-[9px] text-outline uppercase">Output Deliverable Format</label>
                    <select 
                      value={format} 
                      onChange={(e) => setFormat(e.target.value)}
                      className="bg-surface border border-outline/20 rounded p-1.5 text-xs text-secondary focus:outline-none"
                    >
                      <option value="Markdown">Markdown</option>
                      <option value="HTML">HTML</option>
                      <option value="PDF">PDF (ReportLab)</option>
                      <option value="DOCX">Microsoft Word (docx)</option>
                      <option value="PPTX">PowerPoint Presentation (pptx)</option>
                    </select>
                  </div>
                </div>

                <button
                  onClick={handleStart}
                  className="mt-4 py-2 border border-primary text-primary font-mono tracking-widest text-xs hover:bg-primary/10 transition-colors"
                >
                  LAUNCH RESEARCH INCEPTION PIPELINE
                </button>
              </div>
            )}

            {/* STAGE B: Task Progress / Running State */}
            {taskState && (
              <div className="flex flex-col gap-5">
                <div className="flex justify-between items-start border-b border-primary/5 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-primary font-space tracking-wide uppercase">{taskState.topic}</h3>
                    <div className="text-[9px] text-outline font-mono mt-1">ID: {taskState.id} // DEPTH: {taskState.depth.toUpperCase()}</div>
                  </div>
                  <div className="text-right">
                    <span className="hud-chip !text-[8px] !py-0.5 !px-2 uppercase font-bold !border-primary/35 !text-primary !bg-primary/5">
                      {taskState.stage.replace(/_/g, " ")}
                    </span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="flex flex-col gap-2">
                  <div className="flex justify-between text-[10px] text-outline font-mono">
                    <span>Progress: {taskState.progress_percent.toFixed(0)}%</span>
                    <span>{progressMessage}</span>
                  </div>
                  <div className="w-full h-1 bg-surface-container rounded-sm overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-primary to-secondary transition-all duration-500" 
                      style={{ width: `${taskState.progress_percent}%` }}
                    />
                  </div>
                </div>

                {/* Sub-Views based on Stage */}
                {taskState.stage === "awaiting_outline_approval" && (
                  <div className="border border-warning/35 bg-warning/5 rounded p-4 flex flex-col gap-4">
                    <div className="text-xs font-mono text-warning font-bold">OUTLINE APPROVAL REQUIRED:</div>
                    <div className="flex flex-col gap-2">
                      {editedSections.map((sec, idx) => (
                        <div key={idx} className="flex gap-2 items-center">
                          <span className="text-[10px] font-mono text-outline">{idx + 1}.</span>
                          <input
                            type="text"
                            value={sec.title}
                            onChange={(e) => {
                              const updated = [...editedSections];
                              updated[idx].title = e.target.value;
                              setEditedSections(updated);
                            }}
                            className="flex-1 bg-surface border border-outline/15 rounded px-2 py-1 text-xs text-primary focus:outline-none"
                          />
                        </div>
                      ))}
                    </div>
                    <button
                      onClick={handleApproveOutline}
                      className="py-1.5 border border-warning text-warning hover:bg-warning/10 font-mono text-xs transition-colors"
                    >
                      APPROVE OUTLINE & GENERATE REPORT
                    </button>
                  </div>
                )}

                {taskState.stage === "awaiting_draft_approval" && (
                  <div className="flex flex-col gap-4">
                    <div className="text-xs font-mono text-success font-bold">DRAFT VALIDATION & EDIT LOOP:</div>
                    <div className="flex flex-col gap-3 max-h-[30vh] overflow-y-auto" style={{ scrollbarWidth: "thin" }}>
                      {sections.map((sec) => (
                        <div key={sec.id} className="border border-outline/10 p-3 bg-surface-container/30 rounded flex flex-col gap-2">
                          <div className="flex justify-between items-center">
                            <span className="text-xs font-mono font-bold text-primary">{sec.title}</span>
                            <span className="text-[8px] text-outline font-mono uppercase">{sec.status}</span>
                          </div>
                          <div className="text-[10px] text-on-surface-variant max-h-[80px] overflow-y-auto whitespace-pre-wrap leading-relaxed font-sans">
                            {sec.content || "Draft section pending..."}
                          </div>
                          <div className="flex gap-2 items-center mt-1">
                            <input
                              type="text"
                              placeholder="Regen instructions (e.g. Add more facts)..."
                              value={regenInstructions[sec.id] || ""}
                              onChange={(e) => setRegenInstructions({ ...regenInstructions, [sec.id]: e.target.value })}
                              className="flex-1 bg-surface border border-outline/15 rounded px-2 py-1 text-[10px] text-primary focus:outline-none"
                            />
                            <button
                              onClick={() => handleRegenSection(sec.id)}
                              className="px-3 py-1 border border-primary/50 hover:bg-primary/10 text-primary font-mono text-[9px] transition-colors"
                            >
                              REGEN SECTION
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                    <button
                      onClick={async () => {
                        const headers: Record<string, string> = {};
                        if (config.apiKey) headers["X-METHER-KEY"] = config.apiKey;
                        await fetch(`${config.backendUrl}/api/v1/research/${activeTaskId}/outline/approve`, {
                          method: "POST",
                          headers,
                          body: JSON.stringify({ modified_sections: sections }),
                        });
                      }}
                      className="py-1.5 border border-success text-success hover:bg-success/10 font-mono text-xs transition-colors"
                    >
                      FINAL APPROVAL & COMPILE DOCUMENT
                    </button>
                  </div>
                )}

                {taskState.stage === "completed" && (
                  <div className="border border-success/35 bg-success/5 rounded p-4 flex flex-col gap-4">
                    <div className="text-xs font-mono text-success font-bold">✓ PIPELINE COMPLETED SUCCESSFULLY</div>
                    <div className="text-[10px] text-outline-variant font-mono">
                      Output Location: <span className="text-primary break-all">{taskState.output_path || "--"}</span>
                    </div>

                    <div className="flex flex-col gap-2 mt-2">
                      <span className="text-[10px] font-mono text-outline">EXPORT AS ANOTHER FORMAT:</span>
                      <div className="flex gap-2">
                        {["PDF", "DOCX", "PPTX", "HTML"].map((fmt) => (
                          <button
                            key={fmt}
                            onClick={() => handleExport(fmt)}
                            className="px-3 py-1 border border-primary/30 hover:border-primary text-primary font-mono text-[10px] transition-colors"
                          >
                            {fmt}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Queue status resets */}
                {taskState.status === "completed" && (
                  <button 
                    onClick={() => setTaskState(null)} 
                    className="py-1 border border-outline/30 hover:bg-surface-container font-mono text-xs text-outline tracking-wider"
                  >
                    START ANOTHER RESEARCH JOB
                  </button>
                )}
              </div>
            )}
            
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
