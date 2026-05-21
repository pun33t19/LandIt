import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function scoreColor(score: number) {
  if (score >= 80) return "text-[var(--color-success)]";
  if (score >= 60) return "text-[var(--color-gold)]";
  return "text-[var(--color-error)]";
}

export function scoreBg(score: number) {
  if (score >= 80) return "bg-[var(--color-success-highlight)]";
  if (score >= 60) return "bg-[var(--color-gold-highlight)]";
  return "bg-[var(--color-error-highlight)]";
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
