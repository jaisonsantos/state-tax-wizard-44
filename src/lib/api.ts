const rawBaseURL = import.meta.env.VITE_API_BASE_URL || '/api';
const normalisedBaseURL = (() => {
  if (!rawBaseURL) {
    return '/api';
  }

  if (rawBaseURL === '/') {
    return '/';
  }

  const trimmed = rawBaseURL.replace(/\/+$/, '');
  return trimmed.length > 0 ? trimmed : '/api';
})();

const appendPath = (base: string, path: string): string => {
  if (!path.startsWith('/')) {
    path = `/${path}`;
  }

  if (!base || base === '/') {
    return path;
  }

  return `${base}${path}`;
};

export const API_BASE_URL = normalisedBaseURL;

export const API_DOCS_URL = appendPath(API_BASE_URL, '/docs');

export class ApiError extends Error {
  status: number;
  code?: string;
  detail?: unknown;

  constructor(status: number, message: string, code?: string, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

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
  hmac_last_rotated_at?: string | null;
  webhook_active: boolean;
  webhook_endpoint?: string | null;
  webhook_events: string[];
}

export interface RotateHmacSecretResponse {
  store_id: string;
  hmac_secret: string;
  rotated_at: string;
  previous_rotated_at?: string | null;
}

export interface WebhookEventRecord {
  event_id: string;
  event_type: string;
  status: string;
  attempts: number;
  next_retry_at?: string | null;
  last_error?: string | null;
  delivered_at?: string | null;
  dead_letter: boolean;
  created_at: string;
  updated_at: string;
}

export interface WebhookEventListResponse {
  events: WebhookEventRecord[];
}

export interface WebhookReplayResponse {
  event_id: string;
  status: string;
  attempts: number;
  next_retry_at?: string | null;
  dead_letter: boolean;
}

export interface UpdateStoreSettingsPayload {
  enable_mn: boolean;
  enable_co: boolean;
  absorb_fee: boolean;
  label_override: string;
  webhook_active?: boolean;
  webhook_endpoint?: string | null;
  webhook_events?: string[];
}

export interface LoginResponse {
  token: string;
  user: UserSummary;
  stores: StoreSummary[];
}

export interface SessionMetadata {
  id: string;
  issued_at: string;
  expires_at: string;
  last_activity_at?: string | null;
  store_scope: string[];
  ip_address?: string | null;
  user_agent?: string | null;
}

export interface MeResponse {
  user: UserSummary;
  stores: StoreSummary[];
  session?: SessionMetadata | null;
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

export interface BillingLimits {
  transactions_per_month: number | null;
  advanced_reports: boolean;
  analytics_dashboard: boolean;
  integrations: boolean;
}

export interface BillingEntitlements {
  plan: string;
  provider: string;
  status: string;
  trial_ends_at: string | null;
  cancel_at_period_end: boolean;
  current_period_start: string | null;
  current_period_end: string | null;
  features: string[];
  limits: BillingLimits;
}

export interface BillingUsage {
  plan: string;
  status: string;
  transactions_used: number;
  transactions_limit: number | null;
  unlimited: boolean;
  percentage_used: number;
  period_start: string | null;
  period_end: string | null;
}

export interface BillingCheckoutSession {
  session_id: string;
  url: string;
}

export interface BillingPortalSession {
  portal_url: string;
  portal_session_id: string;
}

export interface IntegrationProviderStatus {
  provider: string;
  enabled: boolean;
  connected: boolean;
  status: 'connected' | 'disconnected' | 'disabled';
  docs_url: string;
  install_url?: string | null;
  installed_at?: string | null;
  notes?: string | null;
}

export interface IntegrationStatusResponse {
  store_id: string;
  providers: IntegrationProviderStatus[];
}

export interface IntegrationInstallRequest {
  store_domain: string;
  external_shop_id?: string;
  metadata?: Record<string, string>;
}

export interface IntegrationInstallResponse {
  provider: string;
  connected: boolean;
  status: 'connected' | 'disabled';
  docs_url: string;
  notes?: string | null;
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
  absorbed?: boolean;
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
  page: number | null;
  limit: number;
  total: number | null;
  next_cursor?: string | null;
}

export type AnalyticsTrend = 'up' | 'down' | 'flat';

export interface AnalyticsMetricCard {
  id: string;
  title: string;
  value: number;
  formatted_value: string;
  delta: number;
  delta_percentage: number;
  trend: AnalyticsTrend;
  unit: string;
  jurisdiction?: string | null;
  insight?: string | null;
}

export interface AnalyticsRecentDecision {
  id: string;
  occurred_at: string;
  order_id?: string | null;
  jurisdiction?: string | null;
  amount_cents?: number | null;
  outcome?: string | null;
  reason_codes: string[];
}

export interface AnalyticsOverviewResponse {
  store_id: string;
  generated_at: string;
  window_start: string;
  window_end: string;
  metric_cards: AnalyticsMetricCard[];
  recent_decisions: {
    items: AnalyticsRecentDecision[];
    next_cursor: string | null;
  };
  counters: {
    fees_applied_total: number;
    fees_absorbed_total: number;
    report_exports_total: number;
  };
}

export interface DownloadResult {
  blob: Blob;
  filename: string | null;
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
      let parsedBody: unknown = null;
      let message = `API Error: ${response.status}`;
      let code: string | undefined;

