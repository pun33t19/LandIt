const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    console.error(`API ${res.status} on ${path}:`, err);

    // FastAPI returns detail as array of validation errors
    const detail = err.detail;
    if (Array.isArray(detail)) {
      const msg = detail.map((d: any) =>
        `${d.loc?.join(".")} — ${d.msg}`
      ).join(", ");
      throw new Error(msg);
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}

export async function uploadResumeFile(file: File) {
    console.log("6️⃣ uploadResumeFile — sending to API");
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/resume/upload`, { method: "POST", body: form });

    console.log("7️⃣ API responded with status:", res.status);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    console.error(`API ${res.status} on /api/resume/upload:`, err);
    const detail = err.detail;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((d: any) => `${d.loc?.join(".")} — ${d.msg}`).join(", "));
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  const json = await res.json();
  console.log("8️⃣ Parsed response JSON:", json);
  return json;
}

export async function getResume(resumeId: string) {
  return request(`/api/resume/${resumeId}`);
}

export async function startOptimise(resumeId: string, resumeData: Record<string, unknown>) {
  return request(`/api/resume/optimize/start`, {
    method: "POST",
    body: JSON.stringify(resumeData),  // send full resume object
  });
}

export async function getOptimiseStatus(sessionId: string) {
  return request(`/api/resume/optimize/${sessionId}`);
}

export async function reviewOptimise(
  sessionId: string,
  action: "approve" | "reject",
  editedResume?: Record<string, unknown>
) {
  return request(`/api/resume/optimize/review?session_id=${sessionId}`, {
    method: "POST",
    body: JSON.stringify({
      action: action,
      edited_resume: editedResume ?? {},
    }),
  });
}

export async function searchJobs(params: {
  resume?: Record<string, unknown>;
  query?: string;
  location?: string;
  experience_level?: string;
  num_results?: number;
}) {
   const body = {
    resume: params.resume ?? {},
    filters: {
      query: params.query ?? "",
      location: params.location ?? "remote",   // ← log this
      country: "IN",
      employment_type: "fulltime",
      work_mode: "any",
      salary_min: 0,
      salary_max: 0,
      experience_level: params.experience_level ?? "entry",
      tech_stack: [],
      date_posted: 7,
      num_results: params.num_results ?? 20,
    },
  };

  console.log("searchJobs sending: ", JSON.stringify(body, null, 2));

  return request(`/api/jobs/search`, {
    method: "POST",
    body: JSON.stringify(body)
  });
}

export async function getJob(jobId: string) {
  return request(`/api/jobs/${jobId}`);
}

export async function startTailoring(
  resume: Record<string, unknown>,
  job: Record<string, unknown>,
  options?: {
    mirror_keywords?: boolean;
    reorder_skills?: boolean;
    rewrite_bullets?: boolean;
    generate_cover_letter?: boolean;
  }
) {
  return request(`/api/tailor/resume`, {
    method: "POST",
    body: JSON.stringify({
      resume,
      job,
      options: {
        mirror_keywords: true,
        reorder_skills: true,
        rewrite_bullets: true,
        generate_cover_letter: false,
        ...options,
      },
    }),
  });
}

export async function getTailorStatus(sessionId: string) {
  return request(`/api/tailor/session/${sessionId}`);
}

export async function reviewTailoring(sessionId: string, action: "approve" | "reject") {
  return request(`/api/tailor/review?session_id=${sessionId}&action=${action}`, {
    method: "POST",
  });
}

export async function exportPDF(sessionId: string): Promise<Blob> {
  const res = await fetch(`${BASE}/api/export/pdf?session_id=${sessionId}`);
  if (!res.ok) throw new Error("Export failed");
  return res.blob();
}
