'use client';

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';
import { Hub } from 'aws-amplify/utils';
import {
  getCurrentUser,
  fetchUserAttributes,
  signOut as amplifySignOut,
  type AuthUser,
} from 'aws-amplify/auth';
import { configureAmplify } from '@/lib/auth/config';

export interface ExtendedUser extends AuthUser {
  attributes?: {
    email?: string;
    name?: string;
    phone_number?: string;
  };
}

interface AuthContextType {
  user: ExtendedUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signOut: () => Promise<void>;
  checkAuth: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  signOut: async () => {},
  checkAuth: async () => false,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<ExtendedUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const currentUser = await getCurrentUser();

      let attributes: Record<string, string | undefined> = {};
      try {
        attributes = await fetchUserAttributes();
      } catch {
        // Attributes fetch can fail, continue with basic user info
        console.log('Could not fetch user attributes');
      }

      const extendedUser: ExtendedUser = {
        ...currentUser,
        attributes: {
          email: attributes.email,
          name: attributes.name,
          phone_number: attributes.phone_number,
        },
      };

      setUser(extendedUser);
      console.log('Authenticated user:', extendedUser.username);
      return true;
    } catch (err: unknown) {
      // Check if it's a "not authenticated" error (expected when user isn't logged in)
      const errorName = err instanceof Error ? err.name : '';
      if (errorName !== 'UserUnAuthenticatedException') {
        console.log('Auth check result:', errorName || 'No authenticated user');
      }
      setUser(null);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    try {
      await amplifySignOut();
      setUser(null);
    } catch (err) {
      console.error('Error signing out:', err);
    }
  }, []);

  useEffect(() => {
    // Ensure Amplify is configured
    configureAmplify();

    // Listen for auth events
    const hubListener = Hub.listen('auth', ({ payload }) => {
      console.log('Auth Hub event:', payload.event);

      switch (payload.event) {
        case 'signedIn':
        case 'signInWithRedirect':
        case 'tokenRefresh':
          checkAuth();
          break;
        case 'signedOut':
          setUser(null);
          setIsLoading(false);
          break;
        case 'signInWithRedirect_failure': {
          const error = payload.data as { error?: { name?: string } } | undefined;
          if (error?.error?.name === 'UserAlreadyAuthenticatedException') {
            console.log('User already authenticated, refreshing auth state...');
            checkAuth();
          } else {
            console.error('Sign in redirect failed:', payload.data);
            setIsLoading(false);
          }
          break;
        }
      }
    });

    // Check auth status on mount
    checkAuth();

    return () => {
      hubListener();
    };
  }, [checkAuth]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        signOut,
        checkAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
