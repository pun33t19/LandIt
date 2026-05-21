"use client";
import { Card, CardBody } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ATSScoreGauge } from "@/components/ATSScoreGauge";
import { MapPin, Building2, ArrowRight } from "lucide-react";

interface Job {
  id: string; title: string; company: string; location?: string;
  match_score?: number; required_skills?: string[];
  seniority_level?: string; domain?: string;
}

export function JobCard({ job, onSelect }: { job: Job; onSelect: (job: Job) => void }) {
  return (
    <Card className="hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5 transition-all group">
      <CardBody className="p-5">
        <div className="flex gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold text-[length:var(--text-base)] text-[var(--color-text)] group-hover:text-[var(--color-primary)] transition-colors">
                  {job.title}
                </h3>
                <div className="flex items-center gap-3 mt-1 text-[length:var(--text-xs)] text-[var(--color-text-muted)]">
                  <span className="flex items-center gap-1"><Building2 size={12} />{job.company}</span>
                  {job.location && (
                    <span className="flex items-center gap-1"><MapPin size={12} />{job.location}</span>
                  )}
                </div>
              </div>
              {job.match_score !== undefined && (
                <ATSScoreGauge score={job.match_score} label="Match" size="sm" />
              )}
            </div>
            {job.required_skills && job.required_skills.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-3">
                {job.required_skills.slice(0, 5).map((s, i) => <Badge key={i}>{s}</Badge>)}
                {job.required_skills.length > 5 && (
                  <Badge>+{job.required_skills.length - 5}</Badge>
                )}
              </div>
            )}
            <div className="flex items-center justify-between mt-4">
              <div className="flex gap-2">
                {job.seniority_level && <Badge variant="primary">{job.seniority_level}</Badge>}
                {job.domain && <Badge variant="default">{job.domain}</Badge>}
              </div>
              <Button size="sm" variant="ghost" onClick={() => onSelect(job)}>
                Tailor Resume <ArrowRight size={14} />
              </Button>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
