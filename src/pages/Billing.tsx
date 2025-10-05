import { useEffect, useMemo, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { FadeIn } from "@/components/ui/fade-in";
import { LoadingOverlay } from "@/components/ui/loading-overlay";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  CreditCard,
  ExternalLink,
  CheckCircle,
  AlertTriangle,
  Calendar,
  TrendingUp,
  Loader2,
  Building,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import {
  apiClient,
  ApiError,
  BillingEntitlements,
  BillingUsage,
  BillingEnterpriseOverage,
} from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  CORE_PRICING_PLANS as CORE_PLANS,
  ENTERPRISE_PRICING_PLANS as ENTERPRISE_PLANS,
  PRICING_PLAN_CATALOG,
  type PricingPlanDefinition,
} from "@/lib/pricing";

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

type PricingPlan = PricingPlanDefinition;

const formatCurrency = (value: number): string => currencyFormatter.format(value);

const computeAnnualSavings = (plan: PricingPlan): number | null => {
  if (plan.monthlyPrice <= 0 || plan.annualPrice <= 0) {
    return null;
  }
  const rack = plan.monthlyPrice * 12;
  if (rack === 0) {
    return null;
  }
  return Math.round((1 - plan.annualPrice / rack) * 100);
};

const limitLabel = (plan: PricingPlan): string => {
  if (plan.commitDeliveries) {
    return `Committed ${plan.commitDeliveries.toLocaleString()} deliveries/month`;
  }
  if (plan.deliveriesIncluded === 0) {
    return "Unlimited deliveries";
  }
  if (plan.deliveriesIncluded) {
    return `Up to ${plan.deliveriesIncluded.toLocaleString()} deliveries/month`;
  }
  return "Limit defined by contract";
};

const formatOverage = (overage: BillingEnterpriseOverage | null | undefined): string | null => {
  if (!overage) {
    return null;
  }
  const fee = overage.overage_fee
    ? `${currencyFormatter.format(overage.overage_fee)}/delivery`
    : "usage recorded";
  return `${overage.overage_units.toLocaleString()} deliveries above the commitment of ${overage.commit_deliveries.toLocaleString()} (${fee}).`;
};

