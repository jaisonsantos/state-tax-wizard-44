import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
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
import { useEffect, useMemo, useState } from "react";

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
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor real-time fee performance, absorption, and export activity for your demo stores.
          </p>
        </div>
        <Button
          asChild
          variant="link"
          className="px-0 h-auto text-sm"
        >
          <a
            href={`${API_DOCS_URL}#/Analytics/get_v1_analytics_overview_api_v1_analytics_overview_get`}
            target="_blank"
            rel="noreferrer"
          >
            Analytics reference
            <ExternalLink className="ml-1 h-4 w-4" />
          </a>
        </Button>
      </div>

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
            <Card key={index} data-testid="analytics-card">
              <CardHeader className="space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-6 w-20" />
              </CardHeader>
              <CardContent className="space-y-2">
                <Skeleton className="h-8 w-24" />
                <Skeleton className="h-3 w-32" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {storeId && !isLoading && cards.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {cards.map((card) => {
            const Icon = trendIconFor(card);
            const trendColor = trendColorFor(card);
            const deltaPct = `${(card.delta_percentage * 100).toFixed(1)}%`;

            return (
              <Card key={card.id} data-testid="analytics-card">
                <CardHeader className="space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      {card.title}
                      {card.jurisdiction && (
                        <Badge variant="secondary">{card.jurisdiction}</Badge>
                      )}
                    </CardTitle>
                    <Icon className={`h-4 w-4 ${trendColor}`} />
                  </div>
                  {card.insight && (
                    <CardDescription>{card.insight}</CardDescription>
                  )}
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="text-2xl font-bold">{card.formatted_value}</div>
                  <div className="flex items-center gap-1 text-xs">
                    <span className={trendColor}>{deltaPct}</span>
                    <span className="text-muted-foreground">vs previous window</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Recent Fee Decisions
            </CardTitle>
            <CardDescription>
              Live feed of audit events powering the analytics snapshot.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {!storeId && (
              <p className="text-sm text-muted-foreground">
                Select a store to view recent fee decisions.
              </p>
            )}
            {storeId && decisions.length === 0 && !isLoading && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>No activity yet</AlertTitle>
                <AlertDescription>
                  Apply demo fees from the Settings playground to populate this list.
                </AlertDescription>
              </Alert>
            )}
            {storeId && decisions.length > 0 && (
              <div className="space-y-3">
                {decisions.map((event) => (
                  <div
                    key={event.id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
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
                      <p className="text-sm font-medium">{formatAmount(event.amount_cents)}</p>
                      <p className="text-xs text-muted-foreground">
                        {event.occurred_at ? new Date(event.occurred_at).toLocaleString() : "--"}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {storeId && nextCursor && (
              <Button
                onClick={handleLoadMore}
                disabled={loadingMore}
                variant="outline"
                className="w-full"
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

        <Card>
          <CardHeader>
            <CardTitle>Prometheus Snapshot</CardTitle>
            <CardDescription>
              Counter values are captured without scraping `/metrics`.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {counters ? (
              <dl className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Fees applied (all jurisdictions)</dt>
                  <dd className="font-medium">{counters.fees_applied_total.toLocaleString()}</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Fees absorbed</dt>
                  <dd className="font-medium">{counters.fees_absorbed_total.toLocaleString()}</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-muted-foreground">Report exports</dt>
                  <dd className="font-medium">{counters.report_exports_total.toLocaleString()}</dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-muted-foreground">
                Counters populate after the first analytics request for your store.
              </p>
            )}
            <Button
              asChild
              variant="outline"
              className="mt-4 w-full"
            >
              <a href="/api/files/docs/observability.md" target="_blank" rel="noreferrer">
                Review observability catalog
                <ExternalLink className="ml-2 h-4 w-4" />
              </a>
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Frequently used navigation shortcuts.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button className="w-full justify-start" variant="outline" onClick={() => void refetch()}>
              Refresh analytics snapshot
            </Button>
            <Button className="w-full justify-start" variant="outline" asChild>
              <a href="/reports">Go to Reports</a>
            </Button>
            <Button className="w-full justify-start" variant="outline" asChild>
              <a href="/logs">Inspect audit logs</a>
            </Button>
            <Button className="w-full justify-start" variant="outline" asChild>
              <a href="/settings">Adjust fee settings</a>
            </Button>
          </CardContent>
        </Card>

        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Need deeper analysis?</AlertTitle>
          <AlertDescription>
            Pipe the analytics payload into your own dashboards or BI tooling via the documented JSON contract.
          </AlertDescription>
        </Alert>
      </div>
    </div>
  );
}