      try {
        parsedBody = await response.json();
      } catch {
        parsedBody = await response.text();
      }

      if (parsedBody && typeof parsedBody === 'object' && 'detail' in (parsedBody as Record<string, unknown>)) {
        const detail = (parsedBody as Record<string, unknown>).detail;
        if (typeof detail === 'string') {
          message = detail;
        } else if (detail && typeof detail === 'object') {
          const detailRecord = detail as Record<string, unknown>;
          if (typeof detailRecord.message === 'string') {
            message = detailRecord.message;
          }
          if (typeof detailRecord.code === 'string') {
            code = detailRecord.code;
          }
        }
      } else if (typeof parsedBody === 'string' && parsedBody.trim().length > 0) {
        message = parsedBody;
      }

      throw new ApiError(response.status, message, code, parsedBody);
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
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', response.token);
    }

    return response;
  }

  async getMe(): Promise<MeResponse> {
    return this.request<MeResponse>('/me');
  }

  async logout(): Promise<void> {
    try {
      await this.request<void>('/auth/logout', {
        method: 'POST',
      });
    } catch (error) {
      // Swallow network/auth errors so UI can still clear local state.
      console.error('Failed to revoke session', error);
    } finally {
      this.authToken = null;
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
      }
    }
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

  async rotateHmacSecret(storeId: string): Promise<RotateHmacSecretResponse> {
    return this.request<RotateHmacSecretResponse>(`/v1/stores/${storeId}/hmac/rotate`, {
      method: 'POST',
    });
  }

  async getWebhookEvents(
    storeId: string,
    status?: string,
    limit: number = 50,
  ): Promise<WebhookEventListResponse> {
    const params = new URLSearchParams({ store_id: storeId, limit: String(limit) });
    if (status) {
      params.set('status', status);
    }

    return this.request<WebhookEventListResponse>(`/v1/webhooks/events?${params.toString()}`);
  }

  async replayWebhookEvent(eventId: string): Promise<WebhookReplayResponse> {
    return this.request<WebhookReplayResponse>(`/v1/webhooks/events/${eventId}/replay`, {
      method: 'POST',
    });
  }

  async getIntegrationStatus(storeId: string): Promise<IntegrationStatusResponse> {
    const params = new URLSearchParams({ store_id: storeId });
    return this.request<IntegrationStatusResponse>(`/v1/integrations/status?${params.toString()}`);
  }

