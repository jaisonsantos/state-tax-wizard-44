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
    return `Compromisso de ${plan.commitDeliveries.toLocaleString()} entregas/mês`;
  }
  if (plan.deliveriesIncluded === 0) {
    return "Sem limite de entregas";
  }
  if (plan.deliveriesIncluded) {
    return `Até ${plan.deliveriesIncluded.toLocaleString()} entregas/mês`;
  }
  return "Limite conforme contrato";
};

const formatOverage = (overage: BillingEnterpriseOverage | null | undefined): string | null => {
  if (!overage) {
    return null;
  }
  const fee = overage.overage_fee ? `${currencyFormatter.format(overage.overage_fee)}/entrega` : "consumo registrado";
  return `${overage.overage_units} entregas acima do commit de ${overage.commit_deliveries.toLocaleString()} (${fee}).`;
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
        title: "Erro",
        description: "Selecione uma loja antes de continuar",
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
          title: "Checkout aberto",
          description: "Conclua a assinatura na nova aba",
        });
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === "billing_unconfigured") {
        toast({
          title: "Billing indisponível",
          description: "Stripe não configurado. Fale com o suporte.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Erro",
          description: err instanceof Error ? err.message : "Não foi possível criar a sessão de checkout",
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
        title: "Erro",
        description: "Selecione uma loja antes de continuar",
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
          title: "Portal aberto",
          description: "Gerencie sua assinatura na nova aba",
        });
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === "billing_unconfigured") {
        toast({
          title: "Billing indisponível",
          description: "Stripe não configurado. Fale com o suporte.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Erro",
          description: err instanceof Error ? err.message : "Não foi possível abrir o portal",
          variant: "destructive",
        });
      }
    } finally {
      setPortalLoading(false);
    }
  };

  const getPlanBadge = (planKey: string) => {
    if (entitlements && planKey === entitlements.plan) {
      return <Badge className="bg-success text-success-foreground">Atual</Badge>;
    }
    return null;
  };

  if (loading) {
    return (
      <div className="max-w-6xl space-y-8">
        <FadeIn className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">Billing & Plans</h1>
          <p className="text-sm text-muted-foreground">Carregando informações de billing...</p>
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
            ? "Gerencie assinaturas, limites e upgrades do State Tax Wizard."
            : "Selecione uma loja para visualizar detalhes de billing."}
        </p>
      </FadeIn>

      {error && (
        <FadeIn variant="fade">
          <Alert variant="destructive" className="border-destructive/50 bg-destructive/10">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Erro</AlertTitle>
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
                  Escolha uma loja no seletor acima para carregar as informações de billing.
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
                    <h3 className="text-base font-semibold text-foreground">Período de trial ativo</h3>
                    <p className="text-sm text-muted-foreground">
                      Restam {trialDaysLeft} dias. Ative um plano para liberar recursos de produção.
                    </p>
                  </div>
                </div>
                <Button className="w-full sm:w-auto hover-lift" onClick={() => handlePlanAction(currentPlan)}>
                  Escolher plano
                </Button>
              </div>
            </CardContent>
          </Card>
        </FadeIn>
      )}

      {storeId && entitlements && (
        <FadeIn>
          <Card className="relative border-none bg-background shadow-sm">
            {portalLoading && <LoadingOverlay message="Abrindo portal" transparent className="rounded-2xl" />}
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg font-semibold">
                <CreditCard className="h-5 w-5 text-primary" />
                Assinatura atual
              </CardTitle>
            </CardHeader>

            <CardContent className="space-y-5">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold">{currentPlan.displayName}</h3>
                  <p className="text-sm text-muted-foreground">
                    Faturado via {entitlements.provider === "shopify" ? "Shopify" : "Stripe"}
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
                    {currentPlan.monthlyPrice > 0 ? `${formatCurrency(currentPlan.monthlyPrice)}/mês` : "Gratuito"}
                  </div>
                  <Badge
                    className={
                      isTrialing
                        ? "animate-pulse bg-primary text-primary-foreground"
                        : "bg-success/90 text-success-foreground"
                    }
                  >
                    <CheckCircle className="mr-1 h-3 w-3" />
                    {isTrialing ? "Trial" : entitlements.status || "Ativo"}
                  </Badge>
                </div>
              </div>

              {usage && (
                <div className="space-y-3 rounded-2xl border border-border/60 bg-muted/40 p-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-muted-foreground" />
                      <h4 className="text-sm font-medium">Uso no período atual</h4>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {usage.unlimited
                        ? `${usage.transactions_used} entregas (sem limite)`
                        : `${usage.transactions_used} / ${usage.transactions_limit} entregas`}
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
                      Alerta programado para {warnThreshold}% do limite mensal.
                    </p>
                  )}
                </div>
              )}

              <div className="rounded-2xl border border-border/60 bg-muted/30 p-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium">Forma de cobrança</h4>
                    <p className="text-sm text-muted-foreground">
                      {entitlements.provider === "shopify"
                        ? "Cobrança consolidada na fatura mensal da Shopify."
                        : "Billing seguro via Stripe com suporte a VAT."}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium">Próxima renovação</h4>
                    <p className="text-sm text-muted-foreground">
                      {isTrialing && entitlements.trial_ends_at
                        ? `Trial encerra em ${new Date(entitlements.trial_ends_at).toLocaleDateString()}`
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
                      Abrindo portal...
                    </>
                  ) : (
                    <>
                      <ExternalLink className="mr-2 h-4 w-4" />
                      Gerenciar assinatura
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
            <CardTitle>Planos principais</CardTitle>
            <CardDescription>
              Escolha o plano que melhor se encaixa na sua operação. Todos oferecem trial de 14 dias.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              {CORE_PLANS.map((plan, index) => {
                const savings = computeAnnualSavings(plan);
                const isCurrent = entitlements?.plan === plan.key;
                const isDisabled = !storeId || isCurrent || checkoutLoading === plan.key;
                const buttonLabel = isCurrent
                  ? "Plano atual"
                  : plan.monthlyPrice === 0
                  ? "Ativar"
                  : "Selecionar plano";

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
                          Mais popular
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
                            {plan.monthlyPrice > 0 ? formatCurrency(plan.monthlyPrice) : "Grátis"}
                          </span>
                          {plan.monthlyPrice > 0 && <span className="text-sm text-muted-foreground">/mês</span>}
                        </div>
                        {plan.annualPrice > 0 && savings !== null && (
                          <p className="text-xs text-muted-foreground">
                            {formatCurrency(plan.annualPrice)}/ano (economize {savings}% no anual)
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
                            Processando...
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
            <CardTitle>Planos Enterprise</CardTitle>
            <CardDescription>
              Compromissos sob contrato com overage monitorado. Configure direto via Stripe ou fale com vendas.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-3">
              {ENTERPRISE_PLANS.map((plan, index) => {
                const savings = computeAnnualSavings(plan);
                const isCurrent = entitlements?.plan === plan.key;
                const configured = isPlanConfigured(plan.key);
                const buttonLabel = isCurrent
                  ? "Plano atual"
                  : configured
                  ? "Configurar"
                  : "Fale com vendas";
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
                          <span className="text-sm text-muted-foreground">/mês</span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {formatCurrency(plan.annualPrice)}/ano{" "}
                          {savings !== null && `(economize ${savings}%)`}
                        </p>
                        <p className="text-xs text-muted-foreground">{limitLabel(plan)}</p>
                        {plan.overageFee && (
                          <p className="text-xs text-muted-foreground">
                            Overage registrado a {formatCurrency(plan.overageFee)} por entrega
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
                            Processando...
                          </>
                        ) : (
                          buttonLabel
                        )}
                      </Button>

                      {!configured && !isCurrent && (
                        <p className="text-center text-xs text-muted-foreground">
                          Configure preços STRIPE_PRICE_ID_* para habilitar checkout automático.
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
            <DialogTitle>Fale com vendas</DialogTitle>
            <DialogDescription>
              Vamos montar o contrato enterprise de {contactPlan?.displayName} para sua operação.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              Envie um e-mail para <span className="font-medium">sales@statetaxwizard.example</span> informando o volume mensal
              ({contactPlan?.commitDeliveries?.toLocaleString()} entregas) e o responsável pelo faturamento.
            </p>
            <p>
              Nossa equipe configura o commit no Stripe e devolve o checkout pronto para assinatura em até 1 dia útil.
            </p>
            <p>
              Enquanto isso o uso acima do commit será monitorado em <code className="font-mono">enterprise_overage_total</code> no
              dashboard de métricas.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setContactOpen(false)}>
              Fechar
            </Button>
            <Button onClick={() => {
              window.location.href = "mailto:sales@statetaxwizard.example";
              setContactOpen(false);
            }}>
              Enviar e-mail
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
