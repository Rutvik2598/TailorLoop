"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Plus, Pencil, Trash2 } from "lucide-react";
import {
  getEducation,
  createEducation,
  updateEducation,
  deleteEducation,
  EducationEntry,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardHeader } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

// ---------------------------------------------------------------------------
// Education form dialog
// ---------------------------------------------------------------------------

type EduForm = { institution: string; degree: string; field: string; graduation_year: string; gpa: string };

function EducationDialog({
  open,
  initial,
  onClose,
  onSave,
}: {
  open: boolean;
  initial: EducationEntry | null;
  onClose: () => void;
  onSave: (data: EduForm) => Promise<void>;
}) {
  const blank: EduForm = { institution: "", degree: "", field: "", graduation_year: "", gpa: "" };
  const [form, setForm] = useState<EduForm>(blank);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm(
      initial
        ? {
            institution: initial.institution,
            degree: initial.degree,
            field: initial.field,
            graduation_year: initial.graduation_year,
            gpa: initial.gpa ?? "",
          }
        : blank
    );
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial, open]);

  const set = (k: keyof EduForm, v: string) => setForm((f) => ({ ...f, [k]: v }));

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
          <DialogTitle>{initial ? "Edit Education" : "Add Education"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label>Institution</Label>
            <Input value={form.institution} onChange={(e) => set("institution", e.target.value)} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Degree</Label>
              <Input value={form.degree} onChange={(e) => set("degree", e.target.value)} placeholder="Bachelor of Science" required />
            </div>
            <div className="space-y-1.5">
              <Label>Field of Study</Label>
              <Input value={form.field} onChange={(e) => set("field", e.target.value)} placeholder="Computer Science" required />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Graduation Year</Label>
              <Input value={form.graduation_year} onChange={(e) => set("graduation_year", e.target.value)} placeholder="2024" required />
            </div>
            <div className="space-y-1.5">
              <Label>GPA <span className="text-gray-400 font-normal">(optional)</span></Label>
              <Input value={form.gpa} onChange={(e) => set("gpa", e.target.value)} placeholder="3.8 / 4.0" />
            </div>
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
// Page
// ---------------------------------------------------------------------------

export default function EducationPage() {
  const [entries, setEntries] = useState<EducationEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<EducationEntry | null>(null);

  const refresh = async () => {
    const data = await getEducation();
    setEntries(data);
  };

  useEffect(() => { refresh().finally(() => setLoading(false)); }, []);

  const openAdd = () => { setEditing(null); setDialogOpen(true); };
  const openEdit = (e: EducationEntry) => { setEditing(e); setDialogOpen(true); };

  const handleSave = async (form: EduForm) => {
    const payload = {
      institution: form.institution,
      degree: form.degree,
      field: form.field,
      graduation_year: form.graduation_year,
      gpa: form.gpa || null,
    };
    try {
      if (editing) {
        await updateEducation(editing.id, payload);
        toast.success("Education updated");
      } else {
        await createEducation(payload);
        toast.success("Education added");
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
      await deleteEducation(id);
      await refresh();
      toast.success("Education deleted");
    } catch (e: unknown) {
      toast.error("Delete failed: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  if (loading) return <div className="p-8 text-gray-500 text-sm">Loading...</div>;

  return (
    <div className="p-8 max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Education</h1>
        <Button onClick={openAdd} size="sm">
          <Plus size={15} className="mr-1.5" />
          Add Education
        </Button>
      </div>

      {entries.length === 0 && (
        <p className="text-gray-500 text-sm">No education yet. Add your first degree.</p>
      )}

      <div className="space-y-3">
        {entries.map((edu) => (
          <Card key={edu.id}>
            <CardHeader className="py-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-gray-900">{edu.institution}</p>
                  <p className="text-sm text-gray-600">
                    {edu.degree} · {edu.field}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Class of {edu.graduation_year}
                    {edu.gpa && <> · GPA: {edu.gpa}</>}
                  </p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openEdit(edu)}>
                    <Pencil size={13} />
                  </Button>
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 hover:text-red-500" onClick={() => handleDelete(edu.id)}>
                    <Trash2 size={13} />
                  </Button>
                </div>
              </div>
            </CardHeader>
          </Card>
        ))}
      </div>

      <EducationDialog
        open={dialogOpen}
        initial={editing}
        onClose={() => { setDialogOpen(false); setEditing(null); }}
        onSave={handleSave}
      />
    </div>
  );
}
