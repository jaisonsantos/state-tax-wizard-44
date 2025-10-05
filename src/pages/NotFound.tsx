import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { FadeIn, LoadingOverlay, EmptyState } from "@/components/patterns";
import { Compass } from "lucide-react";

const NotFound = () => {
  const location = useLocation();
  const [searching, setSearching] = useState(true);

  useEffect(() => {
    console.error("404 Error: User attempted to access non-existent route:", location.pathname);
  }, [location.pathname]);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearching(false), 350);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-muted/40 to-primary-muted/40 px-6">
      <LoadingOverlay visible={searching} message="Searching for that page..." tone="muted" />
      <FadeIn className="w-full max-w-lg">
        <EmptyState
          icon={Compass}
          title="Page not found"
          description="The route you tried to open doesn’t exist. Return to the dashboard to continue exploring the demo."
          tone="bordered"
          action={
            <Button asChild size="lg" className="hover-lift">
              <a href="/">Back to dashboard</a>
            </Button>
          }
        />
      </FadeIn>
    </div>
  );
};

export default NotFound;
