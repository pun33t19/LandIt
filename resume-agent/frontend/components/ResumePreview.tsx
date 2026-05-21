import { Badge } from "@/components/ui/Badge";

interface Exp {
  role: string; company: string; start_date?: string; end_date?: string;
  bullets?: string[]; tech_used?: string[];
}
interface Edu { degree: string; institution: string; year?: string; }
interface ResumeData {
  name?: string; email?: string; phone?: string; summary?: string;
  skills?: string[]; experience?: Exp[]; education?: Edu[];
}

export function ResumePreview({ data }: { data: ResumeData }) {
  return (
    <div className="space-y-6 text-[length:var(--text-sm)]">
      {(data.name || data.email) && (
        <div>
          {data.name && (
            <h2 className="text-[length:var(--text-lg)] font-semibold text-[var(--color-text)]">
              {data.name}
            </h2>
          )}
          {(data.email || data.phone) && (
            <p className="text-[var(--color-text-muted)] mt-0.5">
              {data.email}{data.email && data.phone ? " · " : ""}{data.phone}
            </p>
          )}
        </div>
      )}

      {data.summary && (
        <div>
          <h3 className="text-[length:var(--text-xs)] font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-2">
            Summary
          </h3>
          <p className="text-[var(--color-text)] leading-relaxed">{data.summary}</p>
        </div>
      )}

      {data.skills && data.skills.length > 0 && (
        <div>
          <h3 className="text-[length:var(--text-xs)] font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-2">
            Skills
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {data.skills.map((s, i) => <Badge key={i}>{s}</Badge>)}
          </div>
        </div>
      )}

      {data.experience && data.experience.length > 0 && (
        <div>
          <h3 className="text-[length:var(--text-xs)] font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-3">
            Experience
          </h3>
          <div className="space-y-5">
            {data.experience.map((exp, i) => (
              <div key={i}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold text-[var(--color-text)]">{exp.role}</p>
                    <p className="text-[var(--color-text-muted)]">{exp.company}</p>
                  </div>
                  {(exp.start_date || exp.end_date) && (
                    <p className="text-[length:var(--text-xs)] text-[var(--color-text-faint)] whitespace-nowrap">
                      {exp.start_date} – {exp.end_date || "Present"}
                    </p>
                  )}
                </div>
                {exp.bullets && exp.bullets.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {exp.bullets.map((b, j) => (
                      <li key={j} className="flex gap-2 text-[var(--color-text)]">
                        <span className="text-[var(--color-primary)] mt-1.5 shrink-0">·</span>
                        <span>{b}</span>
                      </li>
                    ))}
                  </ul>
                )}
                {exp.tech_used && exp.tech_used.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {exp.tech_used.map((t, j) => <Badge key={j} variant="primary">{t}</Badge>)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {data.education && data.education.length > 0 && (
        <div>
          <h3 className="text-[length:var(--text-xs)] font-semibold uppercase tracking-wide text-[var(--color-text-muted)] mb-2">
            Education
          </h3>
          <div className="space-y-2">
            {data.education.map((edu, i) => (
              <div key={i} className="flex justify-between">
                <div>
                  <p className="font-medium text-[var(--color-text)]">{edu.degree}</p>
                  <p className="text-[var(--color-text-muted)]">{edu.institution}</p>
                </div>
                {edu.year && (
                  <p className="text-[length:var(--text-xs)] text-[var(--color-text-faint)]">{edu.year}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
