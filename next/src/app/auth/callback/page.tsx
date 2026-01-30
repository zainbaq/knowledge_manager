'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, fetchAuthSession } from 'aws-amplify/auth';
import { Hub } from 'aws-amplify/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { configureAmplify } from '@/lib/auth/config';

export default function AuthCallbackPage() {
  const router = useRouter();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  const [debugInfo, setDebugInfo] = useState<string[]>([]);

  const addDebug = (msg: string) => {
    console.log(`[OAuth Callback] ${msg}`);
    setDebugInfo(prev => [...prev.slice(-15), msg]);
  };

  useEffect(() => {
    let mounted = true;

    // Ensure Amplify is configured
    configureAmplify();

    addDebug('Callback page loaded');
    addDebug(`URL: ${window.location.href}`);

    // Check for error in URL
    const urlParams = new URLSearchParams(window.location.search);
    const authError = urlParams.get('error');
    if (authError) {
      addDebug(`OAuth error: ${authError}`);
      setStatus('error');
      setError(authError);
      return;
    }

    // Listen for auth events
    const hubListener = Hub.listen('auth', ({ payload }) => {
      addDebug(`Hub event: ${payload.event}`);

      if (payload.event === 'signInWithRedirect') {
        addDebug('Sign in successful!');
        if (mounted) {
          setStatus('success');
          setTimeout(() => router.replace('/'), 1000);
        }
      }

      if (payload.event === 'signInWithRedirect_failure') {
        addDebug(`Sign in failed: ${JSON.stringify(payload.data)}`);
        // Check if it's actually a success (user already authenticated)
        const errorData = payload.data as { error?: { name?: string } } | undefined;
        if (errorData?.error?.name === 'UserAlreadyAuthenticatedException') {
          addDebug('User already authenticated');
          if (mounted) {
            setStatus('success');
            setTimeout(() => router.replace('/'), 1000);
          }
        } else if (mounted) {
          setStatus('error');
          setError('Sign in failed. Please try again.');
        }
      }

      if (payload.event === 'signedIn') {
        addDebug('Signed in event received');
        if (mounted) {
          setStatus('success');
          setTimeout(() => router.replace('/'), 1000);
        }
      }
    });

    // Also poll for auth status in case we missed the event
    const checkAuth = async () => {
      try {
        const session = await fetchAuthSession();
        if (session.tokens?.accessToken) {
          const user = await getCurrentUser();
          addDebug(`Authenticated as: ${user.username}`);
          if (mounted) {
            setStatus('success');
            setTimeout(() => router.replace('/'), 1000);
          }
          return true;
        }
      } catch {
        // Not authenticated yet
      }
      return false;
    };

    // Check immediately and then poll
    const pollAuth = async () => {
      if (await checkAuth()) return;

      // Poll a few times
      for (let i = 0; i < 10; i++) {
        await new Promise(resolve => setTimeout(resolve, 500));
        if (!mounted) return;
        addDebug(`Checking auth... attempt ${i + 1}`);
        if (await checkAuth()) return;
      }

      // Timeout
      if (mounted && status === 'loading') {
        addDebug('Timeout waiting for authentication');
        setStatus('error');
        setError('Authentication timed out. Please try again.');
      }
    };

    // Small delay to let Amplify process the callback
    setTimeout(pollAuth, 500);

    return () => {
      mounted = false;
      hubListener();
    };
  }, [router, status]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center">
          <CardTitle>
            {status === 'loading' && 'Signing you in...'}
            {status === 'success' && 'Welcome!'}
            {status === 'error' && 'Authentication Failed'}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          {status === 'loading' && (
            <>
              <Loader2 className="h-12 w-12 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">
                Processing authentication...
              </p>
            </>
          )}
          {status === 'success' && (
            <>
              <CheckCircle className="h-12 w-12 text-green-500" />
              <p className="text-muted-foreground">Redirecting to dashboard...</p>
            </>
          )}
          {status === 'error' && (
            <>
              <XCircle className="h-12 w-12 text-destructive" />
              <p className="text-destructive text-center">{error}</p>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => router.push('/')}>
                  Go to Home
                </Button>
              </div>
            </>
          )}

          {/* Debug info */}
          <div className="w-full mt-4 p-3 bg-muted rounded text-xs font-mono max-h-48 overflow-y-auto">
            <div className="font-bold mb-2">Debug Log:</div>
            {debugInfo.map((msg, i) => (
              <div key={i} className="py-0.5">{msg}</div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
