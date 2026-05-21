"use client";
import { cn } from "@/lib/utils";

interface DiffToken { type: "added" | "removed" | "equal"; text: string; }

export function DiffViewer({ tokens, label }: { tokens: DiffToken[]; label?: string }) {
  return (
    <div className="space-y-2">
      {label && (
        <p className="text-[length:var(--text-xs)] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
          {label}
        </p>
      )}
      <p className="text-[length:var(--text-sm)] leading-relaxed text-[var(--color-text)]">
        {tokens.map((t, i) => (
          <span key={i} className={cn({
            "bg-[var(--color-success-highlight)] text-[var(--color-success)] rounded px-0.5 mx-0.5": t.type === "added",
            "bg-[var(--color-error-highlight)] text-[var(--color-error)] line-through rounded px-0.5 mx-0.5": t.type === "removed",
          })}>
            {t.text}
          </span>
        ))}
      </p>
    </div>
  );
}

interface BulletDiff { index: number; changed: boolean; original: string; tailored: string; tokens?: DiffToken[]; }
interface ExpDiff { role: string; company?: string; bullet_diffs: BulletDiff[]; }

export function ExperienceDiffViewer({ diffs }: { diffs: ExpDiff[] }) {
  return (
    <div className="space-y-6">
      {diffs.map((exp, i) => (
        <div key={i} className="space-y-2">
          <h4 className="text-[length:var(--text-sm)] font-semibold text-[var(--color-text)]">
            {exp.role}
            {exp.company && (
              <span className="font-normal text-[var(--color-text-muted)]"> · {exp.company}</span>
            )}
          </h4>
          <div className="space-y-2 pl-4 border-l-2 border-[var(--color-divider)]">
            {exp.bullet_diffs.map((b, j) => (
              <div key={j}>
                {b.changed && b.tokens
                  ? <DiffViewer tokens={b.tokens} />
                  : <p className="text-[length:var(--text-sm)] text-[var(--color-text-muted)]">{b.original}</p>
                }
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
