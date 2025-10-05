import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FadeIn, LoadingOverlay, EmptyState } from "@/components/patterns";
import { Settings2, Play, AlertTriangle, RotateCw, Copy, Send, Store } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient, ApiError, type IntegrationProviderStatus, type IntegrationStatusResponse } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { getPricingPlanDisplayName } from "@/lib/pricing";

export default function Settings() {
  const [enableMN, setEnableMN] = useState(true);
  const [enableCO, setEnableCO] = useState(true);
  const [absorbFee, setAbsorbFee] = useState(false);
  const [labelOverride, setLabelOverride] = useState("Delivery Fee");
  const [plan, setPlan] = useState<string | null>(null);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [hmacRotatedAt, setHmacRotatedAt] = useState<string | null>(null);
  const [rotatingSecret, setRotatingSecret] = useState(false);
  const [lastRotatedSecret, setLastRotatedSecret] = useState<string | null>(null);
  const [webhookActive, setWebhookActive] = useState(false);
  const [webhookEndpoint, setWebhookEndpoint] = useState("");
  const [webhookEvents, setWebhookEvents] = useState<string[]>([]);
  const [applyResult, setApplyResult] = useState<{
    totalFeeCents: number;
    reasonCodes: string[];
    absorbed: boolean;
  } | null>(null);
  const [integrationsLoading, setIntegrationsLoading] = useState(false);
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatusResponse | null>(null);
  const [installingProvider, setInstallingProvider] = useState<string | null>(null);
  const lastSettingsStoreRef = useRef<string | null>(null);

  const overlayMessage = useMemo(() => {
    if (settingsLoading) {
      return "Loading store configuration...";
    }
    if (settingsSaving) {
      return "Saving settings...";
    }
    return null;
  }, [settingsLoading, settingsSaving]);

  const showOverlay = overlayMessage !== null;
  
  // Playground form state
  const [playgroundData, setPlaygroundData] = useState({
    destination: "Minneapolis, MN",
    deliveryMethod: "standard",
    orderValue: "120.00",
    shippingCost: "15.00",
    items: "2x T-shirts ($50 each), 1x Jeans ($20)"
  });

  const { toast } = useToast();

  const { selectedStoreId: storeId, stores } = useAuth();

  const webhookEventOptions = useMemo(
    () => [
      { value: "fee.applied", label: "Fee applied" },
      { value: "fee.skipped", label: "Fee skipped" },
      { value: "report.ready", label: "Report ready" },
      { value: "hmac.rotated", label: "HMAC rotated" },
    ],
    [],
  );

  const storeName = useMemo(() => {
    return stores.find((store) => store.id === storeId)?.name ?? "";
  }, [stores, storeId]);

  const formattedHmacRotation = useMemo(() => {
    if (!hmacRotatedAt) {
      return null;
    }
    const parsed = new Date(hmacRotatedAt);
    if (Number.isNaN(parsed.getTime())) {
      return hmacRotatedAt;
    }
    return parsed.toLocaleString();
  }, [hmacRotatedAt]);

  const displayPlan = useMemo(() => getPricingPlanDisplayName(plan), [plan]);

  const refreshIntegrations = useCallback(() => {
    if (!storeId) {
      setIntegrationStatus(null);
      return;
    }

    setIntegrationsLoading(true);
    apiClient
      .getIntegrationStatus(storeId)
      .then((status) => {
        setIntegrationStatus(status);
      })
      .catch((error: unknown) => {
        toast({
          title: "Failed to load integrations",
          description: error instanceof Error ? error.message : "Unexpected error",
          variant: "destructive",
        });
      })
      .finally(() => setIntegrationsLoading(false));
  }, [storeId, toast]);

  const describeHmacError = (error: ApiError): string => {
    switch (error.code) {
      case "missing_signature":
        return "Request signature missing. Refresh the page and try again.";
      case "invalid_signature":
        return "Signature verification failed. Confirm the HMAC secret configured for this store.";
      case "stale_timestamp":
        return "Signature expired. Ensure your integration sends UTC timestamps within the 5-minute window.";
      case "replay_detected":
        return "Replay detected. Generate a new nonce for each request before retrying.";
      case "missing_nonce":
        return "Nonce header missing. Include X-Taxo-Nonce when signing requests.";
      default:
        return error.message;
    }
  };

  const integrationDocsLink = (provider: IntegrationProviderStatus): string => {
    if (provider.docs_url && provider.docs_url.startsWith("http")) {
      return provider.docs_url;
    }
    return provider.docs_url || "/api/files/docs/integrations/README.md";
  };

  const handleInstallIntegration = async (provider: IntegrationProviderStatus) => {
    if (!storeId) {
      toast({
        title: "Select a store",
        description: "Choose a store before installing integrations.",
        variant: "destructive",
      });
      return;
    }

    setInstallingProvider(provider.provider);
    const defaultDomain = typeof window !== "undefined" ? window.location.hostname || "demo-store.local" : "demo-store.local";

    try {
      await apiClient.installIntegration(provider.provider, storeId, {
        store_domain: defaultDomain,
        external_shop_id: provider.provider === "shopify" ? `shopify-${storeId}` : `woo-${storeId}`,
      });
      toast({
        title: "Integration connected",
        description: `${provider.provider} marked as connected.`,
      });
      refreshIntegrations();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Unexpected error";
      toast({
        title: "Failed to install integration",
        description: message,
        variant: "destructive",
      });
    } finally {
      setInstallingProvider(null);
    }
  };

  useEffect(() => {
    if (!storeId) {
      setPlan(null);
      setEnableMN(true);
      setEnableCO(true);
      setAbsorbFee(false);
      setLabelOverride("Delivery Fee");
      setHmacRotatedAt(null);
      setLastRotatedSecret(null);
      setWebhookActive(false);
      setWebhookEndpoint("");
      setWebhookEvents([]);
      setIntegrationStatus(null);
      setSettingsLoading(false);
      setIntegrationsLoading(false);
      lastSettingsStoreRef.current = null;
      return;
    }

    if (lastSettingsStoreRef.current === storeId) {
      return;
    }

    lastSettingsStoreRef.current = storeId;

    let cancelled = false;
    setSettingsLoading(true);
    setLastRotatedSecret(null);

    apiClient
      .getStoreSettings(storeId)
      .then((settings) => {
        if (cancelled) return;
        setEnableMN(settings.enable_mn);
        setEnableCO(settings.enable_co);
        setAbsorbFee(settings.absorb_fee);
        setLabelOverride(settings.label_override);
        setPlan(settings.plan ?? null);
        setHmacRotatedAt(settings.hmac_last_rotated_at ?? null);
        setWebhookActive(settings.webhook_active);
        setWebhookEndpoint(settings.webhook_endpoint ?? "");
        setWebhookEvents(settings.webhook_events ?? []);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        toast({
          title: "Failed to load settings",
          description: error instanceof Error ? error.message : "Unexpected error",
          variant: "destructive",
        });
      })
      .finally(() => {
        if (cancelled) return;
        setSettingsLoading(false);
        refreshIntegrations();
      });

    return () => {
      cancelled = true;
    };
  }, [storeId, toast, refreshIntegrations]);

  const handleSaveSettings = async () => {
    if (!storeId) {
      toast({
        title: "Select a store",
        description: "Choose a store before saving settings.",
        variant: "destructive",
      });
      return;
    }

    setSettingsSaving(true);
    try {
      const payload = {
        enable_mn: enableMN,
        enable_co: enableCO,
        absorb_fee: absorbFee,
        label_override: labelOverride,
        webhook_active: webhookActive,
        webhook_endpoint: webhookEndpoint.trim() ? webhookEndpoint.trim() : null,
        webhook_events: webhookEvents,
      };
      const updated = await apiClient.updateStoreSettings(storeId, payload);
      setEnableMN(updated.enable_mn);
      setEnableCO(updated.enable_co);
      setAbsorbFee(updated.absorb_fee);
      setLabelOverride(updated.label_override);
      setPlan(updated.plan ?? null);
      setHmacRotatedAt(updated.hmac_last_rotated_at ?? null);
      setWebhookActive(updated.webhook_active);
      setWebhookEndpoint(updated.webhook_endpoint ?? "");
      setWebhookEvents(updated.webhook_events ?? []);

      toast({
        title: "Settings saved",
        description: "Your delivery fee rules have been updated",
      });
    } catch (error) {
      toast({
        title: "Failed to save settings",
        description: error instanceof Error ? error.message : "Unexpected error",
        variant: "destructive",
      });
    } finally {
      setSettingsSaving(false);
    }
  };

  const toggleWebhookEvent = (value: string) => {
    setWebhookEvents((previous) => {
      if (previous.includes(value)) {
        return previous.filter((event) => event !== value);
      }
      return [...previous, value];
    });
  };

  const handleRotateSecret = async () => {
    if (!storeId) {
      toast({
        title: "Select a store",
        description: "Choose a store before rotating the HMAC secret.",
        variant: "destructive",
      });
      return;
    }

    setRotatingSecret(true);
    try {
      const response = await apiClient.rotateHmacSecret(storeId);
      setHmacRotatedAt(response.rotated_at ?? null);
      setLastRotatedSecret(response.hmac_secret);

      toast({
        title: "HMAC secret rotated",
        description:
          "All future signatures must use the new secret. Copy it now and store it securely.",
      });
    } catch (error) {
      toast({
        title: "Failed to rotate secret",
        description: error instanceof Error ? error.message : "Unexpected error",
        variant: "destructive",
      });
    } finally {
      setRotatingSecret(false);
    }
  };

  const handleCopySecret = async () => {
    if (!lastRotatedSecret) {
      return;
    }

    if (typeof navigator === "undefined" || !navigator.clipboard) {
      toast({
        title: "Clipboard unavailable",
        description: "Copy this value manually from the field below.",
        variant: "destructive",
      });
      return;
    }

    try {
      await navigator.clipboard.writeText(lastRotatedSecret);
      toast({
        title: "Secret copied",
        description: "Store it in your password manager or secrets vault.",
      });
    } catch (error) {
      toast({
        title: "Failed to copy",
        description: error instanceof Error ? error.message : "Copy command was blocked.",
        variant: "destructive",
      });
    }
  };

  const controlsDisabled = settingsLoading || settingsSaving || !storeId;

  const buildFeeRequest = () => {
    if (!storeId) {
      throw new Error("No store selected");
    }

    const stateMatch = playgroundData.destination.match(/,\s*([A-Z]{2})\s*$/i);
    const state = stateMatch ? stateMatch[1].toUpperCase() : "MN";

    const normalizedOrderValue = playgroundData.orderValue.replace(',', '.');
    const normalizedShipping = playgroundData.shippingCost.replace(',', '.');

    const orderValueCents = Math.round((parseFloat(normalizedOrderValue || "0") || 0) * 100);
    const shippingCents = Math.round((parseFloat(normalizedShipping || "0") || 0) * 100);

    const items = [{
      sku: "TEST-SKU",
      qty: 1,
      unit_price_cents: orderValueCents,
      taxability: "taxable"
    }];

    return {
      store_id: storeId,
      destination: { state },
      delivery_method: playgroundData.deliveryMethod === "standard" ? "ship" : playgroundData.deliveryMethod,
      items,
      shipping_amount_cents: shippingCents
    };
  };

  const handlePlaygroundTest = async () => {
    if (!storeId) {
      toast({
        title: "Error",
        description: "No store selected",
        variant: "destructive",
      });
      return;
    }

    setTesting(true);
    
    try {
      const request = buildFeeRequest();
      const response = await apiClient.quoteFees(request);

      if (response.lines && response.lines.length > 0) {
        const totalFee = response.lines.reduce((sum, line) => sum + line.amount_cents, 0);
        const reasonCodes = response.lines.flatMap((line) => line.reason_codes);

        toast({
          title: "Fee Calculation Result",
          description: `Fee: $${(totalFee / 100).toFixed(2)} | Reasons: ${reasonCodes.join(", ")}`,
        });
      } else {
        toast({
          title: "Fee Calculation Result",
          description:
            response.decisions
              .filter((decision) => decision.outcome === "skipped")
              .map((decision) => `${decision.jurisdiction}: ${decision.reason_codes.join(", ")}`)
              .join(" | ") || "No delivery fee applied for this order",
        });
      }
    } catch (error) {
      toast({
        title: "Calculation Error",
        description: error instanceof Error ? error.message : "Failed to calculate fee",
        variant: "destructive",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleApplyDemo = async () => {
    if (!storeId) {
      toast({
        title: "Error",
        description: "No store selected",
        variant: "destructive",
      });
      return;
    }

    setTesting(true);
    try {
      const request = buildFeeRequest();
      const response = await apiClient.applyFees({
        ...request,
        order_id: `demo-order-${Date.now()}`,
      });

      const totalFeeCents = response.lines.reduce((sum, line) => sum + line.amount_cents, 0);
      const reasonCodes = response.lines.flatMap((line) => line.reason_codes);

      setApplyResult({ totalFeeCents, reasonCodes, absorbed: response.absorbed });

      toast({
        title: response.absorbed ? "Fee absorbed" : "Fee applied",
        description:
          totalFeeCents > 0
            ? `Fee: $${(totalFeeCents / 100).toFixed(2)} | Reasons: ${reasonCodes.join(", ")}`
            : response.decisions
                .filter((decision) => decision.outcome === "skipped")
                .map((decision) => `${decision.jurisdiction}: ${decision.reason_codes.join(", ")}`)
                .join(" | ") || "No delivery fee applied for this order",
      });
    } catch (error) {
      setApplyResult(null);
      const description =
        error instanceof ApiError
          ? `${describeHmacError(error)} Review docs/security/hmac.md for integration steps.`
          : error instanceof Error
            ? error.message
            : "Failed to apply fee";
      toast({
        title: "Apply Error",
        description,
        variant: "destructive",
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="relative space-y-6 max-w-4xl">
      <LoadingOverlay visible={showOverlay} message={overlayMessage ?? ""} tone="muted" />
      <FadeIn className="surface-gradient border border-border/60 rounded-2xl p-6 shadow-[var(--shadow-card)]">
        <div>
          <h1 className="text-3xl font-bold">Rules &amp; Settings</h1>
          <p className="text-muted-foreground">
            Configure delivery fee rules for {storeName || "your store"}
          </p>
          {displayPlan && (
            <p className="mt-1 text-xs text-muted-foreground">
              Current plan: <span className="font-medium text-foreground">{displayPlan}</span>
            </p>
          )}
          <p className="mt-2 text-xs text-muted-foreground">
            Signed requests are required when using the Apply endpoint. Review <span className="font-medium text-foreground">docs/security/hmac.md</span> for header, nonce, and rotation guidance.
          </p>
          {formattedHmacRotation && (
            <p className="mt-1 text-xs text-muted-foreground">
              HMAC secret last rotated: <span className="font-medium text-foreground">{formattedHmacRotation}</span>
            </p>
          )}
        </div>
      </FadeIn>

      {!storeId && (
        <FadeIn delay={0.1}>
          <EmptyState
            icon={Store}
            title="Select a store to manage rules"
            description="Choose a demo store from the header to enable editing and webhooks."
            tone="muted"
          />
        </FadeIn>
      )}

      {/* Regulatory Banner */}
      <FadeIn delay={0.15}>
        <Card className="border border-warning/30 bg-warning-muted hover-lift shadow-[var(--shadow-card)]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-warning" />
              <div>
                <p className="font-medium text-warning-foreground">Regulatory Update</p>
                <p className="text-sm text-warning-foreground/80">
                  Colorado rate schedule updated July 1st. Minnesota threshold remains $100.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </FadeIn>

      <FadeIn delay={0.2}>
        <Card className="relative border-glow hover-lift">
          <LoadingOverlay visible={rotatingSecret} message="Rotating HMAC secret..." tone="muted" />
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <RotateCw className="h-5 w-5" />
              HMAC Secret Management
            </CardTitle>
            <CardDescription>
              Rotate your signing secret to invalidate compromised credentials.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Rotating the secret immediately blocks existing signatures. Generate a new secret before distributing
              credentials to your commerce platform.
            </p>
            <div className="flex flex-wrap items-center gap-3">
            <Button
              onClick={handleRotateSecret}
              variant="outline"
              disabled={rotatingSecret || !storeId}
            >
              <RotateCw className="mr-2 h-4 w-4" />
              {rotatingSecret ? "Rotating…" : "Rotate HMAC Secret"}
            </Button>
            <p className="text-xs text-muted-foreground">
              Ensure all integrations update their stored secret after rotation.
            </p>
          </div>
          {lastRotatedSecret && (
            <div className="space-y-3 rounded-md border border-sky-300 bg-sky-100 p-4 text-sky-900">
              <p className="text-sm font-medium">
                New secret generated — copy it now. This value will not be shown again.
              </p>
              <Textarea
                value={lastRotatedSecret}
                readOnly
                rows={3}
                className="font-mono text-xs bg-white text-sky-900"
              />
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="secondary" size="sm" onClick={handleCopySecret}>
                  <Copy className="mr-2 h-4 w-4" /> Copy secret
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setLastRotatedSecret(null)}
                >
                  Dismiss
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
      </FadeIn>

      <FadeIn delay={0.25}>
        <Card id="webhook-delivery" className="border-glow hover-lift">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Send className="h-5 w-5" />
              Webhook Delivery
            </CardTitle>
            <CardDescription>
              Configure the endpoint that receives Taxo webhook events and select the event types to deliver.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center justify-between gap-3">
              <div className="space-y-1">
                <p className="font-medium">Enable webhooks</p>
                <p className="text-xs text-muted-foreground">
                  When enabled, fee and report lifecycle events are signed with your HMAC secret and POSTed to the endpoint below.
                </p>
              </div>
              <Switch
                checked={webhookActive}
                onCheckedChange={setWebhookActive}
                disabled={controlsDisabled}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="webhook-endpoint">Delivery endpoint URL</Label>
              <Input
                id="webhook-endpoint"
                placeholder="https://example.com/webhooks/taxo"
                value={webhookEndpoint}
                onChange={(event) => setWebhookEndpoint(event.target.value)}
                disabled={!webhookActive || controlsDisabled}
                inputMode="url"
              />
              <p className="text-xs text-muted-foreground">
                The destination must accept HTTPS POST requests with the <span className="font-medium">X-Taxo-*
              </span> headers.
              </p>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium">Subscribed events</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {webhookEventOptions.map((option) => (
                  <label
                    key={option.value}
                    className="flex items-center gap-3 rounded-md border border-border bg-muted/40 p-3 text-sm"
                  >
                    <Checkbox
                      checked={webhookEvents.includes(option.value)}
                      onCheckedChange={() => toggleWebhookEvent(option.value)}
                      disabled={!webhookActive || controlsDisabled}
                    />
                    <span>{option.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-muted-foreground/20 bg-muted/60 p-4">
                <h4 className="font-medium">Payload Example</h4>
                <p className="text-xs text-muted-foreground">
                  Requests are signed with <span className="font-medium">X-Taxo-Signature</span> and <span className="font-medium">X-Taxo-Timestamp</span> headers.
                </p>
              </div>
              <div className="rounded-lg border border-muted-foreground/20 bg-muted/60 p-4">
                <h4 className="font-medium">Replay Protection</h4>
                <p className="text-xs text-muted-foreground">
                  Reject requests where the nonce or timestamp is older than 5 minutes to avoid replay attacks.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </FadeIn>
      <FadeIn delay={0.3}>
        <Card id="integrations" className="relative border-glow hover-lift">
          <LoadingOverlay
            visible={integrationsLoading || Boolean(installingProvider)}
            message={installingProvider ? `Connecting ${installingProvider}…` : 'Refreshing integration status...'}
            tone="muted"
          />
          <CardHeader>
            <CardTitle>Integrations</CardTitle>
            <CardDescription>
              Review platform connector status and align with the WooCommerce/Shopify deployment guides.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {integrationsLoading && (
              <p className="text-sm text-muted-foreground">Loading integration providers…</p>
            )}
            {!integrationsLoading && integrationStatus && (
              <div className="space-y-3">
                {integrationStatus.providers.map((provider) => (
                  <div key={provider.provider} className="flex flex-col gap-2 rounded-lg border border-border p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-medium capitalize">{provider.provider}</p>
                        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                          <Badge variant={provider.connected ? 'default' : provider.enabled ? 'secondary' : 'outline'}>
                            {provider.status}
                          </Badge>
                          {provider.notes && <span>{provider.notes}</span>}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="outline" asChild>
                          <a href={integrationDocsLink(provider)} target="_blank" rel="noreferrer">
                            View docs
                          </a>
                        </Button>
                        {provider.enabled && !provider.connected && (
                          <Button
                            onClick={() => handleInstallIntegration(provider)}
                            disabled={installingProvider === provider.provider}
                          >
                            {installingProvider === provider.provider ? 'Connecting…' : 'Mark as connected'}
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {!integrationsLoading && !integrationStatus && (
              <p className="text-sm text-muted-foreground">Select a store to view integration status.</p>
            )}
          </CardContent>
        </Card>
      </FadeIn>
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Fee Rules Configuration */}
        <FadeIn delay={0.35}>
          <Card id="fee-rules" className="border-glow hover-lift">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings2 className="h-5 w-5" />
              Fee Rules
            </CardTitle>
            <CardDescription>
              Configure which states apply delivery fees
            </CardDescription>
          </CardHeader>
          
            <CardContent className="space-y-6">
            {/* Minnesota Settings */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Badge className="bg-minnesota text-minnesota-foreground">MN</Badge>
                  <div>
                    <Label htmlFor="enable-mn" className="font-medium">Minnesota</Label>
                    <p className="text-xs text-muted-foreground">$0.50 fee when order + shipping ≥ $100</p>
                  </div>
                </div>
                <Switch
                  id="enable-mn"
                  checked={enableMN}
                  onCheckedChange={setEnableMN}
                  disabled={controlsDisabled}
                />
              </div>
            </div>

            {/* Colorado Settings */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Badge className="bg-colorado text-colorado-foreground">CO</Badge>
                  <div>
                    <Label htmlFor="enable-co" className="font-medium">Colorado</Label>
                    <p className="text-xs text-muted-foreground">1 fee per transaction with taxable items</p>
                  </div>
                </div>
                <Switch
                  id="enable-co"
                  checked={enableCO}
                  onCheckedChange={setEnableCO}
                  disabled={controlsDisabled}
                />
              </div>
            </div>

            {/* Additional Options */}
            <div className="space-y-4 pt-4 border-t">
              <div className="flex items-center justify-between">
                <Label htmlFor="absorb-fee" className="flex flex-col gap-1">
                  <span>Absorb Fee</span>
                  <span className="text-xs text-muted-foreground">Don't show fee line in checkout</span>
                </Label>
                <Switch
                  id="absorb-fee"
                  checked={absorbFee}
                  onCheckedChange={setAbsorbFee}
                  disabled={controlsDisabled}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="label-override">Fee Label Override</Label>
                <Input
                  id="label-override"
                  value={labelOverride}
                  onChange={(e) => setLabelOverride(e.target.value)}
                  disabled={controlsDisabled}
                  placeholder="Delivery Fee"
                />
                <p className="text-xs text-muted-foreground">
                  Text shown in checkout for the fee line item
                </p>
              </div>
            </div>

            <Button onClick={handleSaveSettings} className="w-full" disabled={controlsDisabled}>
              {settingsSaving ? "Saving..." : "Save Settings"}
            </Button>
            {settingsLoading && (
              <p className="text-xs text-muted-foreground text-center">Loading current settings…</p>
            )}
            </CardContent>
          </Card>
        </FadeIn>
        {/* Playground */}
        <FadeIn delay={0.4}>
          <Card id="rules-playground" className="relative border-glow hover-lift">
            <LoadingOverlay visible={testing} message="Running sandbox simulation..." tone="muted" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Play className="h-5 w-5" />
                Rules Playground
              </CardTitle>
              <CardDescription>
                Test fee calculations with sample orders
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="space-y-2">
              <Label htmlFor="destination">Delivery Destination</Label>
              <Input
                id="destination"
                value={playgroundData.destination}
                onChange={(e) => setPlaygroundData(prev => ({ ...prev, destination: e.target.value }))}
                placeholder="City, State"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="delivery-method">Delivery Method</Label>
              <Select value={playgroundData.deliveryMethod} onValueChange={(value) => 
                setPlaygroundData(prev => ({ ...prev, deliveryMethod: value }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="standard">Standard Delivery</SelectItem>
                  <SelectItem value="bopis">Buy Online, Pick In Store</SelectItem>
                  <SelectItem value="curbside">Curbside Pickup</SelectItem>
                </SelectContent>
              </Select>
              </div>

              <div className="grid gap-4 grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="order-value">Order Value</Label>
                <Input
                  id="order-value"
                  type="number"
                  step="0.01"
                  value={playgroundData.orderValue}
                  onChange={(e) => setPlaygroundData(prev => ({ ...prev, orderValue: e.target.value }))}
                  placeholder="0.00"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="shipping-cost">Shipping Cost</Label>
                <Input
                  id="shipping-cost"
                  type="number"
                  step="0.01"
                  value={playgroundData.shippingCost}
                  onChange={(e) => setPlaygroundData(prev => ({ ...prev, shippingCost: e.target.value }))}
                  placeholder="0.00"
                />
              </div>
              </div>

              <div className="space-y-2">
              <Label htmlFor="items">Items</Label>
              <Textarea
                id="items"
                value={playgroundData.items}
                onChange={(e) => setPlaygroundData(prev => ({ ...prev, items: e.target.value }))}
                placeholder="Describe the items in the cart"
                rows={3}
              />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
              <Button
                onClick={handlePlaygroundTest}
                className="w-full"
                variant="outline"
                disabled={testing || !storeId}
              >
                {testing ? "Testing..." : "Test Fee Calculation"}
              </Button>
              <Button
                onClick={handleApplyDemo}
                className="w-full"
                disabled={testing || !storeId}
              >
                {testing ? "Applying..." : "Apply Fee (demo)"}
              </Button>
              </div>

              {applyResult && (
                <div className="rounded-md border border-muted p-3 text-sm text-muted-foreground space-y-1">
                <p>
                  Demo fee total: <span className="font-medium text-foreground">${(applyResult.totalFeeCents / 100).toFixed(2)}</span>
                </p>
                <p>
                  Reason codes: {applyResult.reasonCodes.length > 0 ? applyResult.reasonCodes.join(', ') : 'None'}
                </p>
                <p>
                  Status: {applyResult.absorbed ? (
                    <span className="font-medium text-foreground">Absorbed</span>
                  ) : (
                    <span className="font-medium text-foreground">Shown</span>
                  )}
                </p>
                </div>
              )}
            </CardContent>
          </Card>
        </FadeIn>
      </div>
    </div>
  );
}
