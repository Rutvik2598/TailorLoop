"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2, Check, X } from "lucide-react";
import {
  getExperience,
  createExperience,
  updateExperience,
  deleteExperience,
  addExperienceBullet,
  updateExperienceBullet,
  deleteExperienceBullet,
  ExperienceEntry,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
// Experience form dialog (create / edit metadata)
// ---------------------------------------------------------------------------

type ExpForm = { company: string; title: string; start_date: string; end_date: string; location: string };

function ExperienceDialog({
  open,
  initial,
  onClose,
  onSave,
}: {
  open: boolean;
  initial: ExperienceEntry | null;
  onClose: () => void;
  onSave: (data: ExpForm) => Promise<void>;
}) {
  const blank: ExpForm = { company: "", title: "", start_date: "", end_date: "", location: "" };
  const [form, setForm] = useState<ExpForm>(blank);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm(
      initial
        ? {
            company: initial.company,
            title: initial.title,
            start_date: initial.start_date,
            end_date: initial.end_date ?? "",
            location: initial.location ?? "",
          }
        : blank
    );
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial, open]);

  const set = (k: keyof ExpForm, v: string) => setForm((f) => ({ ...f, [k]: v }));

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
          <DialogTitle>{initial ? "Edit Experience" : "Add Experience"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label>Company</Label>
            <Input value={form.company} onChange={(e) => set("company", e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label>Title</Label>
            <Input value={form.title} onChange={(e) => set("title", e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Start Date</Label>
              <Input value={form.start_date} onChange={(e) => set("start_date", e.target.value)} placeholder="YYYY-MM" required />
            </div>
            <div className="space-y-1.5">
              <Label>End Date</Label>
              <Input value={form.end_date} onChange={(e) => set("end_date", e.target.value)} placeholder="YYYY-MM or blank" />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Location</Label>
            <Input value={form.location} onChange={(e) => set("location", e.target.value)} placeholder="San Francisco, CA" />
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
// Bullet row — handles inline editing
// ---------------------------------------------------------------------------

function BulletRow({
  expId,
  bulletId,
  text,
  onUpdated,
  onDeleted,
}: {
  expId: string;
  bulletId: string;
  text: string;
  onUpdated: (newText: string) => void;
  onDeleted: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(text);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    if (!draft.trim()) return;
    setBusy(true);
    try {
      await updateExperienceBullet(expId, bulletId, draft.trim());
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
      await deleteExperienceBullet(expId, bulletId);
      onDeleted();
    } catch (e: unknown) {
      toast.error("Delete failed: " + (e instanceof Error ? e.message : String(e)));
      setBusy(false);
    }
  };

  if (editing) {
    return (
      <div className="flex items-center gap-2">
        <Input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") setEditing(false); }}
          className="h-8 text-sm"
        />
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

export default function ExperiencePage() {
  const [entries, setEntries] = useState<ExperienceEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ExperienceEntry | null>(null);
  const [addingBulletFor, setAddingBulletFor] = useState<string | null>(null);
  const [newBulletText, setNewBulletText] = useState("");

  const refresh = async () => {
    const data = await getExperience();
    setEntries(data);
  };

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, []);

  const openAdd = () => { setEditing(null); setDialogOpen(true); };
  const openEdit = (e: ExperienceEntry) => { setEditing(e); setDialogOpen(true); };

  const handleSave = async (form: ExpForm) => {
    const payload = {
      company: form.company,
      title: form.title,
      start_date: form.start_date,
      end_date: form.end_date || null,
      location: form.location || null,
    };
    try {
      if (editing) {
        await updateExperience(editing.id, payload);
        toast.success("Experience updated");
      } else {
        await createExperience(payload);
        toast.success("Experience added");
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
      await deleteExperience(id);
      await refresh();
      toast.success("Experience deleted");
    } catch (e: unknown) {
      toast.error("Delete failed: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const handleAddBullet = async (expId: string) => {
    if (!newBulletText.trim()) return;
    try {
      await addExperienceBullet(expId, newBulletText.trim());
      await refresh();
      setAddingBulletFor(null);
      setNewBulletText("");
    } catch (e: unknown) {
      toast.error("Failed: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const updateBulletInState = (expId: string, bulletId: string, newText: string) => {
    setEntries((es) =>
      es.map((e) =>
        e.id === expId
          ? { ...e, bullets: e.bullets.map((b) => (b.id === bulletId ? { ...b, text: newText } : b)) }
          : e
      )
    );
  };

  const removeBulletFromState = (expId: string, bulletId: string) => {
    setEntries((es) =>
      es.map((e) =>
        e.id === expId ? { ...e, bullets: e.bullets.filter((b) => b.id !== bulletId) } : e
      )
    );
  };

  if (loading) return <div className="p-8 text-gray-500 text-sm">Loading...</div>;

  return (
    <div className="p-8 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Work Experience</h1>
        <Button onClick={openAdd} size="sm">
          <Plus size={15} className="mr-1.5" />
          Add Experience
        </Button>
      </div>

      {entries.length === 0 && (
        <p className="text-gray-500 text-sm">No experience yet. Add your first role.</p>
      )}

      <div className="space-y-4">
        {entries.map((exp) => (
          <Card key={exp.id}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-gray-900">{exp.company}</p>
                  <p className="text-sm text-gray-600">{exp.title}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {exp.start_date} — {exp.end_date ?? "Present"}
                    {exp.location && <> · {exp.location}</>}
                  </p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openEdit(exp)}>
                    <Pencil size={13} />
                  </Button>
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 hover:text-red-500" onClick={() => handleDelete(exp.id)}>
                    <Trash2 size={13} />
                  </Button>
                </div>
              </div>
            </CardHeader>

            {(exp.bullets.length > 0 || addingBulletFor === exp.id) && (
              <>
                <Separator />
                <CardContent className="pt-3 space-y-2">
                  {exp.bullets.map((b) => (
                    <BulletRow
                      key={b.id}
                      expId={exp.id}
                      bulletId={b.id}
                      text={b.text}
                      onUpdated={(t) => updateBulletInState(exp.id, b.id, t)}
                      onDeleted={() => removeBulletFromState(exp.id, b.id)}
                    />
                  ))}

                  {addingBulletFor === exp.id && (
                    <div className="flex items-center gap-2 mt-1">
                      <Input
                        autoFocus
                        value={newBulletText}
                        onChange={(e) => setNewBulletText(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleAddBullet(exp.id);
                          if (e.key === "Escape") { setAddingBulletFor(null); setNewBulletText(""); }
                        }}
                        placeholder="New bullet point..."
                        className="h-8 text-sm"
                      />
                      <button onClick={() => handleAddBullet(exp.id)} className="text-green-600 hover:text-green-700 shrink-0"><Check size={15} /></button>
                      <button onClick={() => { setAddingBulletFor(null); setNewBulletText(""); }} className="text-gray-400 hover:text-gray-600 shrink-0"><X size={15} /></button>
                    </div>
                  )}
                </CardContent>
              </>
            )}

            {addingBulletFor !== exp.id && (
              <div className="px-6 pb-3">
                <button
                  onClick={() => { setAddingBulletFor(exp.id); setNewBulletText(""); }}
                  className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                >
                  <Plus size={12} /> Add bullet
                </button>
              </div>
            )}
          </Card>
        ))}
      </div>

      <ExperienceDialog
        open={dialogOpen}
        initial={editing}
        onClose={() => { setDialogOpen(false); setEditing(null); }}
        onSave={handleSave}
      />
    </div>
  );
}
