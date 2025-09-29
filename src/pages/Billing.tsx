import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { CreditCard, ExternalLink, CheckCircle, AlertTriangle, Calendar, DollarSign } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const plans = [
  {
    name: "starter",
    displayName: "Starter",
    price: 29,
    description: "Perfect for small businesses",
    features: [
      "Up to 1,000 orders/month",
      "Basic compliance reports",
      "Email support",
      "MN & CO coverage"
    ],
    popular: false
  },
  {
    name: "pro",
    displayName: "Pro", 
    price: 49,
    description: "Most popular for growing stores",
    features: [
      "Up to 10,000 orders/month", 
      "Advanced analytics & reports",
      "Priority support",
      "MN & CO coverage",
      "Custom fee labels",
      "Audit trail exports"
    ],
    popular: true
  },
  {
    name: "plus",
    displayName: "Plus",
    price: 99,
    description: "For enterprise-scale operations",
    features: [
      "Unlimited orders",
      "White-label reports",
      "Dedicated account manager", 
      "SLA guarantee",
      "MN & CO coverage",
      "Custom integrations",
      "Real-time alerts"
    ],
    popular: false
  }
];

const invoiceHistory = [
  {
    id: "inv_001",
    date: "2024-09-01",
    amount: "$49.00",
    plan: "Pro",
    status: "paid",
    provider: "shopify"
  },
  {
    id: "inv_002", 
    date: "2024-08-01",
    amount: "$49.00",
    plan: "Pro",
    status: "paid",
    provider: "shopify"
  },
  {
    id: "inv_003",
    date: "2024-07-01", 
    amount: "$29.00",
    plan: "Starter",
    status: "paid", 
    provider: "stripe"
  }
];

