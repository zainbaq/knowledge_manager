'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import { Sidebar, Header, MobileNav } from '@/components/layout';
import { useUIStore } from '@/lib/stores/ui-store';
import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';
import { isReturningFromUnifiedLogin, redirectToUnifiedLogin } from '@/lib/auth/unifiedLogin';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isLoading, isAuthenticated, signIn } = useAuth();
  const { sidebarCollapsed } = useUIStore();
  const [signInError, setSignInError] = useState<string | null>(null);

  useEffect(() => {
    if (isLoading || isAuthenticated) return;

    if (isReturningFromUnifiedLogin()) {
      // Bounced back from home.promethean-labs.co — complete this app's own
      // Cognito round trip, which should be silent now that the shared
      // Hosted UI session is live.
      signIn().catch((err) => {
        setSignInError(err instanceof Error ? err.message : 'Sign in failed');
      });
      return;
    }

    if (!signInError) {
      redirectToUnifiedLogin();
    }
  }, [isLoading, isAuthenticated, signIn, signInError]);

  if (isLoading || (!isAuthenticated && !signInError)) {
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

  if (signInError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center justify-center text-center max-w-md p-4">
          <h2 className="text-2xl font-semibold mb-4">Sign-in failed</h2>
          <p className="text-muted-foreground mb-6">{signInError}</p>
          <button
            onClick={() => {
              setSignInError(null);
              redirectToUnifiedLogin();
            }}
            className="text-sm underline underline-offset-4"
          >
            Try again
          </button>
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
        <div className="p-4 md:p-6">{children}</div>
      </main>
    </div>
  );
}
