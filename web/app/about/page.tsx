"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { getMeta, updateMeta, ProfileMeta } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AboutPage() {
  const [form, setForm] = useState<Partial<ProfileMeta>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getMeta()
      .then((d) => setForm(d))
      .catch((e) => toast.error("Failed to load profile: " + e.message))
      .finally(() => setLoading(false));
  }, []);

  const set = (key: keyof ProfileMeta, value: string) =>
    setForm((f) => ({ ...f, [key]: value || null }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateMeta(form);
      toast.success("Profile saved");
    } catch (e: unknown) {
      toast.error("Save failed: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-8 text-gray-500 text-sm">Loading...</div>;

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">About</h1>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Personal Info</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  value={form.name ?? ""}
                  onChange={(e) => set("name", e.target.value)}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={form.email ?? ""}
                  onChange={(e) => set("email", e.target.value)}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  value={form.phone ?? ""}
                  onChange={(e) => set("phone", e.target.value)}
                  placeholder="+1 (555) 000-0000"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="location">Location</Label>
                <Input
                  id="location"
                  value={form.location ?? ""}
                  onChange={(e) => set("location", e.target.value)}
                  placeholder="San Francisco, CA"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="linkedin">LinkedIn</Label>
                <Input
                  id="linkedin"
                  value={form.linkedin ?? ""}
                  onChange={(e) => set("linkedin", e.target.value)}
                  placeholder="linkedin.com/in/yourname"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="github">GitHub</Label>
                <Input
                  id="github"
                  value={form.github ?? ""}
                  onChange={(e) => set("github", e.target.value)}
                  placeholder="github.com/yourname"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="summary">Professional Summary</Label>
              <Textarea
                id="summary"
                value={form.summary ?? ""}
                onChange={(e) => set("summary", e.target.value)}
                rows={5}
                placeholder="Brief professional summary used in your cover letter and resume header..."
              />
            </div>

            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save Changes"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
