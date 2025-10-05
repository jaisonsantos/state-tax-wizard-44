import { HTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface LoadingOverlayProps extends HTMLAttributes<HTMLDivElement> {
  visible?: boolean;
  message?: string;
  tone?: "default" | "muted";
}

export function LoadingOverlay({
  visible = false,
  message = "Loading...",
  tone = "default",
  className,
  children,
  ...props
}: LoadingOverlayProps) {
  if (!visible) {
    return null;
  }

  const toneClass =
    tone === "muted"
      ? "bg-background/85"
      : "bg-gradient-to-br from-primary/10 via-primary/5 to-transparent";

  return (
    <div
      className={cn(
        "absolute inset-0 z-30 flex flex-col items-center justify-center rounded-lg backdrop-blur-sm transition-opacity",
        toneClass,
        className,
      )}
      {...props}
    >
      <div className="flex items-center gap-3 rounded-full border border-border/80 bg-background/90 px-5 py-2 shadow-lg">
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
        <span className="text-sm font-medium text-muted-foreground">{message}</span>
      </div>
      {children}
    </div>
  );
}
