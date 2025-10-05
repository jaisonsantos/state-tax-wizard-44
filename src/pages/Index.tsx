import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FadeIn, LoadingOverlay, EmptyState } from "@/components/patterns";
import { ArrowRight, Sparkles } from "lucide-react";

const Index = () => {
  const [hydrating, setHydrating] = useState(true);

  useEffect(() => {
    const timer = window.setTimeout(() => setHydrating(false), 300);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-primary/5 to-primary-muted/40 px-6 py-16">
      <LoadingOverlay visible={hydrating} message="Preparing workspace..." tone="muted" />
      <div className="relative z-10 flex w-full max-w-4xl flex-col items-center space-y-8 text-center">
        <FadeIn className="space-y-4">
          <Badge variant="secondary" className="mx-auto flex items-center gap-2 px-4 py-1 text-sm hover-lift">
            <Sparkles className="h-4 w-4 text-primary" />
            Delivery Fee Router Sandbox
          </Badge>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Launch compliant delivery fees in minutes
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
            Explore analytics, audit trails, and automated reports for Minnesota and Colorado delivery fees. Connect a demo store to experience the platform end-to-end.
          </p>
        </FadeIn>

        <FadeIn delay={0.15} className="flex flex-col gap-3 sm:flex-row">
          <Button asChild size="lg" className="hover-lift">
            <a href="/onboarding">
              Start onboarding
              <ArrowRight className="ml-2 h-4 w-4" />
            </a>
          </Button>
          <Button asChild variant="outline" size="lg" className="hover-lift">
            <a href="/reports">View compliance reports</a>
          </Button>
        </FadeIn>

        <FadeIn delay={0.25} className="w-full max-w-xl">
          <EmptyState
            icon={Sparkles}
            title="No store connected yet"
            description="Create a demo storefront from onboarding to populate analytics, logs, and billing data."
            tone="bordered"
            action={
              <Button asChild variant="secondary" className="hover-lift">
                <a href="/onboarding">Connect store</a>
              </Button>
            }
          />
        </FadeIn>
      </div>
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top,_hsl(var(--primary)/0.12),_transparent_45%)]" />
    </div>
  );
};

export default Index;
