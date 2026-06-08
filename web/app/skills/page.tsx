"use client";

import { useState, useEffect, KeyboardEvent } from "react";
import { toast } from "sonner";
import { X, Plus } from "lucide-react";
import { getSkills, addSkill, deleteSkill } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function SkillsPage() {
  const [skills, setSkills] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [adding, setAdding] = useState(false);

  const refresh = async () => {
    const data = await getSkills();
    setSkills(data);
  };

  useEffect(() => { refresh().finally(() => setLoading(false)); }, []);

  const handleAdd = async () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    if (skills.includes(trimmed)) {
      toast.error(`"${trimmed}" is already in your skills.`);
      return;
    }
    setAdding(true);
    try {
      await addSkill(trimmed);
      setSkills((s) => [...s, trimmed]);
      setInput("");
      toast.success(`Added "${trimmed}"`);
    } catch (e: unknown) {
      toast.error("Failed: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (skill: string) => {
    try {
      await deleteSkill(skill);
      setSkills((s) => s.filter((x) => x !== skill));
      toast.success(`Removed "${skill}"`);
    } catch (e: unknown) {
      toast.error("Failed: " + (e instanceof Error ? e.message : String(e)));
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") { e.preventDefault(); handleAdd(); }
    if (e.key === "Escape") setInput("");
  };

  if (loading) return <div className="p-8 text-gray-500 text-sm">Loading...</div>;

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Skills</h1>

      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Add a Skill</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g. TypeScript"
              className="max-w-xs"
            />
            <Button onClick={handleAdd} disabled={adding || !input.trim()} size="sm">
              <Plus size={14} className="mr-1" />
              Add
            </Button>
          </div>
          <p className="text-xs text-gray-400 mt-2">Press Enter to add quickly.</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Your Skills</CardTitle>
            <span className="text-xs text-gray-400">{skills.length} skills</span>
          </div>
        </CardHeader>
        <CardContent>
          {skills.length === 0 ? (
            <p className="text-sm text-gray-500">No skills yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {skills.map((skill) => (
                <Badge
                  key={skill}
                  variant="secondary"
                  className="flex items-center gap-1.5 px-2.5 py-1 text-sm"
                >
                  {skill}
                  <button
                    onClick={() => handleDelete(skill)}
                    className="text-gray-400 hover:text-red-500 transition-colors ml-0.5 leading-none"
                    aria-label={`Remove ${skill}`}
                  >
                    <X size={12} />
                  </button>
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
