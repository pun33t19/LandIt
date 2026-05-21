import Link from "next/link";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FileUp, Sparkles, Search, ArrowRight } from "lucide-react";

const steps = [
  { step: "01", icon: FileUp,     title: "Upload Resume",  desc: "Parse your PDF into structured data",        href: "/resume/upload" },
  { step: "02", icon: Sparkles,   title: "Optimise",       desc: "AI improves your resume generically",        href: "/resume/upload" },
  { step: "03", icon: Search,     title: "Find Jobs",      desc: "Rank jobs by your profile match score",      href: "/jobs/search" },
  { step: "04", icon: ArrowRight, title: "Tailor & Apply", desc: "Job-specific resume tailored in one click",  href: "/jobs/search" },
];

export default function Dashboard() {
  return (
    <div className="space-y-10">
      <div className="space-y-4 pt-4">
        <h1
          className="text-[var(--color-text)] leading-tight"
          style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)" }}
        >
          Tailor every application.<br />
          <span className="text-[var(--color-primary)]">Land more interviews.</span>
        </h1>
        <p className="text-[var(--color-text-muted)] max-w-lg" style={{ fontSize: "var(--text-base)" }}>
          Upload your resume once. AI optimises, matches jobs, and tailors it per role — with full control over every change.
        </p>
        <div className="flex gap-3 pt-1">
          <Link href="/resume/upload">
            <Button size="lg">Get Started <ArrowRight size={16} /></Button>
          </Link>
          <Link href="/jobs/search">
            <Button size="lg" variant="secondary">Browse Jobs</Button>
          </Link>
        </div>
      </div>

      <div>
        <p className="text-[length:var(--text-xs)] font-semibold text-[var(--color-text-muted)] uppercase tracking-wide mb-4">
          How it works
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {steps.map((s) => {
            const Icon = s.icon;
            return (
              <Link key={s.step} href={s.href}>
                <Card className="hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5 transition-all h-full">
                  <CardBody className="p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="w-9 h-9 rounded-[var(--radius-lg)] bg-[var(--color-primary-highlight)] flex items-center justify-center">
                        <Icon size={16} className="text-[var(--color-primary)]" />
                      </div>
                      <span className="font-mono text-[var(--color-text-faint)]" style={{ fontSize: "var(--text-xs)" }}>
                        {s.step}
                      </span>
                    </div>
                    <div>
                      <p className="font-semibold text-[var(--color-text)]">{s.title}</p>
                      <p className="text-[var(--color-text-muted)] mt-0.5" style={{ fontSize: "var(--text-xs)" }}>
                        {s.desc}
                      </p>
                    </div>
                  </CardBody>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
