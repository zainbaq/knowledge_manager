"""AWS Cognito JWT verification utilities."""

import time
from typing import Optional
from urllib.request import urlopen
import json

from jose import jwt, JWTError
from cachetools import TTLCache

from config import (
    COGNITO_USER_POOL_ID,
    COGNITO_REGION,
    COGNITO_ENABLED,
    COGNITO_TRUSTED_CLIENT_IDS,
)
from logging_config import get_logger

logger = get_logger(__name__)

# Cache JWKS keys for 1 hour
_jwks_cache: TTLCache = TTLCache(maxsize=1, ttl=3600)
_JWKS_CACHE_KEY = "jwks"


def _get_jwks_url() -> str:
    """Get the JWKS URL for the Cognito User Pool."""
    return f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"


def _get_issuer() -> str:
    """Get the expected issuer for JWT tokens."""
    return f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"


def _fetch_jwks() -> dict:
    """Fetch JWKS from Cognito, with caching."""
    if _JWKS_CACHE_KEY in _jwks_cache:
        return _jwks_cache[_JWKS_CACHE_KEY]

    try:
        jwks_url = _get_jwks_url()
        logger.debug(f"Fetching JWKS from {jwks_url}")
        with urlopen(jwks_url, timeout=10) as response:
            jwks = json.loads(response.read().decode("utf-8"))
            _jwks_cache[_JWKS_CACHE_KEY] = jwks
            logger.debug(f"Cached {len(jwks.get('keys', []))} JWKS keys")
            return jwks
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise


def _get_signing_key(token: str) -> Optional[dict]:
    """Get the signing key for the token from JWKS."""
    try:
        headers = jwt.get_unverified_headers(token)
        kid = headers.get("kid")
        if not kid:
            logger.warning("Token missing 'kid' header")
            return None

        jwks = _fetch_jwks()
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key

        logger.warning(f"No matching key found for kid: {kid}")
        return None
    except Exception as e:
        logger.error(f"Error getting signing key: {e}")
        return None


def verify_cognito_token(token: str) -> Optional[dict]:
    """
    Verify a Cognito JWT token and return the claims if valid.

    Args:
        token: The JWT token string (without 'Bearer ' prefix)

    Returns:
        dict with user claims if valid, None if invalid
    """
    if not COGNITO_ENABLED:
        logger.warning("Cognito authentication is not configured")
        return None

    try:
        # Get the signing key
        signing_key = _get_signing_key(token)
        if not signing_key:
            return None

        # Verify the token. Audience is deliberately NOT checked here - jose's
        # verify_aud only accepts one fixed value, but this API trusts a SET of
        # app clients (see COGNITO_TRUSTED_CLIENT_IDS). It is instead checked
        # explicitly below, against every trusted client, once we know which
        # claim actually carries it for this token type.
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=_get_issuer(),
            options={
                "verify_at_hash": False,  # Access tokens don't have at_hash
                "verify_aud": False,
            }
        )

        # Check token expiration (jose does this, but double-check)
        if claims.get("exp", 0) < time.time():
            logger.warning("Token has expired")
            return None

        # Check token use (should be 'access' for API calls)
        token_use = claims.get("token_use")
        if token_use not in ("access", "id"):
            logger.warning(f"Invalid token_use: {token_use}")
            return None

        # Bind the token to a TRUSTED app client.
        #
        # Cognito puts the client id in `aud` on ID tokens but in `client_id` on
        # access tokens. Left unchecked, any access token issued for ANY client
        # on the shared pool would authenticate here, since access tokens carry
        # no `aud` at all and jose's own audience check (disabled above anyway)
        # only ever supports one fixed value. COGNITO_TRUSTED_CLIENT_IDS always
        # includes this app's own client; other apps must be added explicitly
        # (e.g. Promethean AI's client, once it forwards its users' tokens here
        # instead of doing a separate KM login) - trust is opt-in per client,
        # never implied by "same pool".
        if COGNITO_TRUSTED_CLIENT_IDS:
            presented_client = (
                claims.get("client_id") if token_use == "access" else claims.get("aud")
            )
            if presented_client not in COGNITO_TRUSTED_CLIENT_IDS:
                logger.warning(
                    "Token was issued for an untrusted app client "
                    f"({presented_client!r}), rejecting"
                )
                return None

        logger.debug(f"Token verified for user: {claims.get('sub')}")
        return claims

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        return None


def get_cognito_user_info(claims: dict) -> dict:
    """
    Extract user information from Cognito token claims.

    Args:
        claims: The verified JWT claims

    Returns:
        dict with username, email, and cognito_sub
    """
    # 'sub' is the unique Cognito user identifier
    cognito_sub = claims.get("sub", "")

    # For access tokens, username is in 'username' claim
    # For id tokens, it might be in 'cognito:username'
    username = claims.get("username") or claims.get("cognito:username") or cognito_sub

    # Email might be in the token if requested in scopes
    email = claims.get("email", "")

    return {
        "cognito_sub": cognito_sub,
        "username": username,
        "email": email,
    }
