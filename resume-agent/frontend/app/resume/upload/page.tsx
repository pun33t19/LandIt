"use client";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ResumePreview } from "@/components/ResumePreview";
import { Spinner } from "@/components/ui/Spinner";
import { useResumeStore } from "@/lib/store";
import { uploadResume, type UploadResult } from "@/lib/resumeUpload";
import { clearCache, getCacheCount } from "@/lib/resumeCache";
import { FileUp, CheckCircle2, AlertCircle, Zap, Trash2 } from "lucide-react";

// ─── UI-only helpers ──────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function UploadPage() {
  const router = useRouter();
  const { setResumeId, setResumeData, resumeId } = useResumeStore();

  const [dragging, setDragging]     = useState(false);
  const [uploading, setUploading]   = useState(false);
  const [result, setResult]         = useState<UploadResult | null>(null);
  const [error, setError]           = useState<string | null>(null);
  const [cacheCount, setCacheCount] = useState(() => getCacheCount());

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please upload a PDF file.");
      return;
    }
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const uploadResult = await uploadResume(file); // ← single call, no fetch here
      setResumeId(uploadResult.resumeId);
      setResumeData(uploadResult.resumeData);
      setResult(uploadResult);
      setCacheCount(getCacheCount());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
      console.error("Upload error:", e);
    } finally {
      setUploading(false);
    }
  }, [setResumeId, setResumeData]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  const handleClearCache = () => {
    clearCache();
    setCacheCount(0);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1
            className="text-[var(--color-text)]"
            style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)" }}
          >
            Upload Your Resume
          </h1>
          <p className="text-[var(--color-text-muted)] mt-1">
            Upload a PDF — we&apos;ll parse it into structured data instantly.
          </p>
        </div>

        {cacheCount > 0 && !result && (
          <div className="flex items-center gap-2">
            <span
              className="text-[var(--color-text-muted)]"
              style={{ fontSize: "var(--text-xs)" }}
            >
              {cacheCount} resume{cacheCount !== 1 ? "s" : ""} cached
            </span>
            <button
              onClick={handleClearCache}
              className="flex items-center gap-1 text-[var(--color-error)] hover:text-[var(--color-error-hover)] transition-colors"
              style={{ fontSize: "var(--text-xs)" }}
              title="Clear all cached resumes"
            >
              <Trash2 size={12} /> Clear
            </button>
          </div>
        )}
      </div>

      {/* Upload Zone */}
      {!result && (
        <Card>
          <CardBody>
            <label
              className={[
                "flex flex-col items-center justify-center gap-4 p-16",
                "rounded-[var(--radius-lg)] border-2 border-dashed cursor-pointer transition-colors",
                dragging
                  ? "border-[var(--color-primary)] bg-[var(--color-primary-highlight)]"
                  : "border-[var(--color-border)] hover:border-[var(--color-primary)] hover:bg-[var(--color-surface-offset)]",
              ].join(" ")}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
            >
              {uploading ? (
                <div className="flex flex-col items-center gap-3">
                  <Spinner className="p-0" />
                  <p
                    className="text-[var(--color-text-muted)]"
                    style={{ fontSize: "var(--text-sm)" }}
                  >
                    Uploading and parsing…
                  </p>
                </div>
              ) : (
                <>
                  <FileUp size={32} className="text-[var(--color-primary)]" />
                  <div className="text-center">
                    <p className="font-medium text-[var(--color-text)]">
                      Drop your PDF here
                    </p>
                    <p
                      className="text-[var(--color-text-muted)] mt-1"
                      style={{ fontSize: "var(--text-sm)" }}
                    >
                      or click to browse
                    </p>
                    {cacheCount > 0 && (
                      <p
                        className="text-[var(--color-primary)] mt-2"
                        style={{ fontSize: "var(--text-xs)" }}
                      >
                        ⚡ Previously uploaded files load instantly
                      </p>
                    )}
                  </div>
                </>
              )}
              <input
                type="file" accept=".pdf" className="sr-only"
                onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
              />
            </label>

            {error && (
              <div className="mt-4 flex items-start gap-2 p-3 rounded-[var(--radius-lg)] bg-[var(--color-error-highlight)]">
                <AlertCircle size={16} className="text-[var(--color-error)] mt-0.5 shrink-0" />
                <p className="text-[var(--color-error)]" style={{ fontSize: "var(--text-sm)" }}>
                  {error}
                </p>
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-4">

          {/* Status Banner */}
          <Card>
            <CardBody className="py-3">
              <div className="flex items-center gap-3">
                {result.fromCache
                  ? <Zap size={18} className="text-[var(--color-gold)] shrink-0" />
                  : <CheckCircle2 size={18} className="text-[var(--color-success)] shrink-0" />
                }
                <div className="flex-1 min-w-0">
                  <p
                    className="font-medium text-[var(--color-text)]"
                    style={{ fontSize: "var(--text-sm)" }}
                  >
                    {result.fromCache ? "Loaded from cache" : "Resume parsed successfully"}
                  </p>
                  <p
                    className="text-[var(--color-text-muted)] truncate"
                    style={{ fontSize: "var(--text-xs)" }}
                  >
                    {result.entry.fileName}
                    {" · "}
                    {formatBytes(result.entry.fileSize)}
                    {result.fromCache && ` · Cached ${formatDate(result.entry.cachedAt)}`}
                  </p>
                </div>
                <Button size="sm" variant="ghost" onClick={handleReset}>
                  Re-upload
                </Button>
              </div>
            </CardBody>
          </Card>

          {/* Preview */}
          <Card elevated>
            <CardBody>
              <ResumePreview data={result.resumeData as any} />
            </CardBody>
          </Card>

          {/* Actions */}
          <div className="flex gap-3 justify-end">
            <Button variant="secondary" onClick={handleReset}>
              Re-upload
            </Button>
            <Button
              onClick={() => router.push(`/resume/${resumeId || "default"}/optimize`)}
            >
              Optimise Resume →
            </Button>
          </div>

        </div>
      )}
    </div>
  );
}