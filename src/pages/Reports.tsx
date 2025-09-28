import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FileText, Download, Calendar, Filter } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiClient, downloadBlob } from "@/lib/api";

const exportHistory = [
  {
    id: 1,
    type: "CO DR-1786",
    period: "Q3 2024",
    generatedAt: "2024-10-01 09:30",
    status: "completed",
    fileSize: "45 KB"
  },
  {
    id: 2,
    type: "MN Summary",
    period: "Sep 2024",
    generatedAt: "2024-10-01 09:15", 
    status: "completed",
    fileSize: "12 KB"
  },
  {
    id: 3,
    type: "CO DR-1786",
    period: "Q2 2024",
    generatedAt: "2024-07-01 14:22",
    status: "completed",
    fileSize: "38 KB"
  },
  {
    id: 4,
    type: "MN Summary",
    period: "Jun 2024",
    generatedAt: "2024-07-01 14:20",
    status: "completed",
    fileSize: "8 KB"
  }
];

export default function Reports() {
  const [startDate, setStartDate] = useState("2024-07-01");
  const [endDate, setEndDate] = useState("2024-09-30");
  const [reportFormat, setReportFormat] = useState("csv");
  const [storeId, setStoreId] = useState<string>("");
  const [loading, setLoading] = useState(false);
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

  const handleGenerateReport = async (type: string) => {
    if (!storeId) {
      toast({
        title: "Error",
        description: "No store selected",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    
    try {
      toast({
        title: `${type} Report Generation Started`,
        description: "Your report is being generated and will download shortly",
      });

      let blob: Blob;
      let filename: string;

      if (type === "CO DR-1786") {
        blob = await apiClient.downloadCOReport(storeId, startDate, endDate);
        filename = `CO_DR1786_${startDate}_${endDate}.csv`;
      } else {
        blob = await apiClient.downloadMNReport(storeId, startDate, endDate, reportFormat);
        filename = `MN_Summary_${startDate}_${endDate}.${reportFormat}`;
      }

      downloadBlob(blob, filename);

      toast({
        title: `${type} Report Downloaded`,
        description: "Your report has been successfully generated and downloaded",
      });
    } catch (error) {
      toast({
        title: "Report Generation Failed",
        description: error instanceof Error ? error.message : "Failed to generate report",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-3xl font-bold">Reports</h1>
        <p className="text-muted-foreground">
          Generate and download compliance reports for tax filing
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Colorado DR-1786 Report */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="h-8 w-8 rounded bg-colorado/10 flex items-center justify-center">
                <FileText className="h-4 w-4 text-colorado" />
              </div>
              Colorado DR-1786
            </CardTitle>
            <CardDescription>
              Official Colorado Department of Revenue form for delivery fee reporting
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="grid gap-3 grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="co-start-date">Start Date</Label>
                  <Input
                    id="co-start-date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="co-end-date">End Date</Label>
                  <Input
                    id="co-end-date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="co-format">Format</Label>
                <Select value={reportFormat} onValueChange={setReportFormat}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="csv">CSV (Recommended)</SelectItem>
                    <SelectItem value="xlsx">Excel (XLSX)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="p-3 bg-colorado-muted rounded-lg">
              <h4 className="font-medium text-sm mb-2">Report Includes:</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Transaction dates and order IDs</li>
                <li>• Fee amounts per delivery</li>
                <li>• Delivery method classification</li>
                <li>• Compliance reason codes</li>
              </ul>
            </div>

            <Button 
              onClick={() => handleGenerateReport("CO DR-1786")} 
              className="w-full"
              disabled={loading}
            >
              <Download className="h-4 w-4 mr-2" />
              Generate CO DR-1786 Report
            </Button>
          </CardContent>
        </Card>

        {/* Minnesota Summary Report */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <div className="h-8 w-8 rounded bg-minnesota/10 flex items-center justify-center">
                <FileText className="h-4 w-4 text-minnesota" />
              </div>
              Minnesota Summary
            </CardTitle>
            <CardDescription>
              Comprehensive summary report for Minnesota delivery fee compliance
            </CardDescription>
          </CardHeader>
          
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="grid gap-3 grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="mn-start-date">Start Date</Label>
                  <Input
                    id="mn-start-date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="mn-end-date">End Date</Label>
                  <Input
                    id="mn-end-date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="mn-format">Format</Label>
                <Select value={reportFormat} onValueChange={setReportFormat}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="csv">CSV</SelectItem>
                    <SelectItem value="json">JSON</SelectItem>
                    <SelectItem value="xlsx">Excel (XLSX)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="p-3 bg-minnesota-muted rounded-lg">
              <h4 className="font-medium text-sm mb-2">Report Includes:</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Total fees collected by month</li>
                <li>• Threshold compliance rates</li>
                <li>• BOPIS/curbside exemptions</li>
                <li>• Order volume analytics</li>
              </ul>
            </div>

            <Button 
              onClick={() => handleGenerateReport("MN Summary")} 
              className="w-full" 
              variant="outline"
              disabled={loading}
            >
              <Download className="h-4 w-4 mr-2" />
              Generate MN Summary Report
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Export History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Export History
          </CardTitle>
          <CardDescription>
            Previously generated reports and downloads
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Report Type</TableHead>
                <TableHead>Period</TableHead>
                <TableHead>Generated</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {exportHistory.map((export_) => (
                <TableRow key={export_.id}>
                  <TableCell>
                    <Badge variant={export_.type.includes("CO") ? "default" : "secondary"}
                           className={export_.type.includes("CO") ? "bg-colorado text-colorado-foreground" : "bg-minnesota text-minnesota-foreground"}>
                      {export_.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium">{export_.period}</TableCell>
                  <TableCell className="text-muted-foreground">{export_.generatedAt}</TableCell>
                  <TableCell>
                    <Badge className="bg-success text-success-foreground">
                      {export_.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{export_.fileSize}</TableCell>
                  <TableCell>
                    <Button size="sm" variant="outline">
                      <Download className="h-3 w-3 mr-1" />
                      Download
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}