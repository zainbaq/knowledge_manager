/**
 * Sign-in for this app is no longer its own branded page — it bounces
 * through the unified login at home.promethean-labs.co and back. See
 * docs/consolidation-readiness-plan.md and promethean-home-portal's
 * redirectTarget.ts for the other half of this flow.
 *
 * First hop: send the browser to the portal with ?redirect=<back here,
 * with ?sso=1>. Second hop (this app, ?sso=1 present): call this app's own
 * signInWithRedirect(). Because the portal hop just established (or
 * confirmed) the shared Cognito Hosted UI session cookie, this second
 * OAuth round trip completes silently — no credential prompt.
 */

const HOME_PORTAL_URL = process.env.NEXT_PUBLIC_HOME_PORTAL_URL || 'https://home.promethean-labs.co';

export function isReturningFromUnifiedLogin(): boolean {
  if (typeof window === 'undefined') return false;
  return new URLSearchParams(window.location.search).get('sso') === '1';
}

export function redirectToUnifiedLogin(): void {
  if (typeof window === 'undefined') return;
  const returnTo = `${window.location.origin}${window.location.pathname}?sso=1`;
  window.location.href = `${HOME_PORTAL_URL}/?redirect=${encodeURIComponent(returnTo)}`;
}
