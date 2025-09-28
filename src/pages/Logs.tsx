import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Activity, Search, Filter, Download, RefreshCw } from "lucide-react";
import { apiClient, downloadBlob } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

type AuditRow = {
  id: string;
  timestamp: string;
  orderId: string;
  jurisdiction: string;
  amount: string;
  reasonCode: string;
  deliveryMethod: string;
  status: string;
};

export default function Logs() {
  const [filterState, setFilterState] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [searchOrder, setSearchOrder] = useState("");
  const [auditLogs, setAuditLogs] = useState<AuditRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [storeId, setStoreId] = useState<string>("");
  const { toast } = useToast();

  useEffect(() => {
    const initializeData = async () => {
      try {
        const userInfo = await apiClient.getMe();
        if (userInfo.stores && userInfo.stores.length > 0) {
          const currentStoreId = userInfo.stores[0].id;
          setStoreId(currentStoreId);
          await fetchAuditLogs(currentStoreId);
        }
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to load store information",
          variant: "destructive",
        });
      }
    };

    initializeData();
  }, []);

  const fetchAuditLogs = async (store_id: string) => {
    setLoading(true);
    try {
      const response = await apiClient.getAuditLogs(store_id);

      const transformedLogs: AuditRow[] = response.items.map((log) => {
        const firstLine = log.payload.lines?.[0];
        const amountCents = firstLine?.amount_cents ?? 0;
        const reasonCodes = firstLine?.reason_codes ?? [];
        const jurisdiction = firstLine?.jurisdiction || (log.payload as any).jurisdiction || "--";

        return {
          id: log.id,
          timestamp: log.timestamp ? new Date(log.timestamp).toLocaleString() : "--",
          orderId: log.payload.order_id ? `${log.payload.order_id}` : "--",
          jurisdiction,
          amount: `$${(amountCents / 100).toFixed(2)}`,
          reasonCode: reasonCodes[0] || log.action.toUpperCase(),
          deliveryMethod: log.payload.delivery_method || "Unknown",
          status: log.payload.status || (log.action === "fee_apply" ? "applied" : "recorded"),
        };
      });

      setAuditLogs(transformedLogs);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load audit logs",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = () => {
    if (storeId) {
      fetchAuditLogs(storeId);
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

    const header = ["timestamp", "orderId", "jurisdiction", "amount", "reasonCode", "deliveryMethod", "status"];
    const rows = auditLogs.map((log) => [
      log.timestamp,
      log.orderId,
      log.jurisdiction,
      log.amount,
      log.reasonCode,
      log.deliveryMethod,
      log.status,
    ]);

    const csvContent = [header, ...rows]
      .map((row) => row.map((value) => `"${value.replace(/"/g, '""')}"`).join(","))
      .join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    downloadBlob(blob, "audit-logs.csv");
  };

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold">Logs & Audit</h1>
        <p className="text-muted-foreground">
          Comprehensive audit trail of all delivery fee decisions
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
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
              <Button variant="secondary" size="sm" onClick={handleRefresh} disabled={loading || !storeId}>
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
                {loading ? "Refreshing" : "Refresh"}
              </Button>
              <Button variant="outline" size="sm" onClick={exportCsv} disabled={auditLogs.length === 0}>
                <Download className="h-4 w-4 mr-2" />
                Export CSV
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Audit Activity
          </CardTitle>
          <CardDescription>
            {loading ? "Loading latest decisions..." : `Showing ${filteredLogs.length} of ${auditLogs.length} records`}
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
                  <TableHead>Delivery Method</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-mono text-sm">{log.timestamp}</TableCell>
                    <TableCell className="font-medium">{log.orderId}</TableCell>
                    <TableCell>{getJurisdictionBadge(log.jurisdiction)}</TableCell>
                    <TableCell className={parseFloat(log.amount.replace('$', '')) > 0 ? "text-primary" : "text-muted-foreground"}>
                      {log.amount}
                    </TableCell>
                    <TableCell>
                      <code className="text-xs bg-muted px-2 py-1 rounded">{log.reasonCode}</code>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{log.deliveryMethod}</TableCell>
                    <TableCell>{getStatusBadge(log.status)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {loading && (
            <div className="text-center py-8 text-muted-foreground">
              Loading audit logs...
            </div>
          )}

          {!loading && filteredLogs.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              No audit logs match the current filters
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
