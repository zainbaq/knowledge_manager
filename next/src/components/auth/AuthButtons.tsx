'use client';

import { signInWithRedirect, getCurrentUser } from 'aws-amplify/auth';
import { Button } from '@/components/ui/button';
import { useAuth } from './AuthProvider';
import { LogIn, LogOut } from 'lucide-react';
import { configureAmplify } from '@/lib/auth/config';

export function SignInButton({ className }: { className?: string }) {
  const { checkAuth } = useAuth();

  const handleSignIn = async () => {
    try {
      // Ensure Amplify is configured
      configureAmplify();

      // Check if user is already authenticated
      try {
        await getCurrentUser();
        // User is already signed in, just refresh auth state
        console.log('User already authenticated, refreshing state...');
        await checkAuth();
        return;
      } catch {
        // User is not authenticated, proceed with sign in
      }

      await signInWithRedirect();
    } catch (err: unknown) {
      const errorName = err instanceof Error ? err.name : '';
      // If user is already authenticated, just refresh the auth state
      if (errorName === 'UserAlreadyAuthenticatedException') {
        console.log('User already authenticated');
        await checkAuth();
      } else {
        console.error('Error signing in:', err);
      }
    }
  };

  return (
    <Button onClick={handleSignIn} className={className}>
      <LogIn className="mr-2 h-4 w-4" />
      Sign In
    </Button>
  );
}

export function SignOutButton({ className }: { className?: string }) {
  const { signOut } = useAuth();

  return (
    <Button variant="ghost" onClick={signOut} className={className}>
      <LogOut className="mr-2 h-4 w-4" />
      Sign Out
    </Button>
  );
}
