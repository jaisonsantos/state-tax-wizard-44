import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { apiClient, type MeResponse, type StoreSummary, type UserSummary } from "@/lib/api";

interface AuthContextValue {
  user: UserSummary | null;
  stores: StoreSummary[];
  selectedStoreId: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
  selectStore: (storeId: string) => void;
  logout: () => Promise<void>;
}

const STORAGE_KEY = "selected_store_id";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function fetchMe(): Promise<MeResponse | null> {
  try {
    return await apiClient.getMe();
  } catch (error) {
    console.error("Failed to fetch current user", error);
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserSummary | null>(null);
  const [stores, setStores] = useState<StoreSummary[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(() => {
    if (typeof window === "undefined") {
      return null;
    }
    return localStorage.getItem(STORAGE_KEY);
  });
  const [loading, setLoading] = useState(false);

  const selectStore = useCallback((storeId: string) => {
    setSelectedStoreId(storeId);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, storeId);
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!apiClient.hasToken()) {
      setUser(null);
      setStores([]);
      setSelectedStoreId(null);
      if (typeof window !== "undefined") {
        localStorage.removeItem(STORAGE_KEY);
      }
      return;
    }

    setLoading(true);
    const profile = await fetchMe();
    if (!profile) {
      setUser(null);
      setStores([]);
      setSelectedStoreId(null);
      if (typeof window !== "undefined") {
        localStorage.removeItem(STORAGE_KEY);
      }
      setLoading(false);
      return;
    }

    setUser(profile.user);
    setStores(profile.stores);

    if (profile.stores.length === 0) {
      setSelectedStoreId(null);
      if (typeof window !== "undefined") {
        localStorage.removeItem(STORAGE_KEY);
      }
      setLoading(false);
      return;
    }

    const persisted =
      typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    const nextStore = profile.stores.find((store) => store.id === persisted)?.id ?? profile.stores[0].id;
    setSelectedStoreId(nextStore);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, nextStore);
    }

    setLoading(false);
  }, []);

  const logout = useCallback(async () => {
    setLoading(true);
    try {
      await apiClient.logout();
    } finally {
      setUser(null);
      setStores([]);
      setSelectedStoreId(null);
      if (typeof window !== "undefined") {
        localStorage.removeItem(STORAGE_KEY);
      }
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, stores, selectedStoreId, loading, refresh, selectStore, logout }),
    [user, stores, selectedStoreId, loading, refresh, selectStore, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
