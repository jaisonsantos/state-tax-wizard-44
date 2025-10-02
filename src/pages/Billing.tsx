import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CreditCard, ExternalLink, CheckCircle, AlertTriangle, Calendar, TrendingUp, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient, ApiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

const plans = [
  {
    name: "starter",
    displayName: "Starter",
    price: 29,
    description: "Perfect for small businesses",
    features: [
      "Up to 1,000 transactions/month",
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
      "Up to 10,000 transactions/month",
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
      "Unlimited transactions",
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

export default function Billing() {
  const [entitlements, setEntitlements] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const { toast } = useToast();
  const { selectedStoreId: storeId } = useAuth();

  useEffect(() => {
    const initializeData = async () => {
      if (!storeId) {
        setEntitlements(null);
        setUsage(null);
        setLoading(false);
        setError(null);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const [entitlementsData, usageData] = await Promise.all([
          apiClient.getEntitlements(storeId),
          apiClient.getUsage(storeId)
        ]);
        setEntitlements(entitlementsData);
        setUsage(usageData);
      } catch (err) {
        if (err instanceof ApiError && err.code === "billing_unconfigured") {
          setError("Billing system not configured. Contact support to enable Stripe integration.");
        } else {
          setError(err instanceof Error ? err.message : "Failed to load billing information");
        }
        setEntitlements(null);
        setUsage(null);
      } finally {
        setLoading(false);
      }
    };

    initializeData();
  }, [storeId, toast]);

  const handleUpgrade = async (planName: string) => {
    if (!storeId) {
      toast({
        title: "Error",
        description: "No store selected",
        variant: "destructive",
      });
      return;
    }

    setCheckoutLoading(planName);
    try {
      const origin = window.location.origin;
      const response = await apiClient.createCheckoutSession(
        storeId,
        planName,
        `${origin}/billing?success=true`,
        `${origin}/billing?canceled=true`
      );

      if (response.url) {
        window.open(response.url, '_blank');
        toast({
          title: "Checkout opened",
          description: "Complete your subscription in the new tab",
        });
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === "billing_unconfigured") {
        toast({
          title: "Billing unavailable",
          description: "Stripe integration not configured. Contact support.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Error",
          description: err instanceof Error ? err.message : "Failed to create checkout session",
          variant: "destructive",
        });
      }
    } finally {
      setCheckoutLoading(null);
    }
  };

  const handleManageSubscription = async () => {
    if (!storeId) {
      toast({
        title: "Error",
        description: "No store selected",
        variant: "destructive",
      });
      return;
    }

    setPortalLoading(true);
    try {
      const origin = window.location.origin;
      const response = await apiClient.createPortalSession(storeId, `${origin}/billing`);

      if (response.portal_url) {
        window.open(response.portal_url, '_blank');
        toast({
          title: "Customer portal opened",
          description: "Manage your subscription in the new tab",
        });
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === "billing_unconfigured") {
        toast({
          title: "Billing unavailable",
          description: "Stripe integration not configured. Contact support.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Error",
          description: err instanceof Error ? err.message : "Failed to open portal",
          variant: "destructive",
        });
      }
    } finally {
      setPortalLoading(false);
    }
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

  const currentPlan = plans.find((p) => p.name === entitlements?.plan) || plans[0];
  const trialDaysLeft = getTrialDaysLeft();
  const isTrialing = entitlements?.status === "trialing";
  const usagePercentage = usage?.unlimited ? 0 : usage?.percentage_used || 0;

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

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

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
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Calendar className="h-6 w-6 text-primary" />
                <div>
                  <h3 className="font-semibold text-foreground">Free Trial Active</h3>
                  <p className="text-sm text-muted-foreground">
                    {trialDaysLeft} days remaining. Activate a plan to unlock production features.
                  </p>
                </div>
              </div>
              <Button onClick={() => handleUpgrade(currentPlan.name)}>
                Choose Plan
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Current Subscription + Usage */}
      {storeId && entitlements && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Current Subscription
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">{currentPlan.displayName} Plan</h3>
                <p className="text-muted-foreground">
                  Billed via {entitlements.provider === "shopify" ? "Shopify" : "Stripe"}
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold">${currentPlan.price}/mo</div>
                <Badge className={isTrialing ? "bg-primary text-primary-foreground" : "bg-success text-success-foreground"}>
                  <CheckCircle className="h-3 w-3 mr-1" />
                  {isTrialing ? "Trial" : entitlements.status || "Active"}
                </Badge>
              </div>
            </div>

            {usage && (
              <div className="p-4 bg-muted rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    <h4 className="font-medium">Usage This Period</h4>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {usage.unlimited
                      ? `${usage.transactions_used} transactions (Unlimited)`
                      : `${usage.transactions_used} / ${usage.transactions_limit} transactions`}
                  </span>
                </div>
                {!usage.unlimited && (
                  <Progress value={usagePercentage} className="h-2" />
                )}
                {!usage.unlimited && usagePercentage >= 80 && (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      You've used {Math.round(usagePercentage)}% of your monthly quota. Consider upgrading to avoid service interruption.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            )}

            <div className="p-4 bg-muted rounded-lg">
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <h4 className="font-medium mb-2">Billing Method</h4>
                  <p className="text-sm text-muted-foreground">
                    {entitlements.provider === "shopify"
                      ? "Charges appear on your monthly Shopify invoice"
                      : "Secure billing via Stripe with VAT handling"}
                  </p>
                </div>
                <div>
                  <h4 className="font-medium mb-2">Next Billing Date</h4>
                  <p className="text-sm text-muted-foreground">
                    {isTrialing && entitlements.trial_ends_at
                      ? `Trial ends: ${new Date(entitlements.trial_ends_at).toLocaleDateString()}`
                      : entitlements.current_period_end
                      ? new Date(entitlements.current_period_end).toLocaleDateString()
                      : "N/A"}
                  </p>
                </div>
              </div>
            </div>

            {entitlements.provider === "stripe" && (
              <Button
                variant="outline"
                onClick={handleManageSubscription}
                disabled={portalLoading}
                className="w-full"
              >
                {portalLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Opening Portal...
                  </>
                ) : (
                  <>
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Manage Subscription
                  </>
                )}
              </Button>
            )}
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
              <div
                key={plan.name}
                className={`relative border rounded-lg p-6 ${
                  plan.popular ? "border-primary shadow-lg" : "border-border"
                }`}
              >
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
                  disabled={!storeId || (entitlements && plan.name === entitlements.plan) || checkoutLoading === plan.name}
                  onClick={() => handleUpgrade(plan.name)}
                >
                  {checkoutLoading === plan.name ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Loading...
                    </>
                  ) : entitlements && plan.name === entitlements.plan ? (
                    "Current Plan"
                  ) : (
                    "Select Plan"
                  )}
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
    </div>
  );
}
