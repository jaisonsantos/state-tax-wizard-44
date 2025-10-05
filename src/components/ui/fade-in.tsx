import * as React from "react";

import { cn } from "@/lib/utils";

type FadeVariant = "fade" | "up" | "right";

export interface FadeInProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: FadeVariant;
  delay?: number;
  once?: boolean;
}

export const FadeIn = React.forwardRef<HTMLDivElement, FadeInProps>(
  ({ className, style, children, variant = "up", delay = 0, once = true, ...props }, ref) => {
    const localRef = React.useRef<HTMLDivElement | null>(null);
    const [isVisible, setIsVisible] = React.useState(false);

    const setRefs = React.useCallback(
      (node: HTMLDivElement | null) => {
        localRef.current = node;
        if (typeof ref === "function") {
          ref(node);
        } else if (ref) {
          (ref as React.MutableRefObject<HTMLDivElement | null>).current = node;
        }
      },
      [ref],
    );

    React.useEffect(() => {
      const element = localRef.current;
      if (!element) {
        return;
      }

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              setIsVisible(true);
              if (once) {
                observer.disconnect();
              }
            } else if (!once) {
              setIsVisible(false);
            }
          });
        },
        { threshold: 0.15 },
      );

      observer.observe(element);

      return () => {
        observer.disconnect();
      };
    }, [once]);

    const animationClass = React.useMemo(() => {
      switch (variant) {
        case "fade":
          return "animate-fade-in";
        case "right":
          return "animate-slide-in-right";
        default:
          return "animate-fade-up";
      }
    }, [variant]);

    const initialTransform = React.useMemo(() => {
      switch (variant) {
        case "fade":
          return "";
        case "right":
          return "-translate-x-3";
        default:
          return "translate-y-3";
      }
    }, [variant]);

    return (
      <div
        ref={setRefs}
        className={cn(
          "will-change-transform will-change-opacity",
          isVisible ? animationClass : "opacity-0",
          !isVisible && initialTransform,
          className,
        )}
        style={{ animationDelay: `${delay}s`, ...style }}
        {...props}
      >
        {children}
      </div>
    );
  },
);

FadeIn.displayName = "FadeIn";