  async installIntegration(
    provider: string,
    storeId: string,
    payload: IntegrationInstallRequest,
  ): Promise<IntegrationInstallResponse> {
    const params = new URLSearchParams({ store_id: storeId });
    return this.request<IntegrationInstallResponse>(
      `/v1/integrations/providers/${provider}/install?${params.toString()}`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    );
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

  // Reports methods
  async downloadCOReport(storeId: string, fromDate: string, toDate: string): Promise<DownloadResult> {
    const url = `${this.baseURL}/v1/reports/co/dr1786?store_id=${storeId}&from_date=${fromDate}&to_date=${toDate}`;
    const headers = this.buildHeaders();
    headers.set('Accept', 'text/csv');

    const response = await fetch(url, { headers });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to download report: ${response.status} - ${errorText}`);
    }

    const blob = await response.blob();
    const filename = extractFilename(response.headers.get('Content-Disposition'));

    return { blob, filename };
  }

  async downloadMNReport(
    storeId: string,
    fromDate: string,
    toDate: string,
    format: string = 'csv',
  ): Promise<DownloadResult> {
    const url = `${this.baseURL}/v1/reports/mn/summary?store_id=${storeId}&from_date=${fromDate}&to_date=${toDate}&format=${format}`;
    const headers = this.buildHeaders();
    headers.set('Accept', format === 'json' ? 'application/json' : 'text/csv');

    const response = await fetch(url, { headers });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to download report: ${response.status} - ${errorText}`);
    }

    const blob = await response.blob();
    const filename = extractFilename(response.headers.get('Content-Disposition'));

    return { blob, filename };
  }

  // Audit methods
  async getAuditLogs(
    storeId: string,
    page: number = 1,
    limit: number = 50,
    action?: string,
    cursor?: string,
  ): Promise<AuditLogResponse> {
    const params = new URLSearchParams({ store_id: storeId, limit: String(limit) });
    if (cursor) {
      params.set('cursor', cursor);
    } else {
      params.set('page', String(page));
    }
    if (action) {
      params.set('action', action);
    }
    return this.request<AuditLogResponse>(`/v1/audit?${params.toString()}`);
  }

  async getAnalyticsOverview(
    storeId: string,
    limit: number = 5,
    cursor?: string,
  ): Promise<AnalyticsOverviewResponse> {
    const params = new URLSearchParams({ store_id: storeId, limit: String(limit) });
    if (cursor) {
      params.set('cursor', cursor);
    }
    return this.request<AnalyticsOverviewResponse>(
      `/v1/analytics/overview?${params.toString()}`,
    );
  }

  // Billing methods
  async getEntitlements(storeId: string): Promise<BillingEntitlements> {
    const params = new URLSearchParams({ store_id: storeId });
    return this.request<BillingEntitlements>(`/v1/billing/entitlements?${params.toString()}`);
  }

  async getUsage(storeId: string): Promise<BillingUsage> {
    const params = new URLSearchParams({ store_id: storeId });
    return this.request<BillingUsage>(`/v1/billing/usage?${params.toString()}`);
  }

  async createCheckoutSession(storeId: string, planTier: string, successUrl: string, cancelUrl: string): Promise<BillingCheckoutSession> {
    return this.request<BillingCheckoutSession>(`/v1/billing/create-checkout-session?store_id=${storeId}`, {
      method: 'POST',
      body: JSON.stringify({ plan_tier: planTier, success_url: successUrl, cancel_url: cancelUrl }),
    });
  }

  async createPortalSession(storeId: string, returnUrl: string): Promise<BillingPortalSession> {
    const params = new URLSearchParams({ store_id: storeId, return_url: returnUrl });
    return this.request<BillingPortalSession>(`/v1/billing/create-portal-session?${params.toString()}`, {
      method: 'POST',
    });
  }
}

// Export singleton instance
export const apiClient = new ApiClient(API_BASE_URL);

// Helper function to download blob as file
const extractFilename = (contentDisposition: string | null): string | null => {
  if (!contentDisposition) {
    return null;
  }

  const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (filenameStarMatch && filenameStarMatch[1]) {
    return decodeURIComponent(filenameStarMatch[1]);
  }

  const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  if (filenameMatch && filenameMatch[1]) {
    return filenameMatch[1];
  }

  return null;
};

export const downloadBlob = (blob: Blob, filename?: string) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename && filename.trim().length > 0 ? filename : 'download';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
};
