"use client";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ResumePreview } from "@/components/ResumePreview";
import { ATSScoreGauge } from "@/components/ATSScoreGauge";
import { Spinner } from "@/components/ui/Spinner";
import { getTailorStatus, exportPDF } from "@/lib/api";
import { downloadBlob } from "@/lib/utils";
import { Download, RotateCcw, CheckCircle2 } from "lucide-react";
import { useState } from "react";

export default function ResultPage() {
  const { sessionId } = useParams() as { sessionId: string };
  const router = useRouter();
  const [downloading, setDownloading] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["tailor-result", sessionId],
    queryFn: () => getTailorStatus(sessionId),
  });

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const blob = await exportPDF(sessionId);
      downloadBlob(blob, "tailored-resume.pdf");
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Export failed");
    } finally {
      setDownloading(false);
    }
  };

  if (isLoading || !data) return (
    <div className="max-w-3xl mx-auto text-center pt-16 space-y-3">
      <Spinner />
      <p className="text-[var(--color-text-muted)]" style={{ fontSize: "var(--text-sm)" }}>
        Loading result…
      </p>
    </div>
  );

  const d = data as any;
  const resume = d.tailored_resume || d.original_resume;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle2 size={20} className="text-[var(--color-success)]" />
            <span style={{ fontSize: "var(--text-sm)" }} className="text-[var(--color-success)] font-medium">
              Tailoring approved
            </span>
          </div>
          <h1 className="text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)" }}>
            Your Tailored Resume
          </h1>
          <p className="text-[var(--color-text-muted)] mt-1">
            Ready to apply. Download or tailor for another role.
          </p>
        </div>
        {d.jd_ats_score && (
          <ATSScoreGauge score={d.jd_ats_score} label="JD Score" size="lg" />
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <Button onClick={handleDownload} loading={downloading}>
          <Download size={16} /> Download PDF
        </Button>
        <Button variant="secondary" onClick={() => router.push("/jobs/search")}>
          <RotateCcw size={16} /> Tailor Another Job
        </Button>
        <Button variant="ghost" onClick={() => router.push("/")}>
          Dashboard
        </Button>
      </div>

      {/* Resume Preview */}
      {resume && (
        <Card elevated>
          <CardBody>
            <ResumePreview data={resume} />
          </CardBody>
        </Card>
      )}

      {/* Cover Letter */}
      {d.cover_letter && (
        <Card>
          <CardHeader>
            <p className="font-semibold text-[var(--color-text)]" style={{ fontSize: "var(--text-sm)" }}>
              Cover Letter
            </p>
          </CardHeader>
          <CardBody>
            <p
              className="text-[var(--color-text)] leading-relaxed whitespace-pre-line"
              style={{ fontSize: "var(--text-sm)" }}
            >
              {d.cover_letter}
            </p>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