export default function Billing() {
  const [entitlements, setEntitlements] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const { selectedStoreId: storeId } = useAuth();

  useEffect(() => {
    const initializeData = async () => {
      if (!storeId) {
        setEntitlements(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const entitlementsData = await apiClient.getEntitlements(storeId);
        setEntitlements(entitlementsData);
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to load billing information",
          variant: "destructive",
        });
        setEntitlements(null);
      } finally {
        setLoading(false);
      }
    };

    initializeData();
  }, [storeId, toast]);

  const handleShopifyBilling = (planName: string) => {
    toast({
      title: "Shopify Billing",
      description: `You'll be redirected to Shopify to approve the ${planName} plan subscription`,
    });
  };

  const handleStripeBilling = (planName: string) => {
    toast({
      title: "Stripe Checkout",
      description: `Opening secure checkout for ${planName} plan`,
    });
  };

  const getPlanBadge = (planName: string) => {
    if (entitlements && planName.toLowerCase() === entitlements.plan.toLowerCase()) {
      return <Badge className="bg-success text-success-foreground">Current</Badge>;
    }
    return null;
  };

  const getTrialDaysLeft = () => {
    if (!entitlements?.trial_ends_at) return 0;
    
    const trialEnd = new Date(entitlements.trial_ends_at);
    const now = new Date();
    const diffTime = trialEnd.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    return Math.max(0, diffDays);
  };

  const currentPlan = useMemo(
    () => plans.find((p) => p.name === entitlements?.plan) || plans[0],
    [entitlements],
  );
  const trialDaysLeft = getTrialDaysLeft();
  const isTrialing = entitlements?.status === "trialing";

  if (loading) {
    return (
      <div className="space-y-6 max-w-6xl">
        <div>
          <h1 className="text-3xl font-bold">Billing & Plans</h1>
          <p className="text-muted-foreground">Loading billing information...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-3xl font-bold">Billing & Plans</h1>
        <p className="text-muted-foreground">
          {storeId
            ? "Manage your subscription and billing preferences"
            : "Select a store to view subscription details"}
        </p>
      </div>

      {!storeId && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-warning" />
              <p className="text-sm text-muted-foreground">
                Choose a store from the selector above to load billing information.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Trial Status */}
      {storeId && isTrialing && trialDaysLeft > 0 && (
        <Card className="bg-primary-muted border-primary/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Calendar className="h-6 w-6 text-primary" />
                <div>
                  <h3 className="font-semibold text-primary">Free Trial Active</h3>
                  <p className="text-sm text-primary/80">
                    {trialDaysLeft} days remaining. Activate a plan to unlock production features.
                  </p>
                </div>
              </div>
              <Button>
                Choose Plan
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Current Subscription */}
      {storeId && (
        <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Current Subscription
          </CardTitle>
        </CardHeader>
        
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold">{currentPlan.displayName} Plan</h3>
              <p className="text-muted-foreground">
                Billed via {entitlements?.provider === "shopify" ? "Shopify" : "Stripe"}
              </p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold">${currentPlan.price}/mo</div>
              <Badge className={isTrialing ? "bg-primary text-primary-foreground" : "bg-success text-success-foreground"}>
                <CheckCircle className="h-3 w-3 mr-1" />
                {isTrialing ? "Trial" : "Active"}
              </Badge>
            </div>
          </div>

          <div className="p-4 bg-muted rounded-lg">
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <h4 className="font-medium mb-2">Billing Method</h4>
                <p className="text-sm text-muted-foreground">
                  {entitlements?.provider === "shopify" 
                    ? "Charges appear on your monthly Shopify invoice"
                    : "Secure billing via Stripe with VAT handling"
                  }
                </p>
              </div>
              <div>
                <h4 className="font-medium mb-2">Next Billing Date</h4>
                <p className="text-sm text-muted-foreground">
                  {isTrialing && entitlements?.trial_ends_at 
                    ? `Trial ends: ${new Date(entitlements.trial_ends_at).toLocaleDateString()}`
                    : "November 1, 2024"
                  }
                </p>
              </div>
            </div>
          </div>
        </CardContent>
        </Card>
      )}

      {/* Plan Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Choose Your Plan</CardTitle>
          <CardDescription>
            Select the plan that best fits your business needs. All plans include 14-day free trial.
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <div className="grid gap-6 md:grid-cols-3">
            {plans.map((plan) => (
              <div key={plan.name} className={`relative border rounded-lg p-6 ${
                plan.popular ? 'border-primary shadow-lg' : 'border-border'
              }`}>
                {plan.popular && (
                  <Badge className="absolute -top-2 left-1/2 transform -translate-x-1/2 bg-primary text-primary-foreground">
                    Most Popular
                  </Badge>
                )}
                
                <div className="text-center mb-4">
                  <h3 className="text-lg font-semibold flex items-center justify-center gap-2">
                    {plan.displayName}
                    {getPlanBadge(plan.name)}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">{plan.description}</p>
                  <div className="mt-4">
                    <span className="text-3xl font-bold">${plan.price}</span>
                    <span className="text-muted-foreground">/month</span>
                  </div>
                </div>

                <ul className="space-y-2 mb-6">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-center gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-success flex-shrink-0" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <Button
                  className="w-full"
                  variant={entitlements && plan.name === entitlements.plan ? "outline" : "default"}
                  disabled={entitlements && plan.name === entitlements.plan}
                  onClick={() => {
                    if (!storeId) {
                      toast({
                        title: "Select a store",
                        description: "Choose a store before updating plan details.",
                        variant: "destructive",
                      });
                      return;
                    }
                    if (entitlements?.provider === "shopify") {
                      handleShopifyBilling(plan.displayName);
                    } else {
                      handleStripeBilling(plan.displayName);
                    }
                  }}
                >
                  {entitlements && plan.name === entitlements.plan ? "Current Plan" : "Select Plan"}
                </Button>
              </div>
            ))}
          </div>

          <div className="mt-6 p-4 bg-muted rounded-lg">
            <h4 className="font-medium mb-2">Billing Information</h4>
            <div className="grid gap-4 md:grid-cols-2 text-sm text-muted-foreground">
              <div>
                <strong>Shopify Merchants:</strong> Billing is handled by Shopify. 
                You'll confirm this subscription in your Shopify Admin and charges 
                appear on your monthly Shopify invoice.
              </div>
              <div>
                <strong>WooCommerce Merchants:</strong> Secure billing via Stripe. 
                EU B2B customers with valid VAT numbers are reverse-charged. 
                Invoices include VAT details as required.
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Invoice History */}
      {storeId && (
        <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Billing History
          </CardTitle>
          <CardDescription>
            Your recent invoices and payment history
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice ID</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Plan</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Provider</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoiceHistory.map((invoice) => (
                <TableRow key={invoice.id}>
                  <TableCell className="font-mono text-sm">{invoice.id}</TableCell>
                  <TableCell>{invoice.date}</TableCell>
                  <TableCell>{invoice.plan}</TableCell>
                  <TableCell className="font-medium">{invoice.amount}</TableCell>
                  <TableCell className="capitalize">{invoice.provider}</TableCell>
                  <TableCell>
                    <Badge className="bg-success text-success-foreground">
                      {invoice.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
        </Card>
      )}
    </div>
  );
}