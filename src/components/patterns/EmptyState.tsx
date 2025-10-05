import { HTMLAttributes, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export interface EmptyStateProps extends HTMLAttributes<HTMLDivElement> {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
  tone?: "default" | "muted" | "bordered";
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  tone = "default",
  className,
  children,
  ...props
}: EmptyStateProps) {
  const toneClass = {
    default:
      "border border-dashed border-border/70 bg-gradient-to-br from-background via-primary/5 to-primary-muted/30",
    muted: "border border-dashed border-border/60 bg-muted/60",
    bordered: "border border-border/70 bg-background",
  }[tone];

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl px-8 py-10 text-center shadow-[var(--shadow-card)]",
        toneClass,
        className,
      )}
      {...props}
    >
      {Icon && (
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Icon className="h-6 w-6" />
        </div>
      )}
      <div className="space-y-1">
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {children}
      {action && <div className="mt-2 flex flex-col items-center gap-2 sm:flex-row">{action}</div>}
    </div>
  );
}
