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
    description: "Plano sandbox para testes, sem cobrança.",
    features: [
      "CO/MN cálculo básico",
      "Dashboard básico",
      "Suporte comunidade",
    ],
    type: "core",
    deliveriesIncluded: 20,
  },
  {
    key: "starter",
    displayName: "Starter",
    monthlyPrice: 10,
    annualPrice: 100,
    description: "Para lojas que iniciam a automação fiscal.",
    features: [
      "Cálculo & aplicação automática",
      "Atualizações automáticas",
      "Relatório mensal",
      "Suporte por e-mail (D+1)",
    ],
    type: "core",
    deliveriesIncluded: 100,
  },
  {
    key: "pro",
    displayName: "Pro",
    monthlyPrice: 29,
    annualPrice: 290,
    description: "Para operações em crescimento que exigem API.",
    features: [
      "Tudo do Starter",
      "CSV avançado",
      "Webhooks/API",
      "Suporte prioritário",
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
    description: "Para multi-lojas com SLA e onboarding assistido.",
    features: [
      "Tudo do Pro",
      "Multi-store",
      "Onboarding assistido",
      "SLA",
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
    description: "Compromisso de 10k entregas com overage monitorado.",
    features: ["Tudo do Plus", "Commit 10k", "Overage monitorado"],
    type: "enterprise",
    commitDeliveries: 10000,
    overageFee: 0.02,
  },
  {
    key: "enterprise_e25k",
    displayName: "Enterprise 25k",
    monthlyPrice: 299,
    annualPrice: 2978.04,
    description: "Para redes com alto volume e suporte dedicado.",
    features: ["Tudo do Plus", "Commit 25k", "Overage monitorado"],
    type: "enterprise",
    commitDeliveries: 25000,
    overageFee: 0.015,
  },
  {
    key: "enterprise_e50k",
    displayName: "Enterprise 50k",
    monthlyPrice: 499,
    annualPrice: 4970.04,
    description: "Compromisso de 50k com governança premium.",
    features: ["Tudo do Plus", "Commit 50k", "Overage monitorado"],
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
