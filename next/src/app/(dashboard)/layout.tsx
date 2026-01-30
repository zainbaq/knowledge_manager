'use client';

import { useAuth } from '@/components/auth/AuthProvider';
import { Sidebar, Header, MobileNav } from '@/components/layout';
import { useUIStore } from '@/lib/stores/ui-store';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isLoading, isAuthenticated } = useAuth();
  const { sidebarCollapsed } = useUIStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="space-y-4 w-full max-w-md p-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-8 w-1/2" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <MobileNav />
      <Header />
      <main
        className={cn(
          'pt-16 transition-all duration-300 min-h-screen',
          'pl-0',
          sidebarCollapsed ? 'md:pl-16' : 'md:pl-64'
        )}
      >
        <div className="p-4 md:p-6">
          {!isAuthenticated ? (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
              <h2 className="text-2xl font-semibold mb-4">Welcome to Knowledge Manager</h2>
              <p className="text-muted-foreground mb-6">
                Please sign in to access your documents and indexes.
              </p>
            </div>
          ) : (
            children
          )}
        </div>
      </main>
    </div>
  );
}
