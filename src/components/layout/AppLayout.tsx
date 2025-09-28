import { Outlet } from "react-router-dom";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";

export function AppLayout() {
  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <AppSidebar />
        
        <div className="flex-1 flex flex-col">
          <header className="h-14 flex items-center justify-between border-b bg-card px-6">
            <SidebarTrigger />
            
            <div className="flex items-center gap-4">
              <span className="text-sm text-muted-foreground">
                Demo Mode
              </span>
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