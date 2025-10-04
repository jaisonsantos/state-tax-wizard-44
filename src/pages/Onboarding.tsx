import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, ExternalLink, Download, Store, CreditCard, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/context/AuthContext";
import { apiClient, ApiError, type IntegrationProviderStatus, type IntegrationStatusResponse } from "@/lib/api";

export default function Onboarding() {
  const [integrationStatus, setIntegrationStatus] = useState<IntegrationStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [installingProvider, setInstallingProvider] = useState<string | null>(null);
  const { toast } = useToast();
  const { selectedStoreId: storeId } = useAuth();
  const navigate = useNavigate();

  const refreshStatus = useCallback(async () => {
    if (!storeId) {
      setIntegrationStatus(null);
      return;
    }

    setStatusLoading(true);
    try {
      const status = await apiClient.getIntegrationStatus(storeId);
      setIntegrationStatus(status);
    } catch (error) {
      setIntegrationStatus(null);
      toast({
        title: "Failed to load integrations",
        description: error instanceof Error ? error.message : "Unexpected error",
        variant: "destructive",
      });
    } finally {
      setStatusLoading(false);
    }
  }, [storeId, toast]);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  const shopifyStatus = useMemo(
    () => integrationStatus?.providers.find((provider) => provider.provider === "shopify"),
    [integrationStatus],
  );
  const wooStatus = useMemo(
    () => integrationStatus?.providers.find((provider) => provider.provider === "woocommerce"),
    [integrationStatus],
  );

  const shopifyConnected = shopifyStatus?.connected ?? false;
  const wooConnected = wooStatus?.connected ?? false;
  const hasConnectedProvider = shopifyConnected || wooConnected;

  const handleInstallIntegration = useCallback(
    async (providerStatus: IntegrationProviderStatus) => {
      if (!storeId) {
        toast({
          title: "Select a store",
          description: "Choose or create a store before installing integrations.",
          variant: "destructive",
        });
        return;
      }

      if (!providerStatus.enabled) {
        toast({
          title: "Integration unavailable",
          description: providerStatus.notes ?? "This connector is disabled via feature flag.",
          variant: "destructive",
        });
        return;
      }

      setInstallingProvider(providerStatus.provider);
      const defaultDomain =
        typeof window !== "undefined" ? window.location.hostname || "demo-store.local" : "demo-store.local";

      try {
        await apiClient.installIntegration(providerStatus.provider, storeId, {
          store_domain: defaultDomain,
          external_shop_id:
            providerStatus.provider === "shopify" ? `shopify-${storeId}` : `woo-${storeId}`,
        });

        toast({
          title: "Integration connected",
          description: `${providerStatus.provider} marked as connected.`,
        });

        await refreshStatus();
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
    },
    [storeId, toast, refreshStatus],
  );

  const renderStatusBadge = (status?: IntegrationProviderStatus) => {
    if (!status) {
      return null;
    }

    if (!status.enabled) {
      return (
        <Badge variant="outline" className="border-dashed text-muted-foreground">
          Disabled
        </Badge>
      );
    }

    if (status.connected) {
      return (
        <Badge className="bg-success text-success-foreground">
          <CheckCircle className="h-3 w-3 mr-1" /> Connected
        </Badge>
      );
    }

    return <Badge variant="secondary">Action required</Badge>;
  };

  const handleNavigate = (pathname: string, hash?: string) => {
    const normalisedHash = hash ? (hash.startsWith("#") ? hash : `#${hash}`) : undefined;
    navigate({ pathname, hash: normalisedHash });
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold">Connect Your Store</h1>
        <p className="text-muted-foreground">
          Choose your e-commerce platform to start applying compliant delivery fees
        </p>
      </div>

      {/* Trial Banner */}
      <Card className="bg-primary-muted border-primary/20">
        <CardContent className="p-6">
          <div className="flex items-center gap-3">
            <CreditCard className="h-6 w-6 text-primary" />
            <div>
              <h3 className="font-semibold text-primary">14-Day Free Trial Active</h3>
              <p className="text-sm text-primary/80">
                Full access to all features. No credit card required during trial.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Shopify Integration */}
        <Card className="relative">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Store className="h-8 w-8 text-primary" />
                <div>
                  <CardTitle>Shopify</CardTitle>
                  <CardDescription>Official Shopify App</CardDescription>
                </div>
              </div>
              {renderStatusBadge(shopifyStatus)}
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Install our official Shopify app for seamless checkout integration and automated billing.
            </p>

            <div className="space-y-2">
              <h4 className="font-medium text-sm">Features:</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Automatic fee application at checkout</li>
                <li>• Billing through your Shopify invoice</li>
                <li>• Real-time compliance updates</li>
                <li>• No manual configuration required</li>
              </ul>
            </div>

            <div className="flex flex-col gap-2 sm:flex-row">
              <Button
                onClick={() => shopifyStatus && handleInstallIntegration(shopifyStatus)}
                className="w-full"
                disabled={
                  !shopifyStatus ||
                  !shopifyStatus.enabled ||
                  shopifyStatus.connected ||
                  installingProvider === shopifyStatus.provider
                }
              >
                {installingProvider === "shopify" ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <ExternalLink className="h-4 w-4 mr-2" />
                )}
                {shopifyStatus?.connected
                  ? "App Installed"
                  : installingProvider === "shopify"
                    ? "Connecting…"
                    : shopifyStatus?.enabled
                      ? "Install Shopify App"
                      : "Unavailable"}
              </Button>
              {shopifyStatus?.docs_url && (
                <Button variant="outline" className="w-full" asChild>
                  <a href={shopifyStatus.docs_url} target="_blank" rel="noreferrer">
                    View docs
                  </a>
                </Button>
              )}
            </div>

            {shopifyStatus?.notes && (
              <p className="text-xs text-muted-foreground">{shopifyStatus.notes}</p>
            )}
          </CardContent>
        </Card>

        {/* WooCommerce Integration */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Store className="h-8 w-8 text-colorado" />
                <div>
                  <CardTitle>WooCommerce</CardTitle>
                  <CardDescription>WordPress Plugin</CardDescription>
                </div>
              </div>
              {renderStatusBadge(wooStatus)}
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Download our WooCommerce plugin and connect your store via API.
            </p>
            
            <div className="space-y-2">
              <h4 className="font-medium text-sm">Installation Steps:</h4>
              <ol className="text-sm text-muted-foreground space-y-1">
                <li>1. Download and install the plugin ZIP</li>
                <li>2. Enter your store URL and API credentials</li>
                <li>3. Generate API key in your dashboard</li>
                <li>4. Configure fee settings</li>
              </ol>
            </div>

            <div className="flex flex-col gap-2 sm:flex-row">
              <Button
                onClick={() => wooStatus && handleInstallIntegration(wooStatus)}
                variant="outline"
                className="w-full"
                disabled={
                  !wooStatus ||
                  !wooStatus.enabled ||
                  wooStatus.connected ||
                  installingProvider === wooStatus.provider
                }
              >
                {installingProvider === "woocommerce" ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                {wooStatus?.connected
                  ? "Plugin Connected"
                  : installingProvider === "woocommerce"
                    ? "Marking…"
                    : wooStatus?.enabled
                      ? "Mark WooCommerce Installed"
                      : "Unavailable"}
              </Button>
              {wooStatus?.docs_url && (
                <Button variant="outline" className="w-full" asChild>
                  <a href={wooStatus.docs_url} target="_blank" rel="noreferrer">
                    View docs
                  </a>
                </Button>
              )}
            </div>

            {wooStatus?.notes && (
              <p className="text-xs text-muted-foreground">{wooStatus.notes}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Next Steps */}
      {hasConnectedProvider && (
        <Card>
          <CardHeader>
            <CardTitle>Next Steps</CardTitle>
            <CardDescription>
              Complete your setup to start applying delivery fees
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
              <CheckCircle className="h-5 w-5 text-success" />
              <span className="text-sm">Store connected successfully</span>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleNavigate("/settings", "fee-rules")}
              >
                Configure Rules
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleNavigate("/settings", "rules-playground")}
              >
                Test Integration
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleNavigate("/dashboard")}
              >
                View Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {!storeId && (
        <p className="text-sm text-muted-foreground">
          Select a store from the header to manage integrations.
        </p>
      )}

      {statusLoading && storeId && (
        <p className="text-xs text-muted-foreground">Checking integration status…</p>
      )}
    </div>
  );
}
