const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: UserInfo;
}

export interface UserInfo {
  id: string;
  email: string;
  stores: StoreInfo[];
}

export interface StoreInfo {
  id: string;
  platform: string;
  domain: string;
  country: string;
  state: string | null;
  created_at: string;
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
}

export interface FeeLine {
  jurisdiction: string;
  amount_cents: number;
  display_name: string;
  rule_version: string;
  reason_codes: string[];
}

export interface FeeQuoteResponse {
  lines: FeeLine[];
  decided: boolean;
}

export interface Entitlements {
  plan: string;
  trial_ends_at: string | null;
  provider: string;
  status: string;
}

export interface RulesResponse {
  mn: {
    threshold_cents: number;
  };
  co: {
    rate_schedule: Array<{
      start: string;
      end: string;
      rate_cents: number;
    }>;
  };
}

// API Client class
class ApiClient {
  private baseURL: string;
  private authToken: string | null = null;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
    // Load token from localStorage
    this.authToken = localStorage.getItem('auth_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.authToken) {
      headers.Authorization = `Bearer ${this.authToken}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`API Error: ${response.status} - ${error}`);
    }

    return response.json();
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

  async getMe(): Promise<UserInfo> {
    return this.request<UserInfo>('/me');
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

  async applyFees(request: FeeQuoteRequest & { order_id: string }): Promise<FeeQuoteResponse> {
    return this.request<FeeQuoteResponse>('/v1/fees/apply', {
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
    
    const headers: Record<string, string> = {};
    if (this.authToken) {
      headers.Authorization = `Bearer ${this.authToken}`;
    }

    const response = await fetch(url, { headers });
    
    if (!response.ok) {
      throw new Error(`Failed to download report: ${response.statusText}`);
    }
    
    return response.blob();
  }

  async downloadMNReport(storeId: string, fromDate: string, toDate: string, format: string = 'csv'): Promise<Blob> {
    const url = `${this.baseURL}/v1/reports/mn/summary?store_id=${storeId}&from_date=${fromDate}&to_date=${toDate}&format=${format}`;
    
    const headers: Record<string, string> = {};
    if (this.authToken) {
      headers.Authorization = `Bearer ${this.authToken}`;
    }

    const response = await fetch(url, { headers });
    
    if (!response.ok) {
      throw new Error(`Failed to download report: ${response.statusText}`);
    }
    
    return response.blob();
  }

  // Audit methods
  async getAuditLogs(storeId: string, page: number = 1, limit: number = 50): Promise<any[]> {
    return this.request<any[]>(`/v1/audit?store_id=${storeId}&page=${page}&limit=${limit}`);
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