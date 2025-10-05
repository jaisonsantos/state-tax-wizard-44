import { useState } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { BillingLimitModal } from "@/components/BillingLimitModal";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { useAuth } from "@/context/AuthContext";
import { formatDistanceToNow } from "date-fns";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { LogOut } from "lucide-react";

export function AppLayout() {
  const { stores, selectedStoreId, selectStore, loading, user, logout, session } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);
  const navigate = useNavigate();

  const handleLogout = async () => {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await logout();
      navigate("/login", { replace: true });
    } finally {
      setLoggingOut(false);
    }
  };

  const initials = user?.email ? user.email[0]?.toUpperCase() : "?";

  const lastActivityLabel = session?.last_activity_at
    ? formatDistanceToNow(new Date(session.last_activity_at), { addSuffix: true })
    : "Not recorded";

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
                disabled={loading || loggingOut || stores.length === 0}
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

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="flex items-center gap-2 px-2">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback>{initials}</AvatarFallback>
                    </Avatar>
                    <div className="hidden sm:flex flex-col items-start">
                      <span className="text-sm font-medium leading-none">
                        {user?.email ?? "Signed out"}
                      </span>
                      <span className="text-xs text-muted-foreground">Account</span>
                    </div>
                  </Button>
                </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel>
                      {user?.email ?? "No active session"}
                    </DropdownMenuLabel>
                    {session && (
                      <>
                        <DropdownMenuLabel className="text-xs text-muted-foreground">
                          Session {session.id.slice(0, 8)}…
                        </DropdownMenuLabel>
                        <DropdownMenuItem disabled className="flex-col items-start whitespace-normal">
                          <span className="text-xs">Issued: {new Date(session.issued_at).toLocaleString()}</span>
                          <span className="text-xs">Expires: {new Date(session.expires_at).toLocaleString()}</span>
                          <span className="text-xs">Last activity: {lastActivityLabel}</span>
                          <span className="text-xs">Stores: {session.store_scope.join(", ")}</span>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                      </>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                    onSelect={(event) => {
                      event.preventDefault();
                      void handleLogout();
                    }}
                    disabled={loggingOut}
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>{loggingOut ? "Signing out..." : "Sign out"}</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          <main className="flex-1 p-6">
            <Outlet />
          </main>
        </div>
      </div>
      
      <Toaster />
      <Sonner />
      <BillingLimitModal />
    </SidebarProvider>
  );
}