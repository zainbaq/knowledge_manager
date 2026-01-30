Perfect! That makes this **way simpler**. Let me give you a streamlined plan:

# Simplified Cognito Implementation Plan (No Existing Users)

## Quick Setup (1-2 days)

### Step 1: Create Cognito User Pool (30 minutes)

**AWS Console:**
1. Cognito → **Create User Pool**
2. **Sign-in options:** Email
3. **Password policy:** Default is fine
4. **MFA:** Optional (recommend starting here)
5. **User account recovery:** Email only
6. **Self-registration:** Enabled
7. **Required attributes:** Email, Name
8. **Email delivery:** Cognito (upgrade to SES later if needed)
9. **User pool name:** `my-apps-users`
10. **Pricing tier:** **Select "Lite"** ✓
11. **Hosted UI domain:** 
    - Choose: `my-apps-auth` 
    - Full URL: `my-apps-auth.auth.us-east-1.amazoncognito.com`
    - Or custom domain: `auth.yourdomain.com` (requires SSL cert)

**Save these values:**
- User Pool ID: `us-east-1_xxxxxxxxx`
- Region: `us-east-1`

---

### Step 2: Add Google Login (15 minutes)

**In Google Cloud Console:**
1. [console.cloud.google.com](https://console.cloud.google.com)
2. APIs & Services → Credentials → Create OAuth 2.0 Client ID
3. **Application type:** Web application
4. **Authorized redirect URIs:**
   ```
   https://my-apps-auth.auth.us-east-1.amazoncognito.com/oauth2/idpresponse
   ```
5. Copy **Client ID** and **Client Secret**

**Back in Cognito:**
1. Your User Pool → Sign-in experience → Federated identity providers
2. **Add identity provider** → Google
3. Paste Client ID and Client Secret
4. **Authorized scopes:** `profile email openid`
5. **Attribute mapping:**
   - Google `email` → User pool `email`
   - Google `name` → User pool `name`

---

### Step 3: Create App Clients (10 minutes per app)

**For each app (App 1, App 2, etc):**

1. User Pool → App integration → **Create app client**
2. **App client name:** `app1-web` (or `app2-web`, etc)
3. **App type:** Public client (for frontend) or Confidential (for backend-only)
4. **Authentication flows:**
   - ✓ ALLOW_USER_SRP_AUTH
   - ✓ ALLOW_REFRESH_TOKEN_AUTH
5. **Callback URLs:**
   ```
   https://app1.example.com/auth/callback
   http://localhost:3000/auth/callback
   ```
6. **Sign-out URLs:**
   ```
   https://app1.example.com
   http://localhost:3000
   ```
7. **OAuth 2.0 grant types:** Authorization code grant
8. **OpenID Connect scopes:** openid, email, profile

**Save for each app:**
- App Client ID
- App Client Secret (if confidential)

---

## Integration Code

### Backend (Flask Example)

**Install dependencies:**
```bash
pip install pyjwt cryptography requests
```

**Create auth module:**
```python
# auth.py
from functools import wraps
from flask import request, jsonify, redirect
import jwt
from jwt import PyJWKClient
import os

# Configuration
REGION = os.getenv('AWS_REGION', 'us-east-1')
USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID')  # us-east-1_xxxxx
CLIENT_ID = os.getenv('COGNITO_CLIENT_ID')        # Your app client ID
COGNITO_DOMAIN = os.getenv('COGNITO_DOMAIN')      # my-apps-auth.auth.us-east-1.amazoncognito.com

# JWKS URL for token validation
JWKS_URL = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json'

def validate_token(token):
    """Validate JWT token from Cognito"""
    try:
        jwks_client = PyJWKClient(JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=['RS256'],
            audience=CLIENT_ID,
            issuer=f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}'
        )
        return decoded
    except Exception as e:
        print(f"Token validation failed: {e}")
        return None

def require_auth(f):
    """Decorator to protect routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Unauthorized'}), 401
        
        token = auth_header.split(' ')[1]
        user = validate_token(token)
        
        if not user:
            return jsonify({'error': 'Invalid token'}), 401
        
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated

# Routes
from flask import Flask
app = Flask(__name__)

@app.route('/api/user')
@require_auth
def get_user():
    return jsonify({
        'email': request.current_user['email'],
        'name': request.current_user['name'],
        'sub': request.current_user['sub']
    })

@app.route('/api/protected')
@require_auth
def protected():
    return jsonify({'message': f'Hello {request.current_user["email"]}'})
```

**.env file:**
```bash
AWS_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
COGNITO_CLIENT_ID=your-app-client-id
COGNITO_DOMAIN=my-apps-auth.auth.us-east-1.amazoncognito.com
```

---

### Frontend (React/Next.js)

**Install:**
```bash
npm install aws-amplify @aws-amplify/auth
```

**Configure Amplify:**
```javascript
// lib/auth.js
import { Amplify } from 'aws-amplify';
import { signIn, signOut, getCurrentUser, fetchAuthSession } from '@aws-amplify/auth';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_USER_POOL_ID,
      userPoolClientId: process.env.NEXT_PUBLIC_CLIENT_ID,
      loginWith: {
        oauth: {
          domain: process.env.NEXT_PUBLIC_COGNITO_DOMAIN,
          scopes: ['openid', 'email', 'profile'],
          redirectSignIn: ['http://localhost:3000/auth/callback'],
          redirectSignOut: ['http://localhost:3000'],
          responseType: 'code',
        }
      }
    }
  }
});

export { signIn, signOut, getCurrentUser, fetchAuthSession };
```

**Auth Context:**
```javascript
// context/AuthContext.js
'use client';
import { createContext, useContext, useEffect, useState } from 'react';
import { getCurrentUser, fetchAuthSession, signOut } from '@/lib/auth';

const AuthContext = createContext({});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkUser();
  }, []);

  async function checkUser() {
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  async function getToken() {
    try {
      const session = await fetchAuthSession();
      return session.tokens?.accessToken?.toString();
    } catch (err) {
      return null;
    }
  }

  async function logout() {
    await signOut();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, checkUser, getToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
```

**Login Button:**
```javascript
// components/LoginButton.js
'use client';
import { signInWithRedirect } from '@aws-amplify/auth';

export function LoginButton() {
  const handleLogin = async () => {
    await signInWithRedirect({ provider: 'Google' }); // Or { provider: { custom: 'Cognito' } } for email/password
  };

  return <button onClick={handleLogin}>Login with Google</button>;
}
```

**Protected Page:**
```javascript
// app/dashboard/page.js
'use client';
import { useAuth } from '@/context/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function Dashboard() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  if (loading) return <div>Loading...</div>;
  if (!user) return null;

  return <div>Welcome {user.username}!</div>;
}
```

**API Calls:**
```javascript
// lib/api.js
import { fetchAuthSession } from '@aws-amplify/auth';

export async function apiCall(endpoint, options = {}) {
  const session = await fetchAuthSession();
  const token = session.tokens?.accessToken?.toString();

  const response = await fetch(endpoint, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) throw new Error('API call failed');
  return response.json();
}

// Usage
const data = await apiCall('/api/user');
```

**.env.local:**
```bash
NEXT_PUBLIC_USER_POOL_ID=us-east-1_xxxxxxxxx
NEXT_PUBLIC_CLIENT_ID=your-app-client-id
NEXT_PUBLIC_COGNITO_DOMAIN=my-apps-auth.auth.us-east-1.amazoncognito.com
```

---

## Database Schema (Simple)

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    cognito_sub VARCHAR(255) UNIQUE NOT NULL,  -- From JWT 'sub' claim
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_cognito_sub ON users(cognito_sub);
```

**On first login, create user record:**
```python
@app.route('/api/auth/callback')
@require_auth
def auth_callback():
    cognito_sub = request.current_user['sub']
    
    # Check if user exists
    user = User.query.filter_by(cognito_sub=cognito_sub).first()
    
    if not user:
        # First login - create user record
        user = User(
            cognito_sub=cognito_sub,
            email=request.current_user['email'],
            name=request.current_user.get('name')
        )
        db.session.add(user)
        db.session.commit()
    
    return jsonify({'user_id': user.id})
```

---

## Testing (30 minutes)

### Test the flow:

1. **Start your app** (localhost:3000)
2. **Click "Login"** → Redirects to Cognito Hosted UI
3. **Click "Sign in with Google"** → Google OAuth
4. **Approve permissions** → Redirects back to your app
5. **Check:** `localStorage` should have tokens
6. **Check:** Protected API call works

**Test with email/password too:**
1. Click "Sign up" on Hosted UI
2. Enter email/password
3. Verify email (check inbox)
4. Login

---

## Deployment Checklist

**Update callback URLs in Cognito:**
```
https://app1.yourdomain.com/auth/callback
https://app2.yourdomain.com/auth/callback
```

**Environment variables for production:**
```bash
# Same values, just update domains in callback URLs
NEXT_PUBLIC_USER_POOL_ID=us-east-1_xxxxxxxxx
NEXT_PUBLIC_CLIENT_ID=your-app-client-id
NEXT_PUBLIC_COGNITO_DOMAIN=my-apps-auth.auth.us-east-1.amazoncognito.com
```

**CORS configuration** (if needed):
```python
from flask_cors import CORS

CORS(app, origins=[
    'https://app1.yourdomain.com',
    'https://app2.yourdomain.com',
    'http://localhost:3000'
])
```

---

## Single Sign-On Between Apps

**It just works!** Because they share the same User Pool:

1. User logs in to App 1 → Cognito session created
2. User navigates to App 2 → App 2 redirects to Cognito
3. Cognito sees active session → Auto-redirects back to App 2 with tokens
4. **No re-login needed!**

**Single Sign-Out:**
```javascript
// When user logs out from any app
await signOut({ global: true }); // Ends session across all apps
```

---

## Total Timeline

- **Day 1 Morning:** Cognito setup (1 hour)
- **Day 1 Afternoon:** Integrate App 1 (2-3 hours)
- **Day 2:** Integrate App 2, App 3, etc (1-2 hours each)
- **Testing:** 30 minutes

**Total: 1-2 days to production!**

---

## Costs

- **0-10,000 users:** $0/month
- You literally pay nothing until you hit 10k active users

---

Want me to help you with any specific integration? (Flask, FastAPI, Next.js, vanilla React, etc?)