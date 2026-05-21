import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ResumeStore {
  resumeId: string | null;
  resumeData: Record<string, unknown> | null;
  optimiseSessionId: string | null;
  tailorSessionId: string | null;
  selectedJobId: string | null;
  setResumeId: (id: string) => void;
  setResumeData: (data: Record<string, unknown>) => void;
  setOptimiseSessionId: (id: string) => void;
  setTailorSessionId: (id: string) => void;
  setSelectedJobId: (id: string) => void;
  reset: () => void;
}

export const useResumeStore = create<ResumeStore>()(
  persist(
    (set) => ({
      resumeId: null,
      resumeData: null,
      optimiseSessionId: null,
      tailorSessionId: null,
      selectedJobId: null,
      setResumeId: (id) => set({ resumeId: id }),
      setResumeData: (data) => set({ resumeData: data }),
      setOptimiseSessionId: (id) => set({ optimiseSessionId: id }),
      setTailorSessionId: (id) => set({ tailorSessionId: id }),
      setSelectedJobId: (id) => set({ selectedJobId: id }),
      reset: () =>
        set({
          resumeId: null, resumeData: null,
          optimiseSessionId: null, tailorSessionId: null, selectedJobId: null,
        }),
    }),
    {
      name: "resume-agent-store", // key in sessionStorage
      storage: {
        getItem: (name) => {
          const str = sessionStorage.getItem(name);
          return str ? JSON.parse(str) : null;
        },
        setItem: (name, value) => {
          sessionStorage.setItem(name, JSON.stringify(value));
        },
        removeItem: (name) => sessionStorage.removeItem(name),
      },
    }
  )
);