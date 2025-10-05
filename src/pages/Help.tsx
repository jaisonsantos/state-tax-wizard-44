import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { FadeIn, LoadingOverlay, EmptyState } from "@/components/patterns";
import { HelpCircle, ExternalLink, Mail, MessageCircle, Book, FileText, MapPin } from "lucide-react";

const faqItems = [
  {
    id: "mn-threshold",
    question: "How does Minnesota's $100 threshold work?",
    answer: "Minnesota charges a $0.50 delivery fee when the total order value (including shipping) meets or exceeds $100 AND the delivery is made by motor vehicle within Minnesota. The threshold includes all items except those specifically exempted by law.",
    category: "minnesota"
  },
  {
    id: "co-taxable-items", 
    question: "What are taxable items in Colorado?",
    answer: "In Colorado, most retail goods are subject to the delivery fee. The fee applies once per transaction when at least one taxable item is delivered by motor vehicle to a Colorado address. Digital goods and services are typically exempt.",
    category: "colorado"
  },
  {
    id: "bopis-exemption",
    question: "Why are BOPIS orders exempt?",
    answer: "Buy Online, Pick In Store (BOPIS) and curbside pickup orders are exempt because they don't involve delivery by motor vehicle to the customer's location. The customer collects the items themselves, so no delivery fee applies.",
    category: "general"
  },
  {
    id: "split-shipments",
    question: "How are split shipments handled?",
    answer: "For Minnesota: Each shipment is evaluated separately against the $100 threshold. For Colorado: Only one delivery fee per original transaction, regardless of how many separate shipments are created.",
    category: "general"
  },
  {
    id: "dr1786-filing",
    question: "How do I file the CO DR-1786 form?",
    answer: "Download the CSV report from our system and use it to complete the DR-1786 form on Colorado's Department of Revenue website. The report includes all required fields: transaction dates, fee amounts, and delivery details.",
    category: "colorado"
  },
  {
    id: "mn-reporting",
    question: "What reporting is required for Minnesota?",
    answer: "Minnesota doesn't require specific forms like Colorado, but you should maintain records of all fees collected. Our MN Summary report provides comprehensive data for your tax professional or internal accounting needs.",
    category: "minnesota"
  }
];

const helpCategories = [
  {
    title: "Minnesota Compliance",
    icon: MapPin,
    color: "bg-minnesota text-minnesota-foreground",
    items: faqItems.filter(item => item.category === "minnesota")
  },
  {
    title: "Colorado Compliance", 
    icon: MapPin,
    color: "bg-colorado text-colorado-foreground",
    items: faqItems.filter(item => item.category === "colorado")
  },
  {
    title: "General Questions",
    icon: HelpCircle,
    color: "bg-muted text-muted-foreground",
    items: faqItems.filter(item => item.category === "general")
  }
];

export default function Help() {
  const [hydrating, setHydrating] = useState(true);

  useEffect(() => {
    const timer = window.setTimeout(() => setHydrating(false), 250);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <div className="relative space-y-6 max-w-4xl">
      <LoadingOverlay visible={hydrating} message="Loading documentation..." tone="muted" />
      <FadeIn className="surface-gradient border border-border/60 rounded-2xl p-6 shadow-[var(--shadow-card)]">
        <div>
          <h1 className="text-3xl font-bold">Help &amp; Documentation</h1>
          <p className="text-muted-foreground">
            Everything you need to know about delivery fee compliance
          </p>
        </div>
      </FadeIn>

      {/* Quick Links */}
      <FadeIn delay={0.1}>
        <Card className="border-glow hover-lift">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Book className="h-5 w-5" />
              Quick Reference
            </CardTitle>
            <CardDescription>
              Essential compliance information and resources
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-3">
                <h4 className="font-medium flex items-center gap-2">
                <Badge className="bg-minnesota text-minnesota-foreground">MN</Badge>
                Minnesota Resources
              </h4>
              <div className="space-y-2">
                <Button variant="outline" size="sm" className="w-full justify-start">
                  <FileText className="h-4 w-4 mr-2" />
                  MN Delivery Fee Law (HF 2887)
                  <ExternalLink className="h-3 w-3 ml-auto" />
                </Button>
                <Button variant="outline" size="sm" className="w-full justify-start">
                  <FileText className="h-4 w-4 mr-2" />
                  MN Department of Revenue Guidance
                  <ExternalLink className="h-3 w-3 ml-auto" />
                </Button>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="font-medium flex items-center gap-2">
                <Badge className="bg-colorado text-colorado-foreground">CO</Badge>
                Colorado Resources
              </h4>
              <div className="space-y-2">
                <Button variant="outline" size="sm" className="w-full justify-start">
                  <FileText className="h-4 w-4 mr-2" />
                  CO Retail Delivery Fee (SB 21-260)
                  <ExternalLink className="h-3 w-3 ml-auto" />
                </Button>
                <Button variant="outline" size="sm" className="w-full justify-start">
                  <FileText className="h-4 w-4 mr-2" />
                  DR-1786 Form Instructions
                  <ExternalLink className="h-3 w-3 ml-auto" />
                </Button>
              </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </FadeIn>

      {/* FAQ Sections */}
      {helpCategories.map((category, index) => (
        <FadeIn key={category.title} delay={0.15 + index * 0.05}>
          <Card className="border-glow hover-lift">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <div className={`h-8 w-8 rounded flex items-center justify-center ${category.color}`}>
                  <category.icon className="h-4 w-4" />
                </div>
                {category.title}
              </CardTitle>
            </CardHeader>

            <CardContent>
              {category.items.length === 0 ? (
                <EmptyState
                  title="No guidance available"
                  description="We’re preparing documentation for this section. Check back soon."
                  tone="bordered"
                />
              ) : (
                <Accordion type="single" collapsible className="w-full">
                  {category.items.map((item) => (
                    <AccordionItem key={item.id} value={item.id}>
                      <AccordionTrigger className="text-left">
                        {item.question}
                      </AccordionTrigger>
                      <AccordionContent className="text-muted-foreground">
                        {item.answer}
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              )}
            </CardContent>
          </Card>
        </FadeIn>
      ))}

      {/* Contact Support */}
      <FadeIn delay={0.25}>
        <Card className="border-glow hover-lift">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5" />
              Contact Support
            </CardTitle>
            <CardDescription>
              Still have questions? We're here to help with compliance and technical issues.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-3">
                <h4 className="font-medium">Technical Support</h4>
              <p className="text-sm text-muted-foreground">
                Help with integration, settings, and troubleshooting
              </p>
              <Button className="w-full">
                <Mail className="h-4 w-4 mr-2" />
                Email Technical Support
              </Button>
            </div>

            <div className="space-y-3">
              <h4 className="font-medium">Compliance Questions</h4>
              <p className="text-sm text-muted-foreground">
                Legal and regulatory guidance from our compliance team
              </p>
              <Button variant="outline" className="w-full">
                <Mail className="h-4 w-4 mr-2" />
                Email Compliance Team
              </Button>
            </div>
          </div>

            <div className="mt-6 p-4 bg-muted rounded-lg">
              <div className="flex items-start gap-3">
                <HelpCircle className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <h4 className="font-medium mb-1">System Status</h4>
                  <p className="text-sm text-muted-foreground">
                    Check our status page for real-time system health and any ongoing maintenance.
                  </p>
                  <Button variant="link" size="sm" className="p-0 mt-1">
                    View Status Page <ExternalLink className="h-3 w-3 ml-1" />
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </FadeIn>
    </div>
  );
}