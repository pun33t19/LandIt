"use client";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ATSScoreGauge } from "@/components/ATSScoreGauge";
import { DiffViewer, ExperienceDiffViewer } from "@/components/DiffViewer";
import { Spinner } from "@/components/ui/Spinner";
import { getTailorStatus, reviewTailoring } from "@/lib/api";
import { CheckCircle2, XCircle, ArrowUp, Minus } from "lucide-react";

export default function TailorReviewPage() {
  const { sessionId } = useParams() as { sessionId: string };
  const router = useRouter();

  const { data, isLoading } = useQuery({
    queryKey: ["tailor", sessionId],
    queryFn: () => getTailorStatus(sessionId),
    refetchInterval: (query) => {
      const d = query.state.data as any;
      return d?.status === "awaiting_review" || d?.status === "complete" ? false : 2000;
    },
  });

  const reviewMutation = useMutation({
    mutationFn: (action: "approve" | "reject") => reviewTailoring(sessionId, action),
    onSuccess: (_: unknown, action: string) => {
      if (action === "approve") router.push(`/tailor/${sessionId}/result`);
      else router.push("/jobs/search");
    },
  });

  if (isLoading || !data) return (
    <div className="max-w-3xl mx-auto text-center pt-16 space-y-3">
      <Spinner />
      <p className="text-[var(--color-text-muted)]" style={{ fontSize: "var(--text-sm)" }}>
        Tailoring your resume…
      </p>
    </div>
  );

  const d = data as any;
  const delta = ((d.jd_ats_score || 0) - (d.generic_ats_score || 0));
  const breakdown = d.jd_ats_breakdown || {};

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-28">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)" }}>
            Review Changes
          </h1>
          <p className="text-[var(--color-text-muted)] mt-1">
            Approve to save, reject to keep your original resume.
          </p>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <ATSScoreGauge score={d.generic_ats_score || 0} label="Original" size="sm" />
          <div className="flex flex-col items-center gap-0.5">
            {delta > 0
              ? <ArrowUp size={14} className="text-[var(--color-success)]" />
              : <Minus size={14} className="text-[var(--color-text-faint)]" />}
            <span
              style={{ fontSize: "var(--text-xs)" }}
              className={delta > 0 ? "text-[var(--color-success)]" : "text-[var(--color-text-faint)]"}
            >
              {delta > 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1)}
            </span>
          </div>
          <ATSScoreGauge score={d.jd_ats_score || 0} label="Tailored" size="sm" />
        </div>
      </div>

      {/* Keywords */}
      {(d.keywords_added?.length > 0 || d.keywords_missed?.length > 0) && (
        <Card>
          <CardHeader>
            <p className="font-semibold text-[var(--color-text)]" style={{ fontSize: "var(--text-sm)" }}>
              Keywords
            </p>
          </CardHeader>
          <CardBody className="space-y-3">
            {d.keywords_added?.length > 0 && (
              <div>
                <p style={{ fontSize: "var(--text-xs)" }} className="text-[var(--color-text-muted)] mb-1.5">Added</p>
                <div className="flex flex-wrap gap-1.5">
                  {d.keywords_added.map((kw: string, i: number) => (
                    <Badge key={i} variant="success">{kw}</Badge>
                  ))}
                </div>
              </div>
            )}
            {d.keywords_missed?.length > 0 && (
              <div>
                <p style={{ fontSize: "var(--text-xs)" }} className="text-[var(--color-text-muted)] mb-1.5">Still missing</p>
                <div className="flex flex-wrap gap-1.5">
                  {d.keywords_missed.slice(0, 8).map((kw: string, i: number) => (
                    <Badge key={i} variant="warning">{kw}</Badge>
                  ))}
                </div>
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {/* Summary Diff */}
      {d.diff?.summary_diff?.length > 0 && (
        <Card>
          <CardHeader>
            <p className="font-semibold text-[var(--color-text)]" style={{ fontSize: "var(--text-sm)" }}>Summary</p>
          </CardHeader>
          <CardBody>
            <DiffViewer tokens={d.diff.summary_diff} />
          </CardBody>
        </Card>
      )}

      {/* Experience Diffs */}
      {d.diff?.experience_diffs?.length > 0 && (
        <Card>
          <CardHeader>
            <p className="font-semibold text-[var(--color-text)]" style={{ fontSize: "var(--text-sm)" }}>Experience Bullets</p>
          </CardHeader>
          <CardBody>
            <ExperienceDiffViewer diffs={d.diff.experience_diffs} />
          </CardBody>
        </Card>
      )}

      {/* Score Breakdown */}
      {Object.keys(breakdown).length > 0 && (
        <Card>
          <CardHeader>
            <p className="font-semibold text-[var(--color-text)]" style={{ fontSize: "var(--text-sm)" }}>Score Breakdown</p>
          </CardHeader>
          <CardBody className="space-y-3">
            {Object.entries(breakdown).map(([key, val]: [string, any]) => (
              <div key={key} className="flex items-center gap-3">
                <p
                  style={{ fontSize: "var(--text-xs)" }}
                  className="text-[var(--color-text-muted)] w-52 capitalize shrink-0"
                >
                  {key.replace(/_/g, " ")}
                </p>
                <div className="flex-1 h-1.5 bg-[var(--color-surface-offset)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[var(--color-primary)] rounded-full transition-all duration-700"
                    style={{ width: `${(val.score / val.max) * 100}%` }}
                  />
                </div>
                <p
                  style={{ fontSize: "var(--text-xs)" }}
                  className="font-mono text-[var(--color-text-muted)] w-14 text-right shrink-0"
                >
                  {val.score}/{val.max}
                </p>
              </div>
            ))}
          </CardBody>
        </Card>
      )}

      {/* Fixed Action Bar */}
      <div className="fixed bottom-6 right-6 flex gap-3 z-40">
        <Button
          variant="danger"
          onClick={() => reviewMutation.mutate("reject")}
          loading={reviewMutation.isPending}
        >
          <XCircle size={16} /> Reject
        </Button>
        <Button
          onClick={() => reviewMutation.mutate("approve")}
          loading={reviewMutation.isPending}
        >
          <CheckCircle2 size={16} /> Approve →
        </Button>
      </div>
    </div>
  );
}