export default function Billing() {
  const [entitlements, setEntitlements] = useState<BillingEntitlements | null>(null);
  const [usage, setUsage] = useState<BillingUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const [contactPlan, setContactPlan] = useState<PricingPlan | null>(null);
  const [contactOpen, setContactOpen] = useState(false);
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
          apiClient.getUsage(storeId),
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
  }, [storeId]);

  const planCatalog = useMemo(() => PRICING_PLAN_CATALOG, []);
  const stripeConfigured = entitlements?.stripe_prices_configured ?? {};

  const isPlanConfigured = (planKey: string) => Boolean(stripeConfigured[planKey]);

  const currentPlan = useMemo(() => {
    if (!entitlements) {
      return CORE_PLANS[0];
    }
    return (
      planCatalog.find((plan) => plan.key === entitlements.plan) ?? CORE_PLANS[0]
    );
  }, [entitlements, planCatalog]);

  const trialDaysLeft = (() => {
    if (!entitlements?.trial_ends_at) return 0;
    const trialEnd = new Date(entitlements.trial_ends_at);
    const now = new Date();
    const diffTime = trialEnd.getTime() - now.getTime();
    return Math.max(0, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
  })();

  const isTrialing = entitlements?.status === "trialing";
  const usagePercentage = usage?.unlimited ? 0 : usage?.percentage_used ?? 0;
  const warnThreshold = usage?.warn_threshold_pct ?? entitlements?.warn_threshold_pct ?? 80;
  const showUsageWarning = Boolean(usage?.warnings && usage.warnings.length > 0);
  const enterpriseOverageMessage = formatOverage(usage?.enterprise_overage);

  const initiateCheckout = async (plan: PricingPlan) => {
    if (!storeId) {
      toast({
        title: "Select a store",
        description: "Choose a store before continuing.",
        variant: "destructive",
      });
      return;
    }

    setCheckoutLoading(plan.key);
    try {
      const origin = window.location.origin;
      const response = await apiClient.createCheckoutSession(
        storeId,
        plan.key,
        `${origin}/billing?success=true`,
        `${origin}/billing?canceled=true`,
      );

      if (response.url) {
        window.open(response.url, "_blank");
        toast({
          title: "Checkout opened",
          description: "Complete the subscription in the new tab.",
        });
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === "billing_unconfigured") {
        toast({
          title: "Billing unavailable",
          description: "Stripe is not configured. Contact support.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Checkout failed",
          description: err instanceof Error ? err.message : "Could not create the checkout session",
          variant: "destructive",
        });
      }
    } finally {
      setCheckoutLoading(null);
    }
  };

  const handlePlanAction = (plan: PricingPlan) => {
    if (plan.type === "enterprise" && !isPlanConfigured(plan.key)) {
      setContactPlan(plan);
      setContactOpen(true);
      return;
    }
    void initiateCheckout(plan);
  };

  const handleManageSubscription = async () => {
    if (!storeId) {
      toast({
        title: "Select a store",
        description: "Choose a store before continuing.",
        variant: "destructive",
      });
      return;
    }

    setPortalLoading(true);
    try {
      const origin = window.location.origin;
      const response = await apiClient.createPortalSession(storeId, `${origin}/billing`);

      if (response.portal_url) {
        window.open(response.portal_url, "_blank");
        toast({
          title: "Portal opened",
          description: "Manage your subscription in the new tab.",
        });
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === "billing_unconfigured") {
        toast({
          title: "Billing unavailable",
          description: "Stripe is not configured. Contact support.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Portal unavailable",
          description: err instanceof Error ? err.message : "Could not open the portal",
          variant: "destructive",
        });
      }
    } finally {
      setPortalLoading(false);
    }
  };

  const getPlanBadge = (planKey: string) => {
    if (entitlements && planKey === entitlements.plan) {
      return <Badge className="bg-success text-success-foreground">Current</Badge>;
    }
    return null;
  };

  if (loading) {
    return (
      <div className="max-w-6xl space-y-8">
        <FadeIn className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">Billing & Plans</h1>
          <p className="text-sm text-muted-foreground">Loading billing information...</p>
        </FadeIn>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Card key={index} className="border-none bg-muted/40 p-6">
              <div className="space-y-4">
                <Skeleton className="h-4 w-1/2" />
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-3/4" />
                <div className="space-y-2">
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-2/3" />
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl space-y-8">
      <FadeIn className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Billing & Plans</h1>
        <p className="text-sm text-muted-foreground">
          {storeId
            ? "Manage subscriptions, limits, and upgrades for State Tax Wizard."
            : "Select a store to view billing details."}
        </p>
      </FadeIn>

      {error && (
        <FadeIn variant="fade">
          <Alert variant="destructive" className="border-destructive/50 bg-destructive/10">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </FadeIn>
      )}

      {!storeId && (
        <FadeIn variant="fade" className="rounded-2xl">
          <Card className="border-none bg-muted/40">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-5 w-5 text-warning" />
                <p className="text-sm text-muted-foreground">
                  Choose a store from the selector above to load billing information.
                </p>
              </div>
            </CardContent>
          </Card>
        </FadeIn>
      )}

      {storeId && isTrialing && trialDaysLeft > 0 && (
        <FadeIn>
          <Card className="border-none bg-gradient-to-r from-primary/10 via-primary/5 to-background">
            <CardContent className="p-6">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-3">
                  <Calendar className="h-6 w-6 text-primary" />
                  <div className="space-y-1">
                    <h3 className="text-base font-semibold text-foreground">Active trial period</h3>
                    <p className="text-sm text-muted-foreground">
                      {trialDaysLeft} days remaining. Activate a plan to unlock production features.
                    </p>
                  </div>
                </div>
                <Button className="w-full sm:w-auto hover-lift" onClick={() => handlePlanAction(currentPlan)}>
                  Choose plan
                </Button>
              </div>
            </CardContent>
          </Card>
        </FadeIn>
      )}

      {storeId && entitlements && (
        <FadeIn>
          <Card className="relative border-none bg-background shadow-sm">
            {portalLoading && <LoadingOverlay message="Opening portal" transparent className="rounded-2xl" />}
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg font-semibold">
                <CreditCard className="h-5 w-5 text-primary" />
                Current subscription
              </CardTitle>
            </CardHeader>

            <CardContent className="space-y-5">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold">{currentPlan.displayName}</h3>
                  <p className="text-sm text-muted-foreground">
                    Billed via {entitlements.provider === "shopify" ? "Shopify" : "Stripe"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {limitLabel({
                      ...currentPlan,
                      deliveriesIncluded: entitlements.deliveries_included ?? currentPlan.deliveriesIncluded,
                      commitDeliveries: entitlements.commit_deliveries ?? currentPlan.commitDeliveries,
                    })}
                  </p>
                </div>
                <div className="space-y-2 text-right">
                  <div className="text-3xl font-semibold text-foreground">
                    {currentPlan.monthlyPrice > 0 ? `${formatCurrency(currentPlan.monthlyPrice)}/mo` : "Free"}
                  </div>
                  <Badge
                    className={
                      isTrialing
                        ? "animate-pulse bg-primary text-primary-foreground"
                        : "bg-success/90 text-success-foreground"
                    }
                  >
                    <CheckCircle className="mr-1 h-3 w-3" />
                    {isTrialing ? "Trial" : entitlements.status || "Active"}
                  </Badge>
                </div>
              </div>

              {usage && (
                <div className="space-y-3 rounded-2xl border border-border/60 bg-muted/40 p-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-muted-foreground" />
                      <h4 className="text-sm font-medium">Usage in the current period</h4>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {usage.unlimited
                        ? `${usage.transactions_used} deliveries (unlimited)`
                        : `${usage.transactions_used} / ${usage.transactions_limit} deliveries`}
                    </span>
                  </div>
                  {!usage.unlimited && (
                    <Progress value={Math.min(usagePercentage, 100)} className="h-2 bg-background">
                      {/* indicator handles animation */}
                    </Progress>
                  )}
                  {showUsageWarning && (
                    <Alert className="border-warning/40 bg-warning/10">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        {usage.warnings.map((warning) => (
                          <div key={warning}>{warning}</div>
                        ))}
                      </AlertDescription>
                    </Alert>
                  )}
                  {enterpriseOverageMessage && (
                    <Alert className="border-primary/40 bg-primary/10">
                      <Building className="h-4 w-4" />
                      <AlertDescription>{enterpriseOverageMessage}</AlertDescription>
                    </Alert>
                  )}
                  {!showUsageWarning && !enterpriseOverageMessage && (
                    <p className="text-xs text-muted-foreground">
                      Alert triggers at {warnThreshold}% of the monthly limit.
                    </p>
                  )}
                </div>
              )}

              <div className="rounded-2xl border border-border/60 bg-muted/30 p-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium">Billing method</h4>
                    <p className="text-sm text-muted-foreground">
                      {entitlements.provider === "shopify"
                        ? "Charges consolidated on the monthly Shopify invoice."
                        : "Secure billing via Stripe with VAT support."}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium">Next renewal</h4>
                    <p className="text-sm text-muted-foreground">
                      {isTrialing && entitlements.trial_ends_at
                        ? `Trial ends on ${new Date(entitlements.trial_ends_at).toLocaleDateString()}`
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
                  className="w-full justify-center transition-all hover-lift"
                >
                  {portalLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Opening portal...
                    </>
                  ) : (
                    <>
                      <ExternalLink className="mr-2 h-4 w-4" />
                      Manage subscription
                    </>
                  )}
                </Button>
              )}
            </CardContent>
          </Card>
        </FadeIn>
      )}

      <FadeIn>
        <Card className="border-none bg-background shadow-sm">
          <CardHeader>
            <CardTitle>Core plans</CardTitle>
            <CardDescription>
              Choose the plan that fits your operation best. Every plan includes a 14-day trial.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              {CORE_PLANS.map((plan, index) => {
                const savings = computeAnnualSavings(plan);
                const isCurrent = entitlements?.plan === plan.key;
                const isDisabled = !storeId || isCurrent || checkoutLoading === plan.key;
                const buttonLabel = isCurrent
                  ? "Current plan"
                  : plan.monthlyPrice === 0
                  ? "Activate"
                  : "Select plan";

                return (
                  <FadeIn key={plan.key} delay={index * 0.05} className="h-full">
                    <div
                      className={`relative flex h-full flex-col gap-4 rounded-2xl border p-6 transition-all ${
                        plan.highlight
                          ? "border-primary/60 bg-gradient-to-br from-primary/10 via-background to-background shadow-lg"
                          : "border-border bg-muted/20"
                      } hover-lift`}
                    >
                      {plan.highlight && (
                        <Badge className="absolute -top-3 left-1/2 -translate-x-1/2 animate-pulse bg-primary text-primary-foreground">
                          Most popular
                        </Badge>
                      )}

                      <div className="space-y-2 text-center">
                        <h3 className="flex items-center justify-center gap-2 text-lg font-semibold">
                          {plan.displayName}
                          {getPlanBadge(plan.key)}
                        </h3>
                        <p className="text-sm text-muted-foreground">{plan.description}</p>
                        <div className="mt-3 flex items-baseline justify-center gap-1">
                          <span className="text-3xl font-bold">
                            {plan.monthlyPrice > 0 ? formatCurrency(plan.monthlyPrice) : "Free"}
                          </span>
                          {plan.monthlyPrice > 0 && <span className="text-sm text-muted-foreground">/mo</span>}
                        </div>
                        {plan.annualPrice > 0 && savings !== null && (
                          <p className="text-xs text-muted-foreground">
                            {formatCurrency(plan.annualPrice)}/year (save {savings}% annually)
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground">{limitLabel(plan)}</p>
                      </div>

                      <ul className="space-y-2 text-sm">
                        {plan.features.map((feature) => (
                          <li key={feature} className="flex items-center gap-2 text-left">
                            <CheckCircle className="h-4 w-4 flex-shrink-0 text-success" />
                            {feature}
                          </li>
                        ))}
                      </ul>

                      <Button
                        className="mt-auto w-full justify-center transition-all hover-lift"
                        variant={isCurrent ? "outline" : "default"}
                        disabled={isDisabled}
                        onClick={() => handlePlanAction(plan)}
                      >
                        {checkoutLoading === plan.key ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Processing...
                          </>
                        ) : (
                          buttonLabel
                        )}
                      </Button>
                    </div>
                  </FadeIn>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </FadeIn>

      <FadeIn>
        <Card className="border-none bg-background shadow-sm">
          <CardHeader>
            <CardTitle>Enterprise plans</CardTitle>
            <CardDescription>
              Contract commitments with monitored overage. Configure directly in Stripe or talk to sales.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-3">
              {ENTERPRISE_PLANS.map((plan, index) => {
                const savings = computeAnnualSavings(plan);
                const isCurrent = entitlements?.plan === plan.key;
                const configured = isPlanConfigured(plan.key);
                const buttonLabel = isCurrent
                  ? "Current plan"
                  : configured
                  ? "Configure"
                  : "Contact sales";
                const isDisabled = !storeId || isCurrent || checkoutLoading === plan.key;

                return (
                  <FadeIn key={plan.key} delay={index * 0.05} className="h-full">
                    <div className="relative flex h-full flex-col gap-4 rounded-2xl border border-border/70 bg-muted/10 p-6 hover-lift">
                      <div className="space-y-2 text-center">
                        <h3 className="flex items-center justify-center gap-2 text-lg font-semibold">
                          {plan.displayName}
                          {getPlanBadge(plan.key)}
                        </h3>
                        <p className="text-sm text-muted-foreground">{plan.description}</p>
                        <div className="mt-3 flex items-baseline justify-center gap-1">
                          <span className="text-3xl font-bold">{formatCurrency(plan.monthlyPrice)}</span>
                          <span className="text-sm text-muted-foreground">/mo</span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {formatCurrency(plan.annualPrice)}/year {savings !== null && `(save ${savings}%)`}
                        </p>
                        <p className="text-xs text-muted-foreground">{limitLabel(plan)}</p>
                        {plan.overageFee && (
                          <p className="text-xs text-muted-foreground">
                            Overage billed at {formatCurrency(plan.overageFee)} per delivery
                          </p>
                        )}
                      </div>

                      <ul className="space-y-2 text-sm">
                        {plan.features.map((feature) => (
                          <li key={feature} className="flex items-center gap-2 text-left">
                            <CheckCircle className="h-4 w-4 flex-shrink-0 text-success" />
                            {feature}
                          </li>
                        ))}
                      </ul>

                      <Button
                        className="mt-auto w-full justify-center transition-all hover-lift"
                        variant={isCurrent ? "outline" : "default"}
                        disabled={isDisabled}
                        onClick={() => handlePlanAction(plan)}
                      >
                        {checkoutLoading === plan.key ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Processing...
                          </>
                        ) : (
                          buttonLabel
                        )}
                      </Button>

                      {!configured && !isCurrent && (
                        <p className="text-center text-xs text-muted-foreground">
                          Configure STRIPE_PRICE_ID_* prices to enable automatic checkout.
                        </p>
                      )}
                    </div>
                  </FadeIn>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </FadeIn>

      <Dialog
        open={contactOpen}
        onOpenChange={(nextOpen) => {
          setContactOpen(nextOpen);
          if (!nextOpen) {
            setContactPlan(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Contact sales</DialogTitle>
            <DialogDescription>
              We'll prepare the enterprise contract for {contactPlan?.displayName} for your operation.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              Email <span className="font-medium">sales@statetaxwizard.example</span> with your monthly volume
              ({contactPlan?.commitDeliveries?.toLocaleString()} deliveries) and the billing owner.
            </p>
            <p>
              Our team configures the commitment in Stripe and returns a ready-to-sign checkout within one business day.
            </p>
            <p>
              In the meantime, usage above the commitment is tracked in <code className="font-mono">enterprise_overage_total</code> on the metrics dashboard.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setContactOpen(false)}>
              Close
            </Button>
            <Button onClick={() => {
              window.location.href = "mailto:sales@statetaxwizard.example";
              setContactOpen(false);
            }}>
              Send email
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
