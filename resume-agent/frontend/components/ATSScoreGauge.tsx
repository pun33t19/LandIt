"use client";
import { cn, scoreColor } from "@/lib/utils";

interface ATSScoreGaugeProps {
  score: number;
  label?: string;
  size?: "sm" | "lg";
}

export function ATSScoreGauge({ score, label = "ATS Score", size = "lg" }: ATSScoreGaugeProps) {
  const radius = size === "lg" ? 52 : 32;
  const stroke = size === "lg" ? 8 : 5;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const dim = (radius + stroke) * 2;

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: dim, height: dim }}>
        <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`}>
          <circle
            cx={dim / 2} cy={dim / 2} r={radius} fill="none"
            stroke="var(--color-surface-offset)" strokeWidth={stroke}
          />
          <circle
            cx={dim / 2} cy={dim / 2} r={radius} fill="none"
            stroke="var(--color-primary)" strokeWidth={stroke}
            strokeDasharray={circumference} strokeDashoffset={offset}
            strokeLinecap="round"
            transform={`rotate(-90 ${dim / 2} ${dim / 2})`}
            style={{ transition: "stroke-dashoffset 0.8s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn(
            "font-bold",
            size === "lg" ? "text-2xl" : "text-base",
            scoreColor(score)
          )}>
            {Math.round(score)}
          </span>
        </div>
      </div>
      <span className="text-[length:var(--text-xs)] text-[var(--color-text-muted)] uppercase tracking-wide">
        {label}
      </span>
    </div>
  );
}
