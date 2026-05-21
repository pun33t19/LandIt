import { cn } from "@/lib/utils";

interface BadgeProps {
  variant?: "default" | "success" | "warning" | "error" | "primary";
  children: React.ReactNode;
  className?: string;
}

const variants = {
  default: "bg-[var(--color-surface-offset)] text-[var(--color-text-muted)]",
  success: "bg-[var(--color-success-highlight)] text-[var(--color-success)]",
  warning: "bg-[var(--color-warning-highlight)] text-[var(--color-warning)]",
  error:   "bg-[var(--color-error-highlight)] text-[var(--color-error)]",
  primary: "bg-[var(--color-primary-highlight)] text-[var(--color-primary)]",
};

export function Badge({ variant = "default", children, className }: BadgeProps) {
  return (
    <span className={cn(
      "inline-flex items-center px-2 py-0.5 rounded-[var(--radius-full)]",
      "text-[length:var(--text-xs)] font-medium",
      variants[variant], className
    )}>
      {children}
    </span>
  );
}
