"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { User, Briefcase, FolderOpen, GraduationCap, Wrench, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const profileItems = [
  { href: "/about", label: "About", icon: User },
  { href: "/experience", label: "Experience", icon: Briefcase },
  { href: "/projects", label: "Projects", icon: FolderOpen },
  { href: "/education", label: "Education", icon: GraduationCap },
  { href: "/skills", label: "Skills", icon: Wrench },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 shrink-0 bg-gray-900 text-white flex flex-col">
      <div className="px-6 py-5 border-b border-gray-800">
        <h1 className="text-lg font-semibold tracking-tight">TailorLoop</h1>
        <p className="text-xs text-gray-400 mt-0.5">Profile Manager</p>
      </div>

      <nav className="flex-1 px-3 py-4 flex flex-col gap-4">
        {/* Generate — primary action */}
        <Link
          href="/generate"
          className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-semibold transition-colors",
            pathname.startsWith("/generate")
              ? "bg-indigo-600 text-white"
              : "bg-indigo-900/50 text-indigo-300 hover:bg-indigo-600 hover:text-white"
          )}
        >
          <Sparkles size={16} />
          Generate
        </Link>

        {/* Divider */}
        <div>
          <p className="px-3 text-[10px] font-semibold uppercase tracking-widest text-gray-500 mb-1">Profile</p>
          <div className="space-y-0.5">
            {profileItems.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                  pathname.startsWith(href)
                    ? "bg-indigo-600 text-white"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white"
                )}
              >
                <Icon size={16} />
                {label}
              </Link>
            ))}
          </div>
        </div>
      </nav>

      <div className="px-4 py-3 border-t border-gray-800">
        <p className="text-xs text-gray-500 font-mono">API :8000</p>
      </div>
    </aside>
  );
}
