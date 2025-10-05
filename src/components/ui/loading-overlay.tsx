import * as React from "react";
import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export interface LoadingOverlayProps extends React.HTMLAttributes<HTMLDivElement> {
  message?: string;
  fullscreen?: boolean;
  transparent?: boolean;
}

export const LoadingOverlay = React.forwardRef<HTMLDivElement, LoadingOverlayProps>(
  ({ className, message = "Loading...", fullscreen = false, transparent = false, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "inset-0 flex flex-col items-center justify-center gap-3",
          fullscreen ? "fixed z-50" : "absolute z-20",
          transparent ? "bg-background/60 backdrop-blur-sm" : "bg-muted/70 backdrop-blur",
          "pointer-events-auto",
          className,
        )}
        aria-live="polite"
        aria-busy="true"
        {...props}
      >
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        {message ? <span className="text-sm font-medium text-muted-foreground">{message}</span> : null}
      </div>
    );
  },
);

LoadingOverlay.displayName = "LoadingOverlay";
