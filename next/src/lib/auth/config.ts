import { Amplify, type ResourcesConfig } from 'aws-amplify';
// This import is REQUIRED for Next.js to handle OAuth callbacks
import 'aws-amplify/auth/enable-oauth-listener';

// Get domain and strip protocol if present
const rawDomain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN || '';
const domain = rawDomain.replace(/^https?:\/\//, '');

// Get redirect URLs - ensure they match exactly what's in Cognito
const redirectSignIn = process.env.NEXT_PUBLIC_REDIRECT_SIGN_IN || 'http://localhost:3000/auth/callback';
const redirectSignOut = process.env.NEXT_PUBLIC_REDIRECT_SIGN_OUT || 'http://localhost:3000';

const authConfig: ResourcesConfig = {
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '',
      userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || '',
      loginWith: {
        oauth: {
          domain: domain,
          scopes: ['openid', 'email', 'profile'],
          redirectSignIn: [redirectSignIn],
          redirectSignOut: [redirectSignOut],
          responseType: 'code',
        },
      },
    },
  },
};

let isConfigured = false;

export function configureAmplify() {
  if (!isConfigured && typeof window !== 'undefined') {
    console.log('[Amplify] Configuring...');

    // Configure Amplify
    Amplify.configure(authConfig, { ssr: false });

    isConfigured = true;
    console.log('[Amplify] Configuration complete');
  }
}

export { authConfig };
