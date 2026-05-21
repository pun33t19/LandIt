"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { FileText, Search, LayoutDashboard, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

const nav = [
  { href: "/",              label: "Dashboard", icon: LayoutDashboard },
  { href: "/resume/upload", label: "Resume",    icon: FileText },
  { href: "/jobs/search",   label: "Jobs",      icon: Search },
];

export function Navbar() {
  const path = usePathname();
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const isDark = matchMedia("(prefers-color-scheme: dark)").matches;
    setDark(isDark);
    document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
  };

  return (
    <nav className="sticky top-0 z-40 border-b border-[var(--color-divider)] bg-[var(--color-surface)]/90 backdrop-blur-sm">
      <div className="max-w-[1200px] mx-auto px-6 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold text-[var(--color-text)]">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-label="ResumeAI">
            <rect x="3" y="2" width="14" height="18" rx="2" stroke="var(--color-primary)" strokeWidth="1.5"/>
            <path d="M7 7h6M7 11h8M7 15h4" stroke="var(--color-primary)" strokeWidth="1.5" strokeLinecap="round"/>
            <circle cx="18" cy="17" r="4" fill="var(--color-primary)"/>
            <path d="M16.5 17l1 1 2-2" stroke="var(--color-text-inverse)" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span style={{ fontFamily: "var(--font-display)" }}>ResumeAI</span>
        </Link>

        <div className="flex items-center gap-1">
          {nav.map((item) => {
            const Icon = item.icon;
            const active = path === item.href || (item.href !== "/" && path.startsWith(item.href));
            return (
              <Link key={item.href} href={item.href} className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-md)]",
                "text-[length:var(--text-sm)] transition-colors",
                active
                  ? "bg-[var(--color-primary-highlight)] text-[var(--color-primary)] font-medium"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-offset)]"
              )}>
                <Icon size={14} />{item.label}
              </Link>
            );
          })}
        </div>

        <button onClick={toggle} aria-label="Toggle theme"
          className="p-2 rounded-[var(--radius-md)] text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-offset)] transition-colors">
          {dark ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </nav>
  );
}
