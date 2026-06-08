"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Check, X, ExternalLink } from "lucide-react";
import {
  getProjects,
  createProject,
  updateProject,
  deleteProject,
  addProjectBullet,
  updateProjectBullet,
  deleteProjectBullet,
  ProjectEntry,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

// ---------------------------------------------------------------------------
// Project form dialog
// ---------------------------------------------------------------------------

type ProjForm = { name: string; description: string; tech_stack: string; url: string };

function ProjectDialog({
  open,
  initial,
  onClose,
  onSave,
}: {
  open: boolean;
  initial: ProjectEntry | null;
  onClose: () => void;
  onSave: (data: ProjForm) => Promise<void>;
}) {
  const blank: ProjForm = { name: "", description: "", tech_stack: "", url: "" };
  const [form, setForm] = useState<ProjForm>(blank);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm(
      initial
        ? {
            name: initial.name,
            description: initial.description,
            tech_stack: initial.tech_stack.join(", "),
            url: initial.url ?? "",
          }
        : blank
    );
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial, open]);

  const set = (k: keyof ProjForm, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{initial ? "Edit Project" : "Add Project"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label>Project Name</Label>
            <Input value={form.name} onChange={(e) => set("name", e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Textarea value={form.description} onChange={(e) => set("description", e.target.value)} rows={3} required />
          </div>
          <div className="space-y-1.5">
            <Label>Tech Stack</Label>
            <Input value={form.tech_stack} onChange={(e) => set("tech_stack", e.target.value)} placeholder="Python, FastAPI, React" />
            <p className="text-xs text-gray-500">Comma-separated</p>
          </div>
          <div className="space-y-1.5">
            <Label>URL</Label>
            <Input value={form.url} onChange={(e) => set("url", e.target.value)} placeholder="github.com/you/project" />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving ? "Saving..." : "Save"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Bullet row — inline editing
// ---------------------------------------------------------------------------

function BulletRow({
  projId,
  bulletId,
  text,
  onUpdated,
  onDeleted,
}: {
  projId: string;
  bulletId: string;
  text: string;
  onUpdated: (t: string) => void;
  onDeleted: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(text);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!draft.trim()) return;
    setBusy(true);
    try {
      await updateProjectBullet(projId, bulletId, draft.trim());
      onUpdated(draft.trim());
      setEditing(false);
    } catch (e: unknown) {
      toast.error("Update failed: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      await deleteProjectBullet(projId, bulletId);
      onDeleted();
    } catch (e: unknown) {
      toast.error("Delete failed: " + (e instanceof Error ? e.message : String(e)));
      setBusy(false);
    }
  };

  if (editing) {
    return (
      <div className="flex items-center gap-2">
        <Input autoFocus value={draft} onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }}
          className="h-8 text-sm" />
        <button onClick={save} disabled={busy} className="text-green-600 hover:text-green-700 shrink-0"><Check size={15} /></button>
        <button onClick={() => { setDraft(text); setEditing(false); }} className="text-gray-400 hover:text-gray-600 shrink-0"><X size={15} /></button>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2 group">
      <span className="text-gray-400 mt-0.5 shrink-0">•</span>
      <span className="flex-1 text-sm text-gray-700 leading-relaxed">{text}</span>
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        <button onClick={() => { setDraft(text); setEditing(true); }} className="text-gray-400 hover:text-gray-600"><Pencil size={13} /></button>
        <button onClick={remove} disabled={busy} className="text-gray-400 hover:text-red-500"><Trash2 size={13} /></button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ProjectsPage() {
  const [entries, setEntries] = useState<ProjectEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ProjectEntry | null>(null);
  const [addingBulletFor, setAddingBulletFor] = useState<string | null>(null);
  const [newBulletText, setNewBulletText] = useState("");

  const refresh = async () => {
    const data = await getProjects();
    setEntries(data);
  };

  useEffect(() => { refresh().finally(() => setLoading(false)); }, []);

  const openAdd = () => { setEditing(null); setDialogOpen(true); };
  const openEdit = (p: ProjectEntry) => { setEditing(p); setDialogOpen(true); };

  const handleSave = async (form: ProjForm) => {
    const payload = {
      name: form.name,
      description: form.description,
      tech_stack: form.tech_stack.split(",").map((s) => s.trim()).filter(Boolean),
      url: form.url || null,
    };
    try {
      if (editing) {
        await updateProject(editing.id, payload);
        toast.success("Project updated");
      } else {
        await createProject(payload);
        toast.success("Project added");
      }
      await refresh();
      setDialogOpen(false);
      setEditing(null);
    } catch (e: unknown) {
      toast.error("Save failed: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteProject(id);
      await refresh();
      toast.success("Project deleted");
    } catch (e: unknown) {
      toast.error("Delete failed: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const handleAddBullet = async (projId: string) => {
    if (!newBulletText.trim()) return;
    try {
      await addProjectBullet(projId, newBulletText.trim());
      await refresh();
      setAddingBulletFor(null);
      setNewBulletText("");
    } catch (e: unknown) {
      toast.error("Failed: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const updateBulletInState = (projId: string, bulletId: string, newText: string) => {
    setEntries((ps) =>
      ps.map((p) =>
        p.id === projId
          ? { ...p, bullets: p.bullets.map((b) => (b.id === bulletId ? { ...b, text: newText } : b)) }
          : p
      )
    );
  };

  const removeBulletFromState = (projId: string, bulletId: string) => {
    setEntries((ps) =>
      ps.map((p) =>
        p.id === projId ? { ...p, bullets: p.bullets.filter((b) => b.id !== bulletId) } : p
      )
    );
  };

  if (loading) return <div className="p-8 text-gray-500 text-sm">Loading...</div>;

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
        <Button onClick={openAdd} size="sm">
          <Plus size={15} className="mr-1.5" />
          Add Project
        </Button>
      </div>

      {entries.length === 0 && (
        <p className="text-gray-500 text-sm">No projects yet. Add your first project.</p>
      )}

      <div className="space-y-4">
        {entries.map((proj) => (
          <Card key={proj.id}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-gray-900">{proj.name}</p>
                    {proj.url && (
                      <a href={proj.url.startsWith("http") ? proj.url : `https://${proj.url}`}
                        target="_blank" rel="noopener noreferrer"
                        className="text-gray-400 hover:text-indigo-600 transition-colors">
                        <ExternalLink size={13} />
                      </a>
                    )}
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5 leading-snug">{proj.description}</p>
                  {proj.tech_stack.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {proj.tech_stack.map((t) => (
                        <Badge key={t} variant="secondary" className="text-xs px-1.5 py-0">{t}</Badge>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex gap-1 shrink-0">
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openEdit(proj)}>
                    <Pencil size={13} />
                  </Button>
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 hover:text-red-500" onClick={() => handleDelete(proj.id)}>
                    <Trash2 size={13} />
                  </Button>
                </div>
              </div>
            </CardHeader>

            {(proj.bullets.length > 0 || addingBulletFor === proj.id) && (
              <>
                <Separator />
                <CardContent className="pt-3 space-y-2">
                  {proj.bullets.map((b) => (
                    <BulletRow
                      key={b.id}
                      projId={proj.id}
                      bulletId={b.id}
                      text={b.text}
                      onUpdated={(t) => updateBulletInState(proj.id, b.id, t)}
                      onDeleted={() => removeBulletFromState(proj.id, b.id)}
                    />
                  ))}

                  {addingBulletFor === proj.id && (
                    <div className="flex items-center gap-2 mt-1">
                      <Input autoFocus value={newBulletText} onChange={(e) => setNewBulletText(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleAddBullet(proj.id);
                          if (e.key === "Escape") { setAddingBulletFor(null); setNewBulletText(""); }
                        }}
                        placeholder="New bullet point..." className="h-8 text-sm" />
                      <button onClick={() => handleAddBullet(proj.id)} className="text-green-600 hover:text-green-700 shrink-0"><Check size={15} /></button>
                      <button onClick={() => { setAddingBulletFor(null); setNewBulletText(""); }} className="text-gray-400 hover:text-gray-600 shrink-0"><X size={15} /></button>
                    </div>
                  )}
                </CardContent>
              </>
            )}

            {addingBulletFor !== proj.id && (
              <div className="px-6 pb-3">
                <button onClick={() => { setAddingBulletFor(proj.id); setNewBulletText(""); }}
                  className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1">
                  <Plus size={12} /> Add bullet
                </button>
              </div>
            )}
          </Card>
        ))}
      </div>

      <ProjectDialog
        open={dialogOpen}
        initial={editing}
        onClose={() => { setDialogOpen(false); setEditing(null); }}
        onSave={handleSave}
      />
    </div>
  );
}
