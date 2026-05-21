import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export function Spinner({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center justify-center p-12", className)}>
      <Loader2 size={24} className="animate-spin text-[var(--color-primary)]" />
    </div>
  );
}
