import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TrendingUp, AlertCircle, DollarSign, CheckCircle, Activity } from "lucide-react";

const kpiData = [
  {
    title: "Fees Applied (30d)",
    value: "1,247",
    change: "+12.5%",
    trend: "up" as const,
    icon: DollarSign,
    color: "text-success"
  },
  {
    title: "MN Threshold Met",
    value: "68%",
    change: "+4.2%",
    trend: "up" as const,
    icon: CheckCircle,
    color: "text-minnesota"
  },
  {
    title: "CO Fees Total",
    value: "$2,847",
    change: "-2.1%",
    trend: "down" as const,
    icon: DollarSign,
    color: "text-colorado"
  },
  {
    title: "Errors (7d)",
    value: "3",
    change: "-50%",
    trend: "down" as const,
    icon: AlertCircle,
    color: "text-warning"
  }
];

const recentEvents = [
  {
    id: 1,
    timestamp: "2 minutes ago",
    event: "MN_THRESHOLD_MET",
    order: "#12847",
    amount: "$0.50",
    state: "MN" as const
  },
  {
    id: 2,
    timestamp: "5 minutes ago",
    event: "CO_HAS_TAXABLE_ITEM",
    order: "#12846",
    amount: "$1.00",
    state: "CO" as const
  },
  {
    id: 3,
    timestamp: "12 minutes ago",
    event: "MN_BOPIS_EXEMPT",
    order: "#12845",
    amount: "$0.00",
    state: "MN" as const
  },
  {
    id: 4,
    timestamp: "18 minutes ago",
    event: "CO_SPLIT_SHIPMENT",
    order: "#12844",
    amount: "$1.00",
    state: "CO" as const
  }
];

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Monitor your delivery fee compliance across Minnesota and Colorado
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {kpiData.map((kpi) => (
          <Card key={kpi.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{kpi.title}</CardTitle>
              <kpi.icon className={`h-4 w-4 ${kpi.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{kpi.value}</div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <TrendingUp className={`h-3 w-3 ${
                  kpi.trend === 'up' ? 'text-success' : 'text-destructive'
                }`} />
                <span className={kpi.trend === 'up' ? 'text-success' : 'text-destructive'}>
                  {kpi.change}
                </span>
                <span>from last month</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Recent Fee Decisions
            </CardTitle>
            <CardDescription>
              Latest automated fee applications and exemptions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentEvents.map((event) => (
                <div key={event.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <Badge variant={event.state === 'MN' ? 'default' : 'secondary'} 
                           className={event.state === 'MN' ? 'bg-minnesota text-minnesota-foreground' : 'bg-colorado text-colorado-foreground'}>
                      {event.state}
                    </Badge>
                    <div>
                      <p className="text-sm font-medium">{event.order}</p>
                      <p className="text-xs text-muted-foreground">{event.event}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">{event.amount}</p>
                    <p className="text-xs text-muted-foreground">{event.timestamp}</p>
                  </div>
                </div>
              ))}
            </div>
            <Button variant="outline" className="w-full mt-4">
              View All Logs
            </Button>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common tasks and navigation
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button className="w-full justify-start" variant="outline">
              Generate CO DR-1786 Report
            </Button>
            <Button className="w-full justify-start" variant="outline">
              Download MN Summary
            </Button>
            <Button className="w-full justify-start" variant="outline">
              Test Fee Rules
            </Button>
            <Button className="w-full justify-start" variant="outline">
              Configure Store Settings
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}