"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ATSScoreGauge } from "@/components/ATSScoreGauge";
import { Spinner } from "@/components/ui/Spinner";
import { startOptimise, getOptimiseStatus, reviewOptimise } from "@/lib/api";
import { useResumeStore } from "@/lib/store";
import { CheckCircle2, XCircle, Lightbulb } from "lucide-react";

export default function OptimisePage() {
  const router = useRouter();
  const { id: resumeId } = useParams() as { id: string };
  const { setOptimiseSessionId, resumeData } = useResumeStore();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [started, setStarted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [reviewing, setReviewing] = useState(false);

  useEffect(() => {
    if (started || !resumeData) return;
    setStarted(true);
    setLoading(true);
    (startOptimise(resumeId, resumeData) as Promise<any>)
      .then((r) => {
        setResult(r);
        setSessionId(r.session_id);
        setOptimiseSessionId(r.session_id);
      })
      .catch((e: unknown) => console.error("Optimise failed:", e))
      .finally(() => setLoading(false));
  }, [resumeId, resumeData, started, setOptimiseSessionId]);

 const handleReview = async (action: "approve" | "reject") => {
  if (!sessionId) return;
  setReviewing(true);
  try {
    await reviewOptimise(
      sessionId,
      action,
      result.pending_resume ?? {}  
    );
    if (action === "approve") router.push("/jobs/search");
    else router.push("/");
  } catch (e: unknown) {
    console.error("Review failed:", e);
  } finally {
    setReviewing(false);
  }
};

  if (loading || !result) return (
    <div className="max-w-3xl mx-auto text-center space-y-3 pt-16">
      <Spinner />
      <p className="text-[var(--color-text-muted)]" style={{ fontSize: "var(--text-sm)" }}>
        Analysing your resume…
      </p>
    </div>
  );

  // response fields
  const score: number        = result.original_ats_score ?? result.ats_score ?? 0;
  const suggestions: string[]= result.suggestions ?? [];
  const status: string       = result.status ?? "awaiting_review";
  const iteration: number    = result.iteration ?? 1;

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)" }}>
            Resume Optimisation
          </h1>
          <p className="text-[var(--color-text-muted)] mt-1">
            {suggestions.length} suggestion{suggestions.length !== 1 ? "s" : ""} found
            {iteration > 1 ? ` · Iteration ${iteration}` : ""}
          </p>
        </div>
        <ATSScoreGauge score={score} label="Current Score" size="lg" />
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="space-y-3">
          {suggestions.map((s: string, i: number) => {
            // Parse format: "[context] issue → fix"
            const arrowParts = s.split(" → ");
            const issue = arrowParts[0] ?? s;
            const fix   = arrowParts[1] ?? null;

            // Extract context tag e.g. "[summary]"
            const tagMatch = issue.match(/^\[([^\]]+)\]/);
            const tag      = tagMatch ? tagMatch[1] : null;
            const text     = tag ? issue.replace(`[${tag}]`, "").trim() : issue;

            return (
              <Card key={i}>
                <CardBody className="space-y-2 py-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 shrink-0 w-7 h-7 rounded-[var(--radius-md)] bg-[var(--color-primary-highlight)] flex items-center justify-center">
                      <Lightbulb size={13} className="text-[var(--color-primary)]" />
                    </div>
                    <div className="flex-1 space-y-1.5">
                      {tag && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-[var(--radius-full)] text-[length:var(--text-xs)] font-medium bg-[var(--color-surface-offset)] text-[var(--color-text-muted)] capitalize">
                          {tag}
                        </span>
                      )}
                      <p className="text-[var(--color-text)]" style={{ fontSize: "var(--text-sm)" }}>
                        {text}
                      </p>
                      {fix && (
                        <p className="text-[var(--color-primary)]" style={{ fontSize: "var(--text-xs)" }}>
                          → {fix}
                        </p>
                      )}
                    </div>
                  </div>
                </CardBody>
              </Card>
            );
          })}
        </div>
      )}

      {/* Action Buttons */}
      {status === "awaiting_review" && (
        <div className="flex gap-3 justify-end pt-2">
          <Button
            variant="danger"
            onClick={() => handleReview("reject")}
            loading={reviewing}
          >
            <XCircle size={16} /> Reject All
          </Button>
          <Button
            onClick={() => handleReview("approve")}
            loading={reviewing}
          >
            <CheckCircle2 size={16} /> Approve & Find Jobs →
          </Button>
        </div>
      )}

      {status === "complete" && (
        <Card>
          <CardBody className="flex items-center gap-3">
            <CheckCircle2 size={18} className="text-[var(--color-success)]" />
            <p className="font-medium text-[var(--color-text)]" style={{ fontSize: "var(--text-sm)" }}>
              Optimisation complete!
            </p>
            <Button size="sm" onClick={() => router.push("/jobs/search")} className="ml-auto">
              Find Jobs →
            </Button>
          </CardBody>
        </Card>
      )}
    </div>
  );
}