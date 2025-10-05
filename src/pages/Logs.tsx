import { useCallback, useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { FadeIn, EmptyState } from "@/components/patterns";
import { Activity, Search, Filter, Download, RefreshCw, Inbox } from "lucide-react";
import { apiClient, downloadBlob } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/context/AuthContext";

type AuditRow = {
  id: string;
  timestamp: string;
  orderId: string;
  jurisdiction: string;
  amount: string;
  reasonCode: string;
  deliveryMethod: string;
  status: string;
  absorbed: boolean;
};

const AUDIT_PAGE_SIZE = 20;

export default function Logs() {
  const [filterState, setFilterState] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [searchOrder, setSearchOrder] = useState("");
  const [auditLogs, setAuditLogs] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const { toast } = useToast();
  const { selectedStoreId: storeId } = useAuth();

  const fetchAuditLogs = useCallback(
    async (
      store_id: string,
      options: { cursor?: string | null; append?: boolean; page?: number } = {},
    ) => {
      const append = Boolean(options.append);
      const cursor = options.cursor ?? null;
      const requestedPage = options.page ?? 1;
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }
      try {
        const response = await apiClient.getAuditLogs(store_id, requestedPage, AUDIT_PAGE_SIZE, undefined, cursor ?? undefined);

        const transformedLogs: AuditRow[] = response.items.map((log) => {
          const firstLine = log.payload.lines?.[0];
          const amountCents = firstLine?.amount_cents ?? 0;
          const reasonCodes = firstLine?.reason_codes ?? [];
          const jurisdiction = firstLine?.jurisdiction ?? log.payload.jurisdiction ?? "--";

          return {
            id: log.id,
            timestamp: log.timestamp ? new Date(log.timestamp).toLocaleString() : "--",
            orderId: log.payload.order_id ? `${log.payload.order_id}` : "--",
            jurisdiction,
            amount: `$${(amountCents / 100).toFixed(2)}`,
            reasonCode: reasonCodes[0] || log.action.toUpperCase(),
            deliveryMethod: log.payload.delivery_method || "Unknown",
            status: log.payload.status || (log.action === "fee_apply" ? "applied" : "recorded"),
            absorbed: firstLine?.absorbed ?? log.payload.absorbed ?? false,
          };
        });

        setAuditLogs((previous) => (append ? [...previous, ...transformedLogs] : transformedLogs));
        const responseCursor = response.next_cursor ?? null;
        setNextCursor(responseCursor);
        const effectivePage = response.page ?? requestedPage;
        setCurrentPage(effectivePage);
        const totalRecords = response.total;
        const pageLimit = response.limit ?? AUDIT_PAGE_SIZE;
        const hasTotal =
          totalRecords !== null && totalRecords !== undefined &&
          response.page !== null && response.page !== undefined;
        const moreAvailable =
          Boolean(responseCursor) ||
          (hasTotal ? totalRecords > effectivePage * pageLimit : response.items.length === pageLimit);
        setHasMore(moreAvailable);
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to load audit logs",
          variant: "destructive",
        });
      } finally {
        if (append) {
          setLoadingMore(false);
        } else {
          setLoading(false);
        }
      }
    },
    [toast],
  );

  useEffect(() => {
    if (!storeId) {
      setAuditLogs([]);
      setNextCursor(null);
      setCurrentPage(1);
      setHasMore(false);
      return;
    }

    void fetchAuditLogs(storeId, { append: false, cursor: null, page: 1 });
  }, [storeId, fetchAuditLogs]);

  const handleRefresh = () => {
    if (storeId) {
      setCurrentPage(1);
      setHasMore(false);
      setNextCursor(null);
      void fetchAuditLogs(storeId, { append: false, cursor: null, page: 1 });
    } else {
      toast({
        title: "Select a store",
        description: "Choose a store to refresh audit logs.",
      });
    }
  };

  const handleLoadMore = () => {
    if (!storeId) {
      return;
    }
    if (nextCursor) {
      void fetchAuditLogs(storeId, { append: true, cursor: nextCursor, page: currentPage + 1 });
      return;
    }

    if (hasMore) {
      void fetchAuditLogs(storeId, { append: true, cursor: null, page: currentPage + 1 });
    }
  };

  const filteredLogs = useMemo(() => {
    return auditLogs.filter((log) => {
      const matchesState = filterState === "all" || log.jurisdiction === filterState;
      const matchesStatus = filterStatus === "all" || log.status === filterStatus;
      const matchesSearch =
        searchOrder === "" || log.orderId.toLowerCase().includes(searchOrder.toLowerCase());

      return matchesState && matchesStatus && matchesSearch;
    });
  }, [auditLogs, filterState, filterStatus, searchOrder]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "applied":
        return <Badge className="bg-success text-success-foreground">Applied</Badge>;
      case "reversed":
        return <Badge className="bg-destructive text-destructive-foreground">Reversed</Badge>;
      case "exempt":
        return <Badge variant="outline">Exempt</Badge>;
      case "not_applied":
        return <Badge variant="secondary">Not Applied</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getJurisdictionBadge = (jurisdiction: string) => {
    return (
      <Badge
        className={
          jurisdiction === "MN"
            ? "bg-minnesota text-minnesota-foreground"
            : "bg-colorado text-colorado-foreground"
        }
      >
        {jurisdiction}
      </Badge>
    );
  };

  const exportCsv = () => {
    if (auditLogs.length === 0) {
      toast({
        title: "Nothing to export",
        description: "No audit logs available",
      });
      return;
    }

    const header = [
      "timestamp",
      "orderId",
      "jurisdiction",
      "amount",
      "reasonCode",
      "deliveryMethod",
      "status",
      "absorbed",
    ];
    const rows = auditLogs.map((log) => [
      log.timestamp,
      log.orderId,
      log.jurisdiction,
      log.amount,
      log.reasonCode,
      log.deliveryMethod,
      log.status,
      log.absorbed ? "true" : "false",
    ]);

    const csvContent = [header, ...rows]
      .map((row) => row.map((value) => `"${value.replace(/"/g, '""')}"`).join(","))
      .join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    downloadBlob(blob, "audit-logs.csv");
  };

  return (
    <div className="space-y-6">
      <FadeIn className="surface-gradient border border-border/60 rounded-2xl p-6 shadow-[var(--shadow-card)]">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold">Logs &amp; Audit</h1>
            <p className="text-muted-foreground">
              {storeId
                ? "Monitor every delivery fee decision with granular context and outcomes."
                : "Select a store to review audit events."}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading || !storeId}>
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              {loading ? "Refreshing" : "Refresh"}
            </Button>
            <Button variant="secondary" size="sm" onClick={exportCsv} disabled={auditLogs.length === 0}>
              <Download className="mr-2 h-4 w-4" />
              Export CSV
            </Button>
          </div>
        </div>
      </FadeIn>

      {!storeId && (
        <FadeIn delay={0.1}>
          <EmptyState
            icon={Inbox}
            title="Choose a store to get started"
            description="Audit history becomes available once a demo store is selected in the header."
            tone="muted"
          />
        </FadeIn>
      )}

      {storeId && (
        <>
          <FadeIn delay={0.1}>
            <Card className="border-glow hover-lift">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Filter className="h-5 w-5" />
                  Filters
                </CardTitle>
                <CardDescription>Refine audit entries by state, status, or order ID.</CardDescription>
              </CardHeader>

              <CardContent>
                <div className="grid gap-4 md:grid-cols-4">
                  <div className="space-y-2">
                    <Label htmlFor="search-order">Search Order</Label>
                    <div className="relative">
                      <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="search-order"
                        placeholder="Order ID..."
                        value={searchOrder}
                        onChange={(e) => setSearchOrder(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="filter-state">State</Label>
                    <Select value={filterState} onValueChange={setFilterState}>
                      <SelectTrigger>
                        <SelectValue placeholder="State" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All States</SelectItem>
                        <SelectItem value="MN">Minnesota</SelectItem>
                        <SelectItem value="CO">Colorado</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="filter-status">Status</Label>
                    <Select value={filterStatus} onValueChange={setFilterStatus}>
                      <SelectTrigger>
                        <SelectValue placeholder="Status" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Statuses</SelectItem>
                        <SelectItem value="applied">Applied</SelectItem>
                        <SelectItem value="recorded">Recorded</SelectItem>
                        <SelectItem value="not_applied">Not Applied</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-end gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleRefresh}
                      disabled={loading || !storeId}
                      className="w-full"
                    >
                      <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                      {loading ? "Refreshing" : "Refresh"}
                    </Button>
                    <Button variant="outline" size="sm" onClick={exportCsv} disabled={auditLogs.length === 0}>
                      <Download className="mr-2 h-4 w-4" />
                      Export
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </FadeIn>

          <FadeIn delay={0.2}>
                <Card className="relative border-glow hover-lift">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Audit Activity
                </CardTitle>
                <CardDescription>
                  {loading
                    ? "Loading latest decisions..."
                    : `Showing ${filteredLogs.length} of ${auditLogs.length} records`}
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Timestamp</TableHead>
                        <TableHead>Order ID</TableHead>
                        <TableHead>State</TableHead>
                        <TableHead>Amount</TableHead>
                        <TableHead>Reason Code</TableHead>
                        <TableHead>Absorbed</TableHead>
                        <TableHead>Delivery Method</TableHead>
                        <TableHead>Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {loading && filteredLogs.length === 0 &&
                        Array.from({ length: 6 }).map((_, index) => (
                          <TableRow key={`audit-skeleton-${index}`}>
                            <TableCell colSpan={8}>
                              <Skeleton className="h-6 w-full" />
                            </TableCell>
                          </TableRow>
                        ))}

                      {filteredLogs.map((log) => (
                        <TableRow key={log.id} className="transition-colors hover:bg-muted/40">
                          <TableCell className="font-mono text-sm">{log.timestamp}</TableCell>
                          <TableCell className="font-medium">{log.orderId}</TableCell>
                          <TableCell>{getJurisdictionBadge(log.jurisdiction)}</TableCell>
                          <TableCell
                            className={
                              parseFloat(log.amount.replace("$", "")) > 0
                                ? "text-primary"
                                : "text-muted-foreground"
                            }
                          >
                            {log.amount}
                          </TableCell>
                          <TableCell>
                            <code className="rounded bg-muted px-2 py-1 text-xs">{log.reasonCode}</code>
                          </TableCell>
                          <TableCell>
                            {log.absorbed ? (
                              <Badge variant="secondary" className="bg-muted text-muted-foreground">
                                Absorbed
                              </Badge>
                            ) : (
                              <Badge variant="outline">Shown</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-muted-foreground">{log.deliveryMethod}</TableCell>
                          <TableCell>{getStatusBadge(log.status)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {!loading && filteredLogs.length === 0 && (
                  <EmptyState
                    icon={Filter}
                    title="No audit logs match the current filters"
                    description="Adjust your filters or refresh the feed to see recent activity."
                    tone="bordered"
                  />
                )}

                {(nextCursor || hasMore) && (
                  <Button
                    variant="outline"
                    className="w-full justify-center transition-all hover-lift"
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                  >
                    {loadingMore ? (
                      <span className="flex items-center gap-2 text-sm">
                        <RefreshCw className="h-4 w-4 animate-spin" /> Loading more activity
                      </span>
                    ) : (
                      "Load more activity"
                    )}
                  </Button>
                )}
              </CardContent>
            </Card>
          </FadeIn>
        </>
      )}
    </div>
  );
}
