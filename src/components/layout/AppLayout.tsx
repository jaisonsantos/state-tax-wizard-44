import { Outlet } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { useAuth } from "@/context/AuthContext";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function AppLayout() {
  const { stores, selectedStoreId, selectStore, loading } = useAuth();

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <AppSidebar />

        <div className="flex-1 flex flex-col">
          <header className="h-14 flex items-center justify-between border-b bg-card px-6">
            <SidebarTrigger />

            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground hidden sm:inline">
                Demo Mode
              </span>
              <Select
                value={selectedStoreId ?? (stores.length > 0 ? stores[0].id : "")}
                onValueChange={selectStore}
                disabled={loading || stores.length === 0}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder={loading ? "Loading stores..." : "Select a store"} />
                </SelectTrigger>
                <SelectContent>
                  {stores.map((store) => (
                    <SelectItem key={store.id} value={store.id}>
                      {store.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </header>

          <main className="flex-1 p-6">
            <Outlet />
          </main>
        </div>
      </div>
      
      <Toaster />
      <Sonner />
    </SidebarProvider>
  );
}