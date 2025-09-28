import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Activity, Search, Filter, Download, RefreshCw } from "lucide-react";
import { apiClient } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

const auditLogs = [
  {
    id: 1,
    timestamp: "2024-10-01 14:23:15",
    orderId: "#12847",
    jurisdiction: "MN",
    amount: "$0.50",
    reasonCode: "MN_THRESHOLD_MET", 
    deliveryMethod: "Standard Delivery",
    status: "applied"
  },
  {
    id: 2,
    timestamp: "2024-10-01 14:18:42",
    orderId: "#12846", 
    jurisdiction: "CO",
    amount: "$1.00",
    reasonCode: "CO_HAS_TAXABLE_ITEM",
    deliveryMethod: "Standard Delivery",
    status: "applied"
  },
  {
    id: 3,
    timestamp: "2024-10-01 14:15:33",
    orderId: "#12845",
    jurisdiction: "MN",
    amount: "$0.00",
    reasonCode: "MN_BOPIS_EXEMPT",
    deliveryMethod: "Buy Online, Pick In Store",
    status: "exempt"
  },
  {
    id: 4,
    timestamp: "2024-10-01 14:12:18",
    orderId: "#12844",
    jurisdiction: "CO", 
    amount: "$1.00",
    reasonCode: "CO_SPLIT_SHIPMENT",
    deliveryMethod: "Standard Delivery",
    status: "applied"
  },
  {
    id: 5,
    timestamp: "2024-10-01 14:08:55",
    orderId: "#12843",
    jurisdiction: "MN",
    amount: "$0.00", 
    reasonCode: "MN_BELOW_THRESHOLD",
    deliveryMethod: "Standard Delivery",
    status: "not_applied"
  },
  {
    id: 6,
    timestamp: "2024-10-01 14:05:12",
    orderId: "#12842",
    jurisdiction: "CO",
    amount: "$0.00",
    reasonCode: "CO_NO_TAXABLE_ITEMS",
    deliveryMethod: "Standard Delivery", 
    status: "not_applied"
  }
];

export default function Logs() {
  const [filterState, setFilterState] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [searchOrder, setSearchOrder] = useState("");
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [storeId, setStoreId] = useState<string>("");
  const { toast } = useToast();

  useEffect(() => {
    const initializeData = async () => {
      try {
        // Get store ID from user info
        const userInfo = await apiClient.getMe();
        if (userInfo.stores && userInfo.stores.length > 0) {
          setStoreId(userInfo.stores[0].id);
          await fetchAuditLogs(userInfo.stores[0].id);
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
      
      // Transform API response to match UI format
      const transformedLogs = response.items.map((log: any, index: number) => ({
        id: log.id || index + 1,
        timestamp: new Date(log.timestamp).toLocaleString(),
        orderId: log.payload.order_id || `#${Math.floor(Math.random() * 10000)}`,
        jurisdiction: log.payload.jurisdiction || (log.payload.destination?.state) || "MN",
        amount: log.payload.amount_cents ? `$${(log.payload.amount_cents / 100).toFixed(2)}` : "$0.00",
        reasonCode: log.payload.reason_codes?.[0] || log.action.toUpperCase(),
        deliveryMethod: log.payload.delivery_method || "Standard Delivery",
        status: log.action === "fee_apply" ? "applied" : (log.payload.amount_cents > 0 ? "applied" : "not_applied")
      }));
      
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

  const filteredLogs = auditLogs.filter(log => {
    const matchesState = filterState === "all" || log.jurisdiction === filterState;
    const matchesStatus = filterStatus === "all" || log.status === filterStatus;
    const matchesSearch = searchOrder === "" || log.orderId.toLowerCase().includes(searchOrder.toLowerCase());
    
    return matchesState && matchesStatus && matchesSearch;
  });

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
        className={jurisdiction === "MN" 
          ? "bg-minnesota text-minnesota-foreground" 
          : "bg-colorado text-colorado-foreground"
        }
      >
        {jurisdiction}
      </Badge>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold">Logs & Audit</h1>
        <p className="text-muted-foreground">
          Comprehensive audit trail of all delivery fee decisions
        </p>
      </div>

      {/* Filters */}
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
                  <SelectValue />
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
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="applied">Applied</SelectItem>
                  <SelectItem value="exempt">Exempt</SelectItem>
                  <SelectItem value="not_applied">Not Applied</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-end gap-2">
              <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Audit Log Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Audit Trail
          </CardTitle>
          <CardDescription>
            {loading ? "Loading..." : `Showing ${filteredLogs.length} of ${auditLogs.length} decisions`}
          </CardDescription>
        </CardHeader>
        
        <CardContent>
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
                  <TableCell className="font-mono text-sm">
                    {log.timestamp}
                  </TableCell>
                  <TableCell className="font-medium">
                    {log.orderId}
                  </TableCell>
                  <TableCell>
                    {getJurisdictionBadge(log.jurisdiction)}
                  </TableCell>
                  <TableCell className={`font-medium ${
                    parseFloat(log.amount.replace('$', '')) > 0 
                      ? 'text-primary' 
                      : 'text-muted-foreground'
                  }`}>
                    {log.amount}
                  </TableCell>
                  <TableCell>
                    <code className="text-xs bg-muted px-2 py-1 rounded">
                      {log.reasonCode}
                    </code>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {log.deliveryMethod}
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(log.status)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading audit logs...
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No audit logs match the current filters
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}