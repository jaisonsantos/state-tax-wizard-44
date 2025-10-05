import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FadeIn } from "@/components/ui/fade-in";
import { BarChart3, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { toast } = useToast();
  const { refresh } = useAuth();

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 4000);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [error]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await apiClient.login({ email, password });
      await refresh();

      toast({
        title: "Login successful",
        description: "Welcome to DeliveryFee Router",
      });

      setError(null);
      navigate("/dashboard");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Please check your credentials";
      toast({
        title: "Login failed",
        description: message,
        variant: "destructive",
      });
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-br from-primary/5 via-background to-secondary/60">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(59,130,246,0.18),transparent_55%)]" />
      <div className="relative z-10 flex min-h-screen items-center justify-center p-4">
        <FadeIn className="w-full max-w-md">
          <Card className="border-none shadow-xl">
            <CardHeader className="space-y-3 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/90 text-primary-foreground shadow-lg shadow-primary/20 transition-transform duration-300">
                <BarChart3 className={`h-7 w-7 ${loading ? "animate-pulse" : ""}`} />
              </div>
              <div className="space-y-1">
                <CardTitle className="text-3xl font-semibold tracking-tight">DeliveryFee Router</CardTitle>
                <CardDescription>
                  Automated compliance for MN &amp; CO delivery fees
                </CardDescription>
              </div>
            </CardHeader>

            <CardContent className="space-y-6">
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    required
                    className="transition-all focus-visible:ring-2 focus-visible:ring-offset-2"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    required
                    className="transition-all focus-visible:ring-2 focus-visible:ring-offset-2"
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full transition-all duration-200 hover:shadow-lg"
                  disabled={loading}
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" /> Signing in
                    </span>
                  ) : (
                    "Sign In"
                  )}
                </Button>

                <div className="text-center">
                  <Button variant="link" className="text-sm text-muted-foreground transition-colors hover:text-primary">
                    Forgot password?
                  </Button>
                </div>
              </form>

              {error && (
                <FadeIn
                  variant="fade"
                  className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive"
                  once={false}
                >
                  {error}
                </FadeIn>
              )}
            </CardContent>
          </Card>
        </FadeIn>
      </div>
    </div>
  );
}