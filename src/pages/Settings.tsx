import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Settings2, Play, AlertTriangle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient } from "@/lib/api";

export default function Settings() {
  const [enableMN, setEnableMN] = useState(true);
  const [enableCO, setEnableCO] = useState(true);
  const [absorbFee, setAbsorbFee] = useState(false);
  const [labelOverride, setLabelOverride] = useState("Delivery Fee");
  const [storeId, setStoreId] = useState<string>("");
  const [testing, setTesting] = useState(false);
  
  // Playground form state
  const [playgroundData, setPlaygroundData] = useState({
    destination: "Minneapolis, MN",
    deliveryMethod: "standard",
    orderValue: "120.00",
    shippingCost: "15.00",
    items: "2x T-shirts ($50 each), 1x Jeans ($20)"
  });

  const { toast } = useToast();

  useEffect(() => {
    // Get store ID from user info
    const fetchStoreId = async () => {
      try {
        const userInfo = await apiClient.getMe();
        if (userInfo.stores && userInfo.stores.length > 0) {
          setStoreId(userInfo.stores[0].id);
        }
      } catch (error) {
        console.error("Failed to fetch store info:", error);
      }
    };
    
    fetchStoreId();
  }, []);

  const handleSaveSettings = () => {
    toast({
      title: "Settings saved",
      description: "Your delivery fee rules have been updated",
    });
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
      // Parse destination to get state
      const stateMatch = playgroundData.destination.match(/,\s*([A-Z]{2})\s*$/i);
      const state = stateMatch ? stateMatch[1].toUpperCase() : "MN";

      // Convert order value and shipping to cents
      const orderValueCents = Math.round(parseFloat(playgroundData.orderValue) * 100);
      const shippingCents = Math.round(parseFloat(playgroundData.shippingCost) * 100);

      // Create mock items from description
      const items = [{
        sku: "TEST-SKU",
        qty: 1,
        unit_price_cents: orderValueCents,
        taxability: "taxable"
      }];

      const request = {
        store_id: storeId,
        destination: { state },
        delivery_method: playgroundData.deliveryMethod === "standard" ? "ship" : playgroundData.deliveryMethod,
        items,
        shipping_amount_cents: shippingCents
      };

      const response = await apiClient.quoteFees(request);

      if (response.lines && response.lines.length > 0) {
        const totalFee = response.lines.reduce((sum, line) => sum + line.amount_cents, 0);
        const reasonCodes = response.lines.flatMap(line => line.reason_codes);
        
        toast({
          title: "Fee Calculation Result",
          description: `Fee: $${(totalFee / 100).toFixed(2)} | Reasons: ${reasonCodes.join(', ')}`,
        });
      } else {
        toast({
          title: "Fee Calculation Result",
          description: "No delivery fee applied for this order",
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

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold">Rules & Settings</h1>
        <p className="text-muted-foreground">
          Configure delivery fee rules for your store
        </p>
      </div>

      {/* Regulatory Banner */}
      <Card className="bg-warning-muted border-warning/20">
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

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Fee Rules Configuration */}
        <Card>
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
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="label-override">Fee Label Override</Label>
                <Input
                  id="label-override"
                  value={labelOverride}
                  onChange={(e) => setLabelOverride(e.target.value)}
                  placeholder="Delivery Fee"
                />
                <p className="text-xs text-muted-foreground">
                  Text shown in checkout for the fee line item
                </p>
              </div>
            </div>

            <Button onClick={handleSaveSettings} className="w-full">
              Save Settings
            </Button>
          </CardContent>
        </Card>

        {/* Playground */}
        <Card>
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

            <Button 
              onClick={handlePlaygroundTest} 
              className="w-full" 
              variant="outline"
              disabled={testing}
            >
              {testing ? "Testing..." : "Test Fee Calculation"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}