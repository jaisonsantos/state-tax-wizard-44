import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { FadeIn } from "@/components/ui/fade-in";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingOverlay } from "@/components/ui/loading-overlay";
import { FileText, Download, Calendar, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient, downloadBlob, type DownloadResult } from "@/lib/api";
import { resolveNextAuditCursor } from "@/lib/auditCursor";
import { useAuth } from "@/context/AuthContext";

type ReportKey = "co_dr1786" | "mn_summary";

const REPORT_LABELS: Record<ReportKey, string> = {
  co_dr1786: "CO DR-1786",
  mn_summary: "MN Summary",
};

interface ReportHistoryRow {
  id: string;
  report: string;
  format: string;
  fromDate?: string;
  toDate?: string;
  generatedAt?: string | null;
  outcome: string;
  rowCount?: number;
  mimeType?: string;
}

const HISTORY_PAGE_SIZE = 10;

export default function Reports() {
  const [startDate, setStartDate] = useState("2024-07-01");
  const [endDate, setEndDate] = useState("2024-09-30");
  const [mnFormat, setMnFormat] = useState<"csv" | "json">("csv");
  const [generatingReport, setGeneratingReport] = useState<ReportKey | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [history, setHistory] = useState<ReportHistoryRow[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const { toast } = useToast();
  const { selectedStoreId: storeId } = useAuth();

  useEffect(() => {
    if (!storeId) {
      setHistory([]);
      setHistoryError(null);
      setNextCursor(null);
      return;
    }

    let active = true;

    const loadHistory = async () => {
      setHistoryLoading(true);
      setHistoryError(null);

      try {
        const response = await apiClient.getAuditLogs(storeId, 1, HISTORY_PAGE_SIZE, "report_export");
        if (!active) return;

        const rows: ReportHistoryRow[] = response.items
          .filter((item) => item.action === "report_export")
          .map((item) => {
            const payload = item.payload as any ?? {};
            const rowCount = typeof payload.row_count === "number" ? payload.row_count : undefined;

            return {
              id: item.id,
              report: payload.report ?? item.action ?? "report_export",
              format: (payload.format ?? "csv") as string,
              fromDate: payload.from_date,
              toDate: payload.to_date,
              generatedAt: item.timestamp,
              outcome: (payload.outcome ?? "unknown") as string,
              rowCount,
              mimeType: payload.mime_type,
            };
          });

        setHistory(rows);
        setNextCursor(resolveNextAuditCursor(response));
      } catch (error) {
        if (!active) return;
        setHistory([]);
        setHistoryError(error instanceof Error ? error.message : "Unable to load export history");
        setNextCursor(null);
      } finally {
        if (active) {
          setHistoryLoading(false);
        }
      }
    };

    void loadHistory();

    return () => {
      active = false;
    };
  }, [storeId, refreshKey]);

  const historyRows = useMemo(() => {
    return history.map((row) => {
      const label = REPORT_LABELS[row.report as ReportKey] ?? row.report;
      const from = row.fromDate ? new Date(row.fromDate).toLocaleDateString() : "—";
      const to = row.toDate ? new Date(row.toDate).toLocaleDateString() : "—";
      const generated = row.generatedAt ? new Date(row.generatedAt).toLocaleString() : "—";

      return {
        ...row,
        label,
        range: `${from} → ${to}`,
        generated,
      };
    });
  }, [history]);

  const handleLoadMoreHistory = async () => {
    if (!storeId || !nextCursor) return;
    setLoadingMore(true);
    try {
      const response = await apiClient.getAuditLogs(storeId, 1, HISTORY_PAGE_SIZE, "report_export", nextCursor);
      const rows: ReportHistoryRow[] = response.items
        .filter((item) => item.action === "report_export")
        .map((item) => {
          const payload = item.payload as any ?? {};
          const rowCount = typeof payload.row_count === "number" ? payload.row_count : undefined;

          return {
            id: item.id,
            report: (payload.report ?? item.action ?? "report_export") as string,
            format: (payload.format ?? "csv") as string,
            fromDate: payload.from_date,
            toDate: payload.to_date,
            generatedAt: item.timestamp,
            outcome: (payload.outcome ?? "unknown") as string,
            rowCount,
            mimeType: payload.mime_type,
          };
        });

      setHistory((current) => [...current, ...rows]);
      setNextCursor(resolveNextAuditCursor(response));
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load additional exports";
      setHistoryError(message);
    } finally {
      setLoadingMore(false);
    }
  };

  const handleGenerateReport = async (target: ReportKey) => {
    if (!storeId) {
      toast({
        title: "Error",
        description: "No store selected",
        variant: "destructive",
      });
      return;
    }

    setGeneratingReport(target);
    setExportError(null);

    try {
      let download: DownloadResult;
      let fallbackFilename: string;

      if (target === "co_dr1786") {
        toast({
          title: "CO DR-1786 export queued",
          description: "Your CSV will download once the export completes.",
        });
        download = await apiClient.downloadCOReport(storeId, startDate, endDate);
        fallbackFilename = `CO_DR1786_${startDate}_${endDate}.csv`;
      } else {
        toast({
          title: "MN summary export queued",
          description: mnFormat === "csv"
            ? "CSV output opens in spreadsheets with individual order rows."
            : "JSON output is ideal for automation and dashboards.",
        });
        download = await apiClient.downloadMNReport(storeId, startDate, endDate, mnFormat);
        fallbackFilename = `MN_Summary_${startDate}_${endDate}.${mnFormat}`;
      }

      downloadBlob(download.blob, download.filename ?? fallbackFilename);

      toast({
        title: "Report ready",
        description: "The export history table now reflects the new download.",
      });
      setRefreshKey((current) => current + 1);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to generate report";
      setExportError(message);
      toast({
        title: "Report Generation Failed",
        description: message,
        variant: "destructive",
      });
    } finally {
      setGeneratingReport(null);
    }
  };

  return (
    <div className="max-w-6xl space-y-8">
      <FadeIn className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground">
          {storeId
            ? "Generate and download compliance reports for tax filing"
            : "Select a store to access compliance reports"}
        </p>
      </FadeIn>

      {exportError && (
        <FadeIn variant="fade">
          <Alert variant="destructive" className="border-destructive/40 bg-destructive/10">
            <AlertTitle>Export failed</AlertTitle>
            <AlertDescription>{exportError}</AlertDescription>
          </Alert>
        </FadeIn>
      )}

      {!storeId && (
        <FadeIn variant="fade">
          <Card className="border-none bg-muted/30">
            <CardContent className="p-4 text-sm text-muted-foreground">
              Choose a store from the selector above to enable report exports.
            </CardContent>
          </Card>
        </FadeIn>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Colorado DR-1786 Report */}
        <FadeIn className="relative">
          <Card className="relative h-full border-none bg-gradient-to-br from-colorado-muted/60 via-background to-background shadow-sm">
            {generatingReport === "co_dr1786" && (
              <LoadingOverlay transparent message="Generating Colorado report" className="rounded-2xl" />
            )}
            <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="h-8 w-8 rounded bg-colorado/10 flex items-center justify-center">
                <FileText className="h-4 w-4 text-colorado" />
              </div>
              Colorado DR-1786
            </CardTitle>
            <CardDescription>
              Official Colorado Department of Revenue form for delivery fee reporting
            </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="grid gap-3 grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="co-start-date">Start Date</Label>
                  <Input
                    id="co-start-date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="co-end-date">End Date</Label>
                  <Input
                    id="co-end-date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="co-format">Format</Label>
                <p id="co-format" className="text-sm text-muted-foreground">
                  Colorado exports are delivered as CSV files matching the Department of Revenue template.
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-colorado/30 bg-colorado-muted/60 p-3">
              <h4 className="font-medium text-sm mb-2">Report Includes:</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Transaction dates and order IDs</li>
                <li>• Fee amounts per delivery</li>
                <li>• Delivery method classification</li>
                <li>• Compliance reason codes</li>
              </ul>
            </div>

            <Button
              onClick={() => handleGenerateReport("co_dr1786")}
              className="w-full justify-center transition-all hover-lift"
              disabled={!!generatingReport || !storeId}
            >
              {generatingReport === "co_dr1786" ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Download className="h-4 w-4 mr-2" />
              )}
              {generatingReport === "co_dr1786" ? "Generating…" : "Generate CO DR-1786 Report"}
            </Button>
            </CardContent>
          </Card>
        </FadeIn>

        {/* Minnesota Summary Report */}
        <FadeIn className="relative">
          <Card className="relative h-full border-none bg-gradient-to-br from-minnesota-muted/60 via-background to-background shadow-sm">
            {generatingReport === "mn_summary" && (
              <LoadingOverlay transparent message="Generating Minnesota report" className="rounded-2xl" />
            )}
            <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="h-8 w-8 rounded bg-minnesota/10 flex items-center justify-center">
                <FileText className="h-4 w-4 text-minnesota" />
              </div>
              Minnesota Summary
            </CardTitle>
            <CardDescription>
              Comprehensive summary report for Minnesota delivery fee compliance
            </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="grid gap-3 grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="mn-start-date">Start Date</Label>
                  <Input
                    id="mn-start-date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="mn-end-date">End Date</Label>
                  <Input
                    id="mn-end-date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="mn-format">Format</Label>
                <Select value={mnFormat} onValueChange={(value) => setMnFormat(value as "csv" | "json")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="csv">CSV</SelectItem>
                    <SelectItem value="json">JSON</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  CSV includes each order line, while JSON returns aggregated counts for dashboards.
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-minnesota/30 bg-minnesota-muted/60 p-3">
              <h4 className="font-medium text-sm mb-2">Report Includes:</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Total fees collected by month</li>
                <li>• Threshold compliance rates</li>
                <li>• BOPIS/curbside exemptions</li>
                <li>• Order volume analytics</li>
              </ul>
            </div>

            <Button
              onClick={() => handleGenerateReport("mn_summary")}
              className="w-full justify-center transition-all hover-lift"
              variant="outline"
              disabled={!!generatingReport || !storeId}
            >
              {generatingReport === "mn_summary" ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Download className="h-4 w-4 mr-2" />
              )}
              {generatingReport === "mn_summary" ? "Generating…" : "Generate MN Summary Report"}
            </Button>
            </CardContent>
          </Card>
        </FadeIn>
      </div>

      {/* Export History */}
      <FadeIn>
        <Card className="border-none bg-background shadow-sm">
          <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-primary" />
            Export History
          </CardTitle>
          <CardDescription>
            Previously generated reports and downloads
          </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            {historyError && (
              <Alert variant="destructive" className="border-destructive/40 bg-destructive/10">
                <AlertTitle>Unable to load export history</AlertTitle>
                <AlertDescription>{historyError}</AlertDescription>
              </Alert>
            )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Report</TableHead>
                <TableHead>Filters</TableHead>
                <TableHead>Generated</TableHead>
                <TableHead>Outcome</TableHead>
                <TableHead>Format</TableHead>
                <TableHead>Rows</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {historyLoading
                ? Array.from({ length: 3 }).map((_, index) => (
                    <TableRow key={`history-skeleton-${index}`}>
                      <TableCell>
                        <Skeleton className="h-4 w-24" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-40" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-32" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-20" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-20" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-16" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-9 w-20" />
                      </TableCell>
                    </TableRow>
                  ))
                : historyRows.length > 0
                ? historyRows.map((export_) => (
                    <TableRow key={export_.id}>
                      <TableCell>
                        <Badge
                          variant={export_.report === "co_dr1786" ? "default" : "secondary"}
                          className={export_.report === "co_dr1786" ? "bg-colorado text-colorado-foreground" : "bg-minnesota text-minnesota-foreground"}
                        >
                          {export_.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium">{export_.range}</TableCell>
                      <TableCell className="text-muted-foreground">{export_.generated}</TableCell>
                      <TableCell>
                        <Badge
                          className={
                            export_.outcome === "success"
                              ? "bg-success text-success-foreground"
                              : "bg-destructive text-destructive-foreground"
                          }
                        >
                          {export_.outcome}
                        </Badge>
                      </TableCell>
                      <TableCell className="uppercase text-muted-foreground">{export_.format}</TableCell>
                      <TableCell className="text-muted-foreground">{export_.rowCount ?? "—"}</TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            handleGenerateReport(
                              export_.report === "co_dr1786" ? "co_dr1786" : "mn_summary"
                            )
                          }
                          disabled={!!generatingReport || !storeId}
                        >
                          {generatingReport === export_.report ? (
                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          ) : (
                            <Download className="h-3 w-3 mr-1" />
                          )}
                          Re-run
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                : (
                    <TableRow>
                      <TableCell colSpan={7}>
                        <EmptyState
                          subtle
                          title={storeId ? "No exports yet" : "Store not selected"}
                          description={
                            storeId
                              ? "Generate a report to populate this history."
                              : "Select a store to view export history."
                          }
                          className="mx-auto max-w-xl"
                        />
                      </TableCell>
                    </TableRow>
                  )}
            </TableBody>
          </Table>
          {nextCursor && storeId && historyRows.length > 0 && (
            <Button
              variant="outline"
              className="mt-4 w-full justify-center transition-all hover-lift"
              onClick={handleLoadMoreHistory}
              disabled={loadingMore}
            >
              {loadingMore ? (
                <span className="flex items-center gap-2 text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading more history
                </span>
              ) : (
                "Load more history"
              )}
            </Button>
          )}
        </CardContent>
        </Card>
      </FadeIn>
    </div>
  );
}