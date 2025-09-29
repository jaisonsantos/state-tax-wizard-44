export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserSummary {
  id: string;
  email: string;
  created_at: string;
}

export interface StoreSummary {
  id: string;
  name: string;
}

export interface StoreSettings {
  store_id: string;
  enable_mn: boolean;
  enable_co: boolean;
  absorb_fee: boolean;
  label_override: string;
  plan?: string | null;
}

export interface UpdateStoreSettingsPayload {
  enable_mn: boolean;
  enable_co: boolean;
  absorb_fee: boolean;
  label_override: string;
}

export interface LoginResponse {
  token: string;
  user: UserSummary;
  stores: StoreSummary[];
}

export interface MeResponse {
  user: UserSummary;
  stores: StoreSummary[];
}

export interface FeeQuoteRequest {
  store_id: string;
  destination: {
    state: string;
    zip?: string;
  };
  delivery_method: string;
  items: Array<{
    sku: string;
    qty: number;
    unit_price_cents: number;
    taxability: string;
  }>;
  shipping_amount_cents: number;
  source_of_remittance?: 'merchant' | 'marketplace';
}

export interface FeeApplyRequest extends FeeQuoteRequest {
  order_id: string;
}

export interface FeeLine {
  jurisdiction: string;
  amount_cents: number;
  display_name: string;
  rule_version: string;
  reason_codes: string[];
  absorbed: boolean;
}

export interface FeeDecision {
  jurisdiction: string;
  outcome: "applied" | "skipped";
  reason_codes: string[];
  amount_cents: number;
}

export interface FeeQuoteResponse {
  lines: FeeLine[];
  decisions: FeeDecision[];
  decided: boolean;
  absorbed: boolean;
}

export interface FeeApplyResponse {
  success: boolean;
  lines: FeeLine[];
  decisions: FeeDecision[];
  absorbed: boolean;
}

export interface Entitlements {
  plan: string;
  trial_ends_at: string | null;
  provider: string;
  status: string;
}

export interface RuleVersionResponse {
  jurisdiction: string;
  version: string;
  effective_from: string;
  effective_to: string | null;
  params: Record<string, unknown>;
  is_latest: boolean;
}

export interface RulesResponse {
  rules: RuleVersionResponse[];
}

export interface AuditLogPayloadLine {
  jurisdiction: string;
  amount_cents: number;
  reason_codes: string[];
  rule_version: string;
}

export interface AuditLogPayload {
  store_id: string;
  order_id?: string;
  delivery_method?: string;
  lines?: AuditLogPayloadLine[];
  status?: string;
  [key: string]: unknown;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string | null;
  actor: string;
  action: string;
  payload: AuditLogPayload;
}

export interface AuditLogResponse {
  items: AuditLogEntry[];
  page: number;
  limit: number;
  total: number;
}

// API Client class
class ApiClient {
  private baseURL: string;
  private authToken: string | null = null;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
    this.authToken = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  }

  hasToken(): boolean {
    return !!this.authToken;
  }

  private buildHeaders(initial?: HeadersInit): Headers {
    const headers = new Headers(initial);

    if (this.authToken) {
      headers.set('Authorization', `Bearer ${this.authToken}`);
    }

    return headers;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const headers = this.buildHeaders(options.headers);

    if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let message: string;
      try {
        const data = await response.json();
        message = typeof data === 'string' ? data : JSON.stringify(data);
      } catch {
        message = await response.text();
      }
      throw new Error(`API Error: ${response.status} - ${message}`);
    }

    const contentType = response.headers.get('content-type') ?? '';
    if (contentType.includes('application/json')) {
      return (await response.json()) as T;
    }

    return undefined as T;
  }

  // Auth methods
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    this.authToken = response.token;
    localStorage.setItem('auth_token', response.token);

    return response;
  }

  async getMe(): Promise<MeResponse> {
    return this.request<MeResponse>('/me');
  }

  // Store settings methods
  async getStoreSettings(storeId: string): Promise<StoreSettings> {
    return this.request<StoreSettings>(`/v1/stores/${storeId}/settings`);
  }

  async updateStoreSettings(
    storeId: string,
    payload: UpdateStoreSettingsPayload,
  ): Promise<StoreSettings> {
    return this.request<StoreSettings>(`/v1/stores/${storeId}/settings`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  }

  logout() {
    this.authToken = null;
    localStorage.removeItem('auth_token');
  }

  // Fee methods
  async quoteFees(request: FeeQuoteRequest): Promise<FeeQuoteResponse> {
    return this.request<FeeQuoteResponse>('/v1/fees/quote', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async applyFees(request: FeeApplyRequest): Promise<FeeApplyResponse> {
    return this.request<FeeApplyResponse>('/v1/fees/apply', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Rules methods
  async getRules(): Promise<RulesResponse> {
    return this.request<RulesResponse>('/v1/rules');
  }

  // Billing methods
  async getEntitlements(storeId: string): Promise<Entitlements> {
    return this.request<Entitlements>(`/v1/billing/entitlements?store_id=${storeId}`);
  }

  // Reports methods
  async downloadCOReport(storeId: string, fromDate: string, toDate: string): Promise<Blob> {
    const url = `${this.baseURL}/v1/reports/co/dr1786?store_id=${storeId}&from_date=${fromDate}&to_date=${toDate}`;
    const headers = this.buildHeaders();

    const response = await fetch(url, { headers });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to download report: ${response.status} - ${errorText}`);
    }

    return response.blob();
  }

  async downloadMNReport(storeId: string, fromDate: string, toDate: string, format: string = 'csv'): Promise<Blob> {
    const url = `${this.baseURL}/v1/reports/mn/summary?store_id=${storeId}&from_date=${fromDate}&to_date=${toDate}&format=${format}`;
    const headers = this.buildHeaders();

    const response = await fetch(url, { headers });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to download report: ${response.status} - ${errorText}`);
    }

    return response.blob();
  }

  // Audit methods
  async getAuditLogs(storeId: string, page: number = 1, limit: number = 50): Promise<AuditLogResponse> {
    return this.request<AuditLogResponse>(`/v1/audit?store_id=${storeId}&page=${page}&limit=${limit}`);
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL);

// Helper function to download blob as file
export const downloadBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};
