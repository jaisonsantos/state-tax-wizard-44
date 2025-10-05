import * as React from "react";

import { cn } from "@/lib/utils";

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  subtle?: boolean;
}

export const EmptyState = React.forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ icon, title, description, action, className, subtle = false, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border/60 p-10 text-center",
          subtle ? "bg-muted/40" : "bg-background",
          "animate-fade-in",
          className,
        )}
        {...props}
      >
        {icon ? <div className="rounded-full bg-primary/10 p-3 text-primary">{icon}</div> : null}
        <div className="space-y-2">
          <h3 className="text-lg font-semibold text-foreground">{title}</h3>
          {description ? <p className="max-w-md text-sm text-muted-foreground">{description}</p> : null}
          {children}
        </div>
        {action ? <div className="mt-2 flex flex-wrap items-center justify-center gap-2">{action}</div> : null}
      </div>
    );
  },
);

EmptyState.displayName = "EmptyState";
