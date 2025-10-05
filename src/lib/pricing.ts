export interface PricingPlanDefinition {
  key: string;
  displayName: string;
  monthlyPrice: number;
  annualPrice: number;
  description: string;
  features: string[];
  type: "core" | "enterprise";
  deliveriesIncluded?: number;
  commitDeliveries?: number;
  overageFee?: number | null;
  highlight?: boolean;
}

export const CORE_PRICING_PLANS: PricingPlanDefinition[] = [
  {
    key: "free",
    displayName: "Free / Dev",
    monthlyPrice: 0,
    annualPrice: 0,
    description: "Sandbox plan for testing with no billing.",
    features: [
      "CO/MN basic calculation",
      "Essential dashboard",
      "Community support",
    ],
    type: "core",
    deliveriesIncluded: 20,
  },
  {
    key: "starter",
    displayName: "Starter",
    monthlyPrice: 10,
    annualPrice: 100,
    description: "For stores beginning their compliance automation journey.",
    features: [
      "Automatic calculation & application",
      "Automatic rule updates",
      "Monthly compliance report",
      "Email support (next business day)",
    ],
    type: "core",
    deliveriesIncluded: 100,
  },
  {
    key: "pro",
    displayName: "Pro",
    monthlyPrice: 29,
    annualPrice: 290,
    description: "For growing operations that require API access.",
    features: [
      "Everything in Starter",
      "Advanced CSV exports",
      "Webhooks & API",
      "Priority support",
    ],
    type: "core",
    deliveriesIncluded: 1000,
    highlight: true,
  },
  {
    key: "plus",
    displayName: "Plus",
    monthlyPrice: 79,
    annualPrice: 790,
    description: "For multi-store retailers with SLAs and guided onboarding.",
    features: [
      "Everything in Pro",
      "Multi-store support",
      "Guided onboarding",
      "SLA availability",
    ],
    type: "core",
    deliveriesIncluded: 5000,
  },
];

export const ENTERPRISE_PRICING_PLANS: PricingPlanDefinition[] = [
  {
    key: "enterprise_e10k",
    displayName: "Enterprise 10k",
    monthlyPrice: 149,
    annualPrice: 1484.04,
    description: "10k delivery commitment with monitored overage.",
    features: ["Everything in Plus", "10k delivery commitment", "Overage monitoring"],
    type: "enterprise",
    commitDeliveries: 10000,
    overageFee: 0.02,
  },
  {
    key: "enterprise_e25k",
    displayName: "Enterprise 25k",
    monthlyPrice: 299,
    annualPrice: 2978.04,
    description: "For high-volume networks with dedicated support.",
    features: ["Everything in Plus", "25k delivery commitment", "Overage monitoring"],
    type: "enterprise",
    commitDeliveries: 25000,
    overageFee: 0.015,
  },
  {
    key: "enterprise_e50k",
    displayName: "Enterprise 50k",
    monthlyPrice: 499,
    annualPrice: 4970.04,
    description: "50k delivery commitment with premium governance.",
    features: ["Everything in Plus", "50k delivery commitment", "Overage monitoring"],
    type: "enterprise",
    commitDeliveries: 50000,
    overageFee: 0.01,
  },
];

export const PRICING_PLAN_CATALOG: PricingPlanDefinition[] = [
  ...CORE_PRICING_PLANS,
  ...ENTERPRISE_PRICING_PLANS,
];

const PRICING_PLAN_MAP = new Map(
  PRICING_PLAN_CATALOG.map((plan) => [plan.key, plan]),
);

const titleCase = (value: string): string =>
  value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");

export const getPricingPlanByKey = (
  key: string | null | undefined,
): PricingPlanDefinition | undefined => {
  if (!key) {
    return undefined;
  }
  return PRICING_PLAN_MAP.get(key.trim().toLowerCase());
};

export const getPricingPlanDisplayName = (
  key: string | null | undefined,
): string | null => {
  const plan = getPricingPlanByKey(key);
  if (plan) {
    return plan.displayName;
  }
  if (!key) {
    return null;
  }
  const normalised = key.trim();
  if (!normalised) {
    return null;
  }
  return titleCase(normalised);
};
