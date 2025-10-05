import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { FadeIn } from "@/components/ui/fade-in";
import { LoadingOverlay } from "@/components/ui/loading-overlay";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/hooks/use-toast";
import {
  type AnalyticsMetricCard,
  type AnalyticsOverviewResponse,
  type AnalyticsRecentDecision,
  API_DOCS_URL,
  apiClient,
} from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  ExternalLink,
  Loader2,
  Minus,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Fragment, useEffect, useMemo, useState } from "react";

function useCountUp(target?: number | null, duration = 800) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (target === undefined || target === null) {
      return;
    }

    let frame = 0;
    const start = performance.now();

    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const nextValue = target * progress;
      setValue(nextValue);
      if (progress < 1) {
        frame = requestAnimationFrame(animate);
      }
    };

    setValue(0);
    frame = requestAnimationFrame(animate);

    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  return target === undefined || target === null ? 0 : value;
}

function formatMetricValue(card: AnalyticsMetricCard, current: number) {
  if (!Number.isFinite(current)) {
    return card.formatted_value;
  }

  switch (card.unit) {
    case "currency_cents":
      return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(current / 100);
    case "currency":
    case "currency_usd":
      return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(current);
    case "percentage":
      return `${current.toFixed(1)}%`;
    case "count":
    default:
      return Math.round(current).toLocaleString();
  }
}

function CountUpValue({ card }: { card: AnalyticsMetricCard }) {
  const animated = useCountUp(card.value);
  return <div className="text-3xl font-semibold tracking-tight count-up">{formatMetricValue(card, animated)}</div>;
}

function trendIconFor(card: AnalyticsMetricCard) {
  if (card.trend === "up") return TrendingUp;
  if (card.trend === "down") return TrendingDown;
  return Minus;
}

function trendColorFor(card: AnalyticsMetricCard) {
  if (card.trend === "up") return "text-success";
  if (card.trend === "down") return "text-destructive";
  return "text-muted-foreground";
}

function formatAmount(amountCents?: number | null): string {
  if (amountCents === undefined || amountCents === null) {
    return "--";
  }
  return `$${(amountCents / 100).toFixed(2)}`;
}

