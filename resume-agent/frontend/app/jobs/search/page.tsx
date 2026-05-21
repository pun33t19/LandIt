"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { JobCard } from "@/components/JobCard";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { useState, useRef } from "react";
import { searchJobs, startTailoring } from "@/lib/api";
import { useResumeStore } from "@/lib/store";
import { Search, SlidersHorizontal } from "lucide-react";

const EXP_LEVELS = ["entry", "mid", "senior", "lead"];

export default function JobSearchPage() {
  const router = useRouter();
  const { resumeData, setTailorSessionId } = useResumeStore();

  // Input state (what user types)
  const [query, setQuery]       = useState("");
  const [location, setLocation] = useState("remote");
  const [expLevel, setExpLevel] = useState("entry");

  // Submitted state (what was last searched) — primitives only
  const [submittedQuery,    setSubmittedQuery]    = useState("");
  const [submittedLocation, setSubmittedLocation] = useState("remote");
  const [submittedExpLevel, setSubmittedExpLevel] = useState("entry");
  const [searchCount,       setSearchCount]       = useState(0);

  const searchParamsRef = useRef({
  query: "",
  location: "remote",
  expLevel: "entry",
});

  const [tailoring, setTailoring] = useState<string | null>(null);

  // queryFn reads from ref, not from closed-over state
const { data, isLoading, isFetching } = useQuery({
  queryKey: ["jobs", submittedQuery, submittedLocation, submittedExpLevel, searchCount],
  queryFn: () => searchJobs({
    resume: (resumeData as Record<string, unknown>) ?? {},
    query: searchParamsRef.current.query,        // ← from ref, always fresh
    location: searchParamsRef.current.location,  // ← from ref, always fresh
    experience_level: searchParamsRef.current.expLevel, // ← from ref, always fresh
    num_results: 20,
  }),
  enabled: !!submittedQuery,
  staleTime: 0,
});

  const handleSubmit = (e: React.FormEvent) => {
  e.preventDefault();
  if (!query.trim()) return;

  // Update ref immediately (no closure delay)
  searchParamsRef.current = {
    query: query.trim(),
    location: location,
    expLevel: expLevel,
  };

  // Update state (triggers re-render + key change)
  setSubmittedQuery(query.trim());
  setSubmittedLocation(location);
  setSubmittedExpLevel(expLevel);
  setSearchCount((c) => c + 1);
  };

  const handleTailor = async (job: any) => {
    if (!resumeData) {
      router.push("/resume/upload");
      return;
    }
    setTailoring(job.id ?? job.job_id ?? job.title);
    try {
      const result = await startTailoring(
        resumeData as Record<string, unknown>,
        job,
      ) as any;
      setTailorSessionId(result.session_id);
      router.push(`/tailor/${result.session_id}/review`);
    } catch (e: unknown) {
      console.error("Tailor error:", e);
      alert(e instanceof Error ? e.message : "Tailoring failed — check console");
    } finally {
      setTailoring(null);
    }
  };

  const jobs =
    (data as any)?.jobs ??
    (data as any)?.results ??
    (data as any)?.data ??
    (Array.isArray(data) ? data : []);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-[var(--color-text)]"
          style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-xl)" }}>
          Find Jobs
        </h1>
        <p className="text-[var(--color-text-muted)] mt-1">
          Search jobs ranked by how well they match your resume.
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              type="text"
              placeholder="e.g. Backend Engineer, Python Developer"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ fontSize: "var(--text-sm)" }}
              className="w-full pl-9 pr-4 py-2.5 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent transition-all"
            />
          </div>
          <Button type="submit" loading={isFetching}>Search</Button>
        </div>

        <div className="flex items-center gap-3">
          <SlidersHorizontal size={14} className="text-[var(--color-text-muted)] shrink-0" />
          <input
            type="text"
            placeholder="Location (e.g. remote, Pune)"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            style={{ fontSize: "var(--text-sm)" }}
            className="flex-1 px-4 py-2 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] placeholder:text-[var(--color-text-faint)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition-all"
          />
          <select
            value={expLevel}
            onChange={(e) => setExpLevel(e.target.value)}
            style={{ fontSize: "var(--text-sm)" }}
            className="px-4 py-2 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] transition-all capitalize"
          >
            {EXP_LEVELS.map((l) => (
              <option key={l} value={l} className="capitalize">{l}</option>
            ))}
          </select>
        </div>
      </form>

      {/* Results */}
      {isLoading || isFetching ? (
        <Spinner />
      ) : jobs.length > 0 ? (
        <div className="space-y-3">
          <p className="text-[length:var(--text-xs)] text-[var(--color-text-muted)]">
            {jobs.length} job{jobs.length !== 1 ? "s" : ""} found
            {submittedLocation && ` in ${submittedLocation}`}
          </p>
          {jobs.map((job: any, idx: number) => (
            <JobCard
              key={job.id ?? job.job_id ?? idx}
              job={job}
              onSelect={handleTailor}
            />
          ))}
        </div>
      ) : submittedQuery ? (
        <div className="text-center py-16 text-[var(--color-text-muted)]">
          <Search size={32} className="mx-auto mb-3 text-[var(--color-text-faint)]" />
          <p className="font-medium">No jobs found</p>
          <p style={{ fontSize: "var(--text-sm)" }} className="mt-1">
            Try a different title, location or experience level
          </p>
        </div>
      ) : (
        <div className="text-center py-16 text-[var(--color-text-muted)]">
          <Search size={32} className="mx-auto mb-3 text-[var(--color-text-faint)]" />
          <p style={{ fontSize: "var(--text-sm)" }}>Enter a job title above to search</p>
        </div>
      )}

      {/* Tailoring overlay */}
      {tailoring && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-[var(--color-surface)] rounded-[var(--radius-xl)] p-8 shadow-[var(--shadow-lg)] flex flex-col items-center gap-3">
            <Spinner className="p-0" />
            <p className="text-[var(--color-text-muted)]" style={{ fontSize: "var(--text-sm)" }}>
              Starting tailoring process…
            </p>
          </div>
        </div>
      )}
    </div>
  );
}