# AWS Cognito Authentication Implementation

This document describes how AWS Cognito authentication is implemented in this Next.js application using AWS Amplify v6.

## Overview

The application uses **AWS Amplify** with **Amazon Cognito** for user authentication. It implements the **OAuth 2.0 Authorization Code flow** with Cognito's Hosted UI for sign-in/sign-up.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Next.js App   │────▶│  Cognito Hosted  │────▶│  Cognito User   │
│   (Amplify)     │◀────│       UI         │◀────│      Pool       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  /auth/callback │
│   (OAuth code)  │
└─────────────────┘
```

## File Structure

```
next/src/
├── lib/auth/
│   └── config.ts              # Amplify/Cognito configuration
├── components/auth/
│   ├── AuthProvider.tsx       # React context for auth state
│   ├── AuthButtons.tsx        # SignIn/SignOut button components
│   └── UserMenu.tsx           # User dropdown menu component
├── app/
│   ├── layout.tsx             # Root layout with AuthProvider
│   ├── auth/callback/
│   │   └── page.tsx           # OAuth callback handler
│   └── account/
│       └── page.tsx           # User account page
└── .env.local                 # Environment variables
```

## Configuration

### Environment Variables

Create a `.env.local` file with these variables:

```bash
# AWS Cognito Configuration
NEXT_PUBLIC_COGNITO_USER_POOL_ID=your-user-pool-id
NEXT_PUBLIC_COGNITO_CLIENT_ID=your-app-client-id
NEXT_PUBLIC_COGNITO_DOMAIN=your-domain.auth.region.amazoncognito.com

# Redirect URLs (must match Cognito app client settings)
NEXT_PUBLIC_REDIRECT_SIGN_IN=http://localhost:3000/auth/callback
NEXT_PUBLIC_REDIRECT_SIGN_OUT=http://localhost:3000
```

### Amplify Configuration (`lib/auth/config.ts`)

```typescript
import { Amplify, type ResourcesConfig } from 'aws-amplify';

const authConfig: ResourcesConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '',
      userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || '',
      loginWith: {
        oauth: {
          domain: process.env.NEXT_PUBLIC_COGNITO_DOMAIN || '',
          scopes: ['openid', 'email', 'phone'],
          redirectSignIn: [process.env.NEXT_PUBLIC_REDIRECT_SIGN_IN || 'http://localhost:3000/auth/callback'],
          redirectSignOut: [process.env.NEXT_PUBLIC_REDIRECT_SIGN_OUT || 'http://localhost:3000'],
          responseType: 'code',
        },
      },
    },
  },
};

export function configureAmplify() {
  Amplify.configure(authConfig, { ssr: true });
}
```

## Components

### 1. AuthProvider (`components/auth/AuthProvider.tsx`)

The central authentication context that:
- Manages global auth state (`user`, `isLoading`, `isAuthenticated`)
- Configures Amplify on initialization
- Listens for auth events via Amplify Hub
- Provides `checkAuth()` and `signOut()` functions
- Fetches user attributes (email, name) from Cognito

**Usage:**
```tsx
// In layout.tsx - wrap the entire app
<AuthProvider>
  {children}
</AuthProvider>

// In any component - access auth state
const { user, isAuthenticated, signOut } = useAuth();
```

**Context Interface:**
```typescript
interface AuthContextType {
  user: ExtendedUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signOut: () => Promise<void>;
  checkAuth: () => Promise<void>;
}
```

### 2. AuthButtons (`components/auth/AuthButtons.tsx`)

Simple button components for authentication actions:

- **SignInButton**: Calls `signInWithRedirect()` to redirect to Cognito Hosted UI
- **SignOutButton**: Uses the `useAuth()` hook to trigger sign out

### 3. UserMenu (`components/auth/UserMenu.tsx`)

A dropdown menu component that:
- Shows "Sign In" button for unauthenticated users
- Shows user icon with dropdown for authenticated users
- Dropdown contains: user email, Account Settings link, Sign Out button

### 4. OAuth Callback Page (`app/auth/callback/page.tsx`)

Handles the redirect from Cognito after authentication:
1. Receives the OAuth authorization code in URL parameters
2. Waits for Amplify to process the code and exchange it for tokens
3. Calls `checkAuth()` to update the auth context
4. Redirects to the home page on success
5. Displays error message on failure

## Authentication Flow

### Sign In Flow

1. User clicks "Sign In" button
2. `signInWithRedirect()` redirects to Cognito Hosted UI
3. User authenticates on Cognito (email/password, social login, etc.)
4. Cognito redirects to `/auth/callback?code=xxx`
5. Callback page processes the OAuth code
6. Amplify exchanges code for tokens (stored in localStorage)
7. `checkAuth()` updates the auth context
8. User is redirected to home page

### Sign Out Flow

1. User clicks "Sign Out"
2. `signOut()` is called from AuthProvider
3. Amplify clears tokens from localStorage
4. User state is set to null
5. Cognito session is terminated

## Auth Events (Hub)

The AuthProvider listens for these Amplify Hub events:

| Event | Action |
|-------|--------|
| `signedIn` | Refresh auth state |
| `signInWithRedirect` | Refresh auth state |
| `signedOut` | Clear user state |
| `tokenRefresh` | Refresh auth state |
| `signInWithRedirect_failure` | Log error, stop loading |

## User Data Access

After authentication, user data is available through the `useAuth()` hook:

```typescript
const { user, isAuthenticated } = useAuth();

// Access user info
const email = user?.attributes?.email;
const name = user?.attributes?.name;
const userId = user?.userId;
const username = user?.username;
```

## Cognito Setup Requirements

In AWS Cognito Console, ensure your App Client has:

1. **Allowed callback URLs**: Must include your `NEXT_PUBLIC_REDIRECT_SIGN_IN` URL
2. **Allowed sign-out URLs**: Must include your `NEXT_PUBLIC_REDIRECT_SIGN_OUT` URL
3. **OAuth 2.0 grant types**: Authorization code grant
4. **OAuth scopes**: openid, email, phone
5. **Hosted UI**: Enabled with your custom domain

## Dependencies

```json
{
  "aws-amplify": "^6.16.0"
}
```

## Troubleshooting

### Common Issues

1. **"Invalid redirect URI"**: Ensure callback URLs in Cognito match exactly (including trailing slashes)
2. **Tokens not persisting**: Check that cookies/localStorage are not blocked
3. **Auth state not updating**: Ensure AuthProvider wraps your component tree
4. **CORS errors**: Verify Cognito domain is correctly configured

### Debug Logging

The implementation includes console logs for debugging. Check browser console for:
- `Amplify configured`
- `Auth session: has tokens / no tokens`
- `Current user: {...}`
- `Auth Hub event: signedIn`
