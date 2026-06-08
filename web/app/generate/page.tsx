"use client";

import { useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import {
  Sparkles, CheckCircle2, Circle, Loader2,
  FileText, Mail, AlertCircle, RotateCcw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface StageInfo { key: string; label: string; desc: string; }

interface JobStatus {
  status: "running" | "complete" | "error";
  current_stage: string | null;
  stages_done: string[];
  error: string | null;
  has_files: boolean;
  stages: StageInfo[];
}

// ---------------------------------------------------------------------------
// Stage row component
// ---------------------------------------------------------------------------

function StageRow({
  stage, done, active, index,
}: {
  stage: StageInfo; done: boolean; active: boolean; index: number;
}) {
  return (
    <div
      className={`
        flex items-start gap-4 px-5 py-4 rounded-xl transition-all duration-700
        ${active
          ? "bg-indigo-50 border border-indigo-200 shadow-sm"
          : done
          ? "opacity-55"
          : "opacity-25"}
      `}
      style={{ transitionDelay: `${index * 60}ms` }}
    >
      {/* Icon */}
      <div className="mt-0.5 shrink-0 w-6 h-6 flex items-center justify-center">
        {done ? (
          <CheckCircle2 size={22} className="text-green-500" />
        ) : active ? (
          <div className="relative flex items-center justify-center">
            <div className="absolute w-5 h-5 rounded-full bg-indigo-300 animate-ping opacity-40" />
            <Loader2 size={18} className="relative text-indigo-600 animate-spin z-10" />
          </div>
        ) : (
          <Circle size={22} className="text-gray-300" />
        )}
      </div>

      {/* Text */}
      <div className="flex-1 min-w-0">
        <p className={`font-medium text-sm leading-snug ${
          active ? "text-indigo-900" : done ? "text-gray-600" : "text-gray-400"
        }`}>
          {stage.label}
        </p>
        {(active || done) && (
          <p className={`text-xs mt-0.5 leading-relaxed ${
            active ? "text-indigo-500" : "text-gray-400"
          }`}>
            {stage.desc}
          </p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Animated thinking dots
// ---------------------------------------------------------------------------

function ThinkingDots() {
  return (
    <div className="flex gap-1.5 items-end h-4">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce"
          style={{ animationDelay: `${i * 0.18}s`, animationDuration: "0.9s" }}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function GeneratePage() {
  const [jdText, setJdText] = useState("");
  const [jobId, setJobId]   = useState<string | null>(null);
  const [job, setJob]       = useState<JobStatus | null>(null);
  const [busy, setBusy]     = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Polling ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!jobId) return;
    if (job?.status === "complete" || job?.status === "error") {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/generate/${jobId}`);
        const data: JobStatus = await res.json();
        setJob(data);
        if (data.status === "complete") toast.success("Documents are ready!");
        else if (data.status === "error") toast.error("Generation failed.");
      } catch { /* ignore transient network errors */ }
    }, 1500);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [jobId, job?.status]);

  // ── Submit ─────────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!jdText.trim()) { toast.error("Paste a job description first."); return; }
    setBusy(true);
    try {
      const res = await fetch(`${API}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jd_text: jdText }),
      });
      if (!res.ok) throw new Error(await res.text());
      const { job_id } = await res.json();
      setJobId(job_id);
      setJob({
        status: "running",
        current_stage: "analyze",
        stages_done: [],
        error: null,
        has_files: false,
        stages: [
          { key: "analyze", label: "Analyzing job description",         desc: "Extracting must-have skills, ATS keywords, and responsibilities" },
          { key: "write",   label: "Tailoring resume & cover letter",   desc: "Selecting the best experience and crafting a grounded cover letter" },
          { key: "verify",  label: "Verifying claims",                  desc: "Ensuring every statement traces back to your real experience" },
          { key: "compile", label: "Compiling PDFs",                    desc: "Rendering LaTeX templates and building final documents" },
        ],
      });
    } catch (e: unknown) {
      toast.error("Failed to start: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
    }
  };

  const handleReset = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setJobId(null);
    setJob(null);
    setJdText("");
  };

  const handleDownload = (filename: string) => {
    window.open(`${API}/api/generate/${jobId}/download/${filename}`, "_blank");
  };

  const isRunning  = job?.status === "running";
  const isComplete = job?.status === "complete";
  const isError    = job?.status === "error";
  const stages     = job?.stages ?? [];

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="p-8 max-w-2xl">
      {/* Page header */}
      <div className="flex items-center gap-3 mb-7">
        <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-md shadow-indigo-200">
          <Sparkles size={17} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 leading-tight">Generate Documents</h1>
          <p className="text-sm text-gray-500">Tailored resume + cover letter from any job description</p>
        </div>
      </div>

      {/* ── Input ──────────────────────────────────────────────────────────── */}
      {!job && (
        <Card className="shadow-sm">
          <CardContent className="pt-5">
            <Textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              placeholder="Paste the full job description here…"
              rows={15}
              className="resize-none font-mono text-xs leading-relaxed focus-visible:ring-indigo-400"
            />
            <div className="flex items-center justify-between mt-4">
              <p className="text-xs text-gray-400">
                {jdText.length > 0 ? `${jdText.length.toLocaleString()} characters` : "No content yet"}
              </p>
              <Button
                onClick={handleSubmit}
                disabled={busy || !jdText.trim()}
                className="bg-indigo-600 hover:bg-indigo-700"
              >
                {busy
                  ? <><Loader2 size={14} className="mr-2 animate-spin" />Starting…</>
                  : <><Sparkles size={14} className="mr-2" />Generate</>}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Progress ───────────────────────────────────────────────────────── */}
      {job && !isError && (
        <div className="space-y-4">
          {/* Status banner */}
          {isRunning && (
            <div className="flex items-center gap-3 px-5 py-3.5 rounded-xl bg-gradient-to-r from-indigo-50 to-violet-50 border border-indigo-100">
              <ThinkingDots />
              <p className="text-sm font-medium text-indigo-700">AI is working on your documents…</p>
            </div>
          )}

          {isComplete && (
            <div className="flex items-center gap-3 px-5 py-3.5 rounded-xl bg-green-50 border border-green-100">
              <CheckCircle2 size={18} className="text-green-500 shrink-0" />
              <p className="text-sm font-medium text-green-700">Your tailored documents are ready!</p>
            </div>
          )}

          {/* Stage tracker */}
          <Card className="shadow-sm overflow-hidden">
            <CardContent className="pt-4 pb-3">
              <div className="space-y-1">
                {stages.map((stage, i) => (
                  <StageRow
                    key={stage.key}
                    stage={stage}
                    index={i}
                    done={job.stages_done.includes(stage.key)}
                    active={job.current_stage === stage.key}
                  />
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Download buttons */}
          {isComplete && (
            <div className="grid grid-cols-2 gap-3 pt-1">
              <button
                onClick={() => handleDownload("resume.pdf")}
                className="group flex flex-col items-center gap-2 px-4 py-5 rounded-xl border-2 border-indigo-100 bg-white hover:border-indigo-400 hover:bg-indigo-50 transition-all duration-200 shadow-sm"
              >
                <div className="w-10 h-10 rounded-lg bg-indigo-100 group-hover:bg-indigo-200 flex items-center justify-center transition-colors">
                  <FileText size={20} className="text-indigo-600" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-gray-800">Resume</p>
                  <p className="text-xs text-gray-400">resume.pdf</p>
                </div>
                <span className="text-xs font-medium text-indigo-600 flex items-center gap-1">
                  Download
                </span>
              </button>

              <button
                onClick={() => handleDownload("cover_letter.pdf")}
                className="group flex flex-col items-center gap-2 px-4 py-5 rounded-xl border-2 border-indigo-100 bg-white hover:border-indigo-400 hover:bg-indigo-50 transition-all duration-200 shadow-sm"
              >
                <div className="w-10 h-10 rounded-lg bg-indigo-100 group-hover:bg-indigo-200 flex items-center justify-center transition-colors">
                  <Mail size={20} className="text-indigo-600" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-semibold text-gray-800">Cover Letter</p>
                  <p className="text-xs text-gray-400">cover_letter.pdf</p>
                </div>
                <span className="text-xs font-medium text-indigo-600">Download</span>
              </button>
            </div>
          )}

          {/* Reset */}
          {isComplete && (
            <button
              onClick={handleReset}
              className="w-full flex items-center justify-center gap-2 py-2.5 text-sm text-gray-400 hover:text-gray-600 transition-colors"
            >
              <RotateCcw size={13} />
              Generate for another job
            </button>
          )}
        </div>
      )}

      {/* ── Error ──────────────────────────────────────────────────────────── */}
      {isError && (
        <div className="space-y-4">
          <div className="flex items-start gap-3 px-5 py-4 rounded-xl bg-red-50 border border-red-100">
            <AlertCircle size={18} className="text-red-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-red-700">Generation failed</p>
              <p className="text-xs text-red-500 mt-1 font-mono break-all">{job?.error}</p>
            </div>
          </div>
          <button
            onClick={handleReset}
            className="w-full flex items-center justify-center gap-2 py-2.5 text-sm text-gray-500 hover:text-gray-700 border rounded-lg transition-colors"
          >
            <RotateCcw size={13} />
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
