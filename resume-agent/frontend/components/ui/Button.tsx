import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

const variants = {
  primary:   "bg-[var(--color-primary)] text-[var(--color-text-inverse)] hover:bg-[var(--color-primary-hover)] shadow-sm",
  secondary: "bg-[var(--color-surface-offset)] text-[var(--color-text)] hover:bg-[var(--color-surface-dynamic)] border border-[var(--color-border)]",
  ghost:     "text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-offset)]",
  danger:    "bg-[var(--color-error-highlight)] text-[var(--color-error)] hover:bg-[var(--color-error)] hover:text-white",
};

const sizes = {
  sm: "px-3 py-1.5 text-[length:var(--text-xs)] rounded-[var(--radius-md)] gap-1.5",
  md: "px-4 py-2   text-[length:var(--text-sm)] rounded-[var(--radius-lg)] gap-2",
  lg: "px-6 py-3   text-[length:var(--text-base)] rounded-[var(--radius-lg)] gap-2",
};

export function Button({
  variant = "primary", size = "md", loading,
  className, children, disabled, ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center font-medium",
        "transition-all duration-[180ms] ease-out cursor-pointer",
        "disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]",
        variants[variant], sizes[size], className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 size={14} className="animate-spin shrink-0" />}
      {children}
    </button>
  );
}