export default function Dashboard() {
  const { selectedStoreId: storeId } = useAuth();
  const { toast } = useToast();
  const [decisions, setDecisions] = useState<AnalyticsRecentDecision[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  const {
    data: analytics,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["analytics-overview", storeId],
    queryFn: async (): Promise<AnalyticsOverviewResponse> => {
      if (!storeId) {
        throw new Error("store not selected");
      }
      return apiClient.getAnalyticsOverview(storeId, 6);
    },
    enabled: !!storeId,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (analytics) {
      setDecisions(analytics.recent_decisions.items);
      setNextCursor(analytics.recent_decisions.next_cursor);
    } else {
      setDecisions([]);
      setNextCursor(null);
    }
  }, [analytics]);

  useEffect(() => {
    if (isError) {
      toast({
        title: "Analytics unavailable",
        description: "The analytics service is temporarily unreachable. Try again shortly.",
        variant: "destructive",
      });
    }
  }, [isError, toast]);

  const handleLoadMore = async () => {
    if (!storeId || !nextCursor) return;
    setLoadingMore(true);
    try {
      const response = await apiClient.getAnalyticsOverview(storeId, 6, nextCursor);
      setDecisions((current) => [...current, ...response.recent_decisions.items]);
      setNextCursor(response.recent_decisions.next_cursor);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to load additional decisions";
      toast({ title: "Load more failed", description: message, variant: "destructive" });
    } finally {
      setLoadingMore(false);
    }
  };

  const cards = useMemo(() => analytics?.metric_cards ?? [], [analytics]);
  const counters = analytics?.counters;

  return (
    <div className="space-y-8">
      <FadeIn variant="fade" className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Monitor real-time fee performance, absorption, and export activity for your demo stores.
          </p>
        </div>
        <Button asChild variant="link" className="h-auto px-0 text-sm font-medium text-primary hover:text-primary/80">
          <a
            href={`${API_DOCS_URL}#/Analytics/get_v1_analytics_overview_api_v1_analytics_overview_get`}
            target="_blank"
            rel="noreferrer"
          >
            Analytics reference
            <ExternalLink className="ml-1 h-4 w-4" />
          </a>
        </Button>
      </FadeIn>

      {!storeId && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Select a store</AlertTitle>
          <AlertDescription>
            Choose a store from the header selector to hydrate live analytics.
          </AlertDescription>
        </Alert>
      )}

      {storeId && isLoading && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Card key={index} data-testid="analytics-card" className="border-none bg-muted/40">
              <CardHeader className="space-y-3">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-6 w-24" />
              </CardHeader>
              <CardContent className="space-y-4">
                <Skeleton className="h-8 w-32" />
                <Skeleton className="h-3 w-36" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {storeId && !isLoading && cards.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {cards.map((card, index) => {
            const Icon = trendIconFor(card);
            const trendColor = trendColorFor(card);
            const deltaPct = `${(card.delta_percentage * 100).toFixed(1)}%`;

            return (
              <FadeIn key={card.id} delay={index * 0.05}>
                <Card data-testid="analytics-card" className="hover-lift border-none bg-gradient-to-br from-background via-background to-muted/40">
                  <CardHeader className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <CardTitle className="flex items-center gap-2 text-sm font-medium">
                        {card.title}
                        {card.jurisdiction && <Badge variant="secondary">{card.jurisdiction}</Badge>}
                      </CardTitle>
                      <Icon className={`h-4 w-4 ${trendColor}`} />
                    </div>
                    {card.insight && <CardDescription>{card.insight}</CardDescription>}
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <CountUpValue card={card} />
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <span className={trendColor}>{deltaPct}</span>
                      <span>vs previous window</span>
                    </div>
                  </CardContent>
                </Card>
              </FadeIn>
            );
          })}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <FadeIn className="relative">
          <Card className="h-full overflow-hidden border-none bg-background shadow-sm">
            {loadingMore && (
              <LoadingOverlay message="Fetching more activity" transparent className="rounded-2xl" />
            )}
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                Recent Fee Decisions
              </CardTitle>
              <CardDescription>
                Live feed of audit events powering the analytics snapshot.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!storeId && (
                <p className="text-sm text-muted-foreground">
                  Select a store to view recent fee decisions.
                </p>
              )}
              {storeId && decisions.length === 0 && !isLoading && (
                <EmptyState
                  title="No activity yet"
                  description="Apply demo fees from the Settings playground to populate this list."
                  className="border-none bg-muted/40"
                  icon={<AlertCircle className="h-5 w-5" />}
                />
              )}
              {storeId && decisions.length > 0 && (
                <div className="space-y-3">
                  {decisions.map((event, index) => (
                    <FadeIn
                      key={event.id}
                      delay={index * 0.04}
                      variant="fade"
                      className="rounded-xl border bg-muted/30 p-3"
                    >
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex items-center gap-3">
                          <Badge
                            variant={event.jurisdiction === "MN" ? "default" : "secondary"}
                            className={
                              event.jurisdiction === "MN"
                                ? "bg-minnesota text-minnesota-foreground"
                                : "bg-colorado text-colorado-foreground"
                            }
                          >
                            {event.jurisdiction ?? "--"}
                          </Badge>
                          <div>
                            <p className="text-sm font-medium">{event.order_id ?? "Unknown order"}</p>
                            <p className="text-xs text-muted-foreground">
                              {(event.reason_codes ?? []).join(", ") || event.outcome || "audit"}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-semibold text-foreground">{formatAmount(event.amount_cents)}</p>
                          <p className="text-xs text-muted-foreground">
                            {event.occurred_at ? new Date(event.occurred_at).toLocaleString() : "--"}
                          </p>
                        </div>
                      </div>
                    </FadeIn>
                  ))}
                </div>
              )}
              {storeId && nextCursor && (
                <Button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  variant="outline"
                  className="w-full transition-all hover-lift"
                >
                  {loadingMore ? (
                    <span className="flex items-center gap-2 text-sm">
                      <Loader2 className="h-4 w-4 animate-spin" /> Loading more activity
                    </span>
                  ) : (
                    "Load more activity"
                  )}
                </Button>
              )}
              {storeId && !nextCursor && decisions.length > 0 && (
                <p className="text-center text-xs text-muted-foreground">
                  End of activity feed
                </p>
              )}
            </CardContent>
          </Card>
        </FadeIn>

        <FadeIn variant="right" className="h-full">
          <Card className="h-full border-none bg-gradient-to-br from-background via-background to-muted/40">
            <CardHeader>
              <CardTitle>Prometheus Snapshot</CardTitle>
              <CardDescription>
                Counter values are captured without scraping `/metrics`.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {counters ? (
                <dl className="space-y-3 text-sm">
                  {["fees_applied_total", "fees_absorbed_total", "report_exports_total"].map((key) => (
                    <Fragment key={key}>
                      <div className="flex items-center justify-between rounded-lg bg-background/60 px-3 py-2">
                        <dt className="text-muted-foreground">
                          {key === "fees_applied_total" && "Fees applied (all jurisdictions)"}
                          {key === "fees_absorbed_total" && "Fees absorbed"}
                          {key === "report_exports_total" && "Report exports"}
                        </dt>
                        <dd className="text-right text-base font-semibold text-foreground">
                          {counters[key as keyof typeof counters].toLocaleString()}
                        </dd>
                      </div>
                    </Fragment>
                  ))}
                </dl>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Counters populate after the first analytics request for your store.
                </p>
              )}
              <Button asChild variant="outline" className="mt-4 w-full transition-all hover-lift">
                <a href="/api/files/docs/security/observability.md" target="_blank" rel="noreferrer">
                  Review observability catalog
                  <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </CardContent>
          </Card>
        </FadeIn>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <FadeIn>
          <Card className="border-none bg-background shadow-sm">
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>Frequently used navigation shortcuts.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button
                className="w-full justify-start transition-all hover-lift"
                variant="outline"
                onClick={() => void refetch()}
              >
                Refresh analytics snapshot
              </Button>
              <Button className="w-full justify-start transition-all hover-lift" variant="outline" asChild>
                <a href="/reports">Go to Reports</a>
              </Button>
              <Button className="w-full justify-start transition-all hover-lift" variant="outline" asChild>
                <a href="/logs">Inspect audit logs</a>
              </Button>
              <Button className="w-full justify-start transition-all hover-lift" variant="outline" asChild>
                <a href="/settings">Adjust fee settings</a>
              </Button>
            </CardContent>
          </Card>
        </FadeIn>

        <FadeIn variant="fade" className="h-full">
          <Alert className="h-full items-start border-none bg-gradient-to-br from-primary/5 via-background to-background">
            <AlertCircle className="h-4 w-4 text-primary" />
            <AlertTitle className="text-base font-semibold">Need deeper analysis?</AlertTitle>
            <AlertDescription>
              Pipe the analytics payload into your own dashboards or BI tooling via the documented JSON contract.
            </AlertDescription>
          </Alert>
        </FadeIn>
      </div>
    </div>
  );
}