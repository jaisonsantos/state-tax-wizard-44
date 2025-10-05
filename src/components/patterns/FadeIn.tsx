import { ElementType, HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type FadeDirection = "up" | "down" | "left" | "right" | "none";

const directionMap: Record<FadeDirection, string> = {
  up: "animate-in fade-in-0 slide-in-from-bottom-4",
  down: "animate-in fade-in-0 slide-in-from-top-4",
  left: "animate-in fade-in-0 slide-in-from-left-4",
  right: "animate-in fade-in-0 slide-in-from-right-4",
  none: "animate-in fade-in-0",
};

export interface FadeInProps extends HTMLAttributes<HTMLElement> {
  as?: ElementType;
  delay?: number;
  duration?: number;
  from?: FadeDirection;
}

export function FadeIn({
  as: Component = "div",
  delay = 0,
  from = "up",
  duration = 0.5,
  className,
  style,
  children,
  ...props
}: FadeInProps) {
  const directionClass = directionMap[from] ?? directionMap.up;

  return (
    <Component
      className={cn(directionClass, className)}
      style={{
        animationDelay: delay ? `${delay}s` : undefined,
        animationDuration: `${duration}s`,
        animationTimingFunction: "cubic-bezier(0.33, 1, 0.68, 1)",
        animationFillMode: "forwards",
        ...style,
      }}
      {...props}
    >
      {children}
    </Component>
  );
}
