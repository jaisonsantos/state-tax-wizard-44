import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, ExternalLink, Download, Store, CreditCard } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export default function Onboarding() {
  const [shopifyConnected, setShopifyConnected] = useState(false);
  const [wooConnected, setWooConnected] = useState(false);
  const { toast } = useToast();

  const handleShopifyConnect = () => {
    toast({
      title: "Shopify Integration",
      description: "In production, this would redirect to the Shopify App Store",
    });
    setShopifyConnected(true);
  };

  const handleWooConnect = () => {
    toast({
      title: "WooCommerce Plugin Downloaded",
      description: "Follow the installation instructions below",
    });
    setWooConnected(true);
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
              {shopifyConnected && (
                <Badge className="bg-success text-success-foreground">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Connected
                </Badge>
              )}
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
            
            <Button 
              onClick={handleShopifyConnect}
              className="w-full"
              disabled={shopifyConnected}
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              {shopifyConnected ? "App Installed" : "Install Shopify App"}
            </Button>
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
              {wooConnected && (
                <Badge className="bg-success text-success-foreground">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Connected
                </Badge>
              )}
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
            
            <Button 
              onClick={handleWooConnect}
              variant="outline"
              className="w-full"
              disabled={wooConnected}
            >
              <Download className="h-4 w-4 mr-2" />
              {wooConnected ? "Plugin Downloaded" : "Download Plugin ZIP"}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Next Steps */}
      {(shopifyConnected || wooConnected) && (
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
              <Button variant="outline" size="sm">
                Configure Rules
              </Button>
              <Button variant="outline" size="sm">
                Test Integration
              </Button>
              <Button variant="outline" size="sm">
                View Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}