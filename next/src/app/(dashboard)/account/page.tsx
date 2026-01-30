'use client';

import { useAuth } from '@/components/auth/AuthProvider';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { SignOutButton } from '@/components/auth/AuthButtons';
import { User, Mail, Shield, LogOut, Moon, Sun, Monitor } from 'lucide-react';
import { useTheme } from 'next-themes';

export default function AccountPage() {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Account Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your account and preferences.
        </p>
      </div>

      {/* Profile Card */}
      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>Your account information from Cognito.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {user ? (
            <>
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-primary-foreground text-2xl font-bold">
                  {user.attributes?.name
                    ?.split(' ')
                    .map((n) => n[0])
                    .join('')
                    .toUpperCase()
                    .slice(0, 2) || user.attributes?.email?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div>
                  <h3 className="text-lg font-semibold">
                    {user.attributes?.name || 'User'}
                  </h3>
                  <p className="text-muted-foreground">{user.attributes?.email}</p>
                </div>
              </div>

              <Separator />

              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <User className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Username</p>
                    <p className="text-sm text-muted-foreground">{user.username}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Mail className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">Email</p>
                    <p className="text-sm text-muted-foreground">
                      {user.attributes?.email}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Shield className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium">User ID</p>
                    <p className="text-sm text-muted-foreground font-mono">
                      {user.userId}
                    </p>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <p className="text-muted-foreground">Not signed in.</p>
          )}
        </CardContent>
      </Card>

      {/* Theme Preferences */}
      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>
            Customize how the application looks on your device.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium mb-3">Theme</p>
              <div className="flex gap-2">
                <Button
                  variant={theme === 'light' ? 'default' : 'outline'}
                  className="flex-1"
                  onClick={() => setTheme('light')}
                >
                  <Sun className="mr-2 h-4 w-4" />
                  Light
                </Button>
                <Button
                  variant={theme === 'dark' ? 'default' : 'outline'}
                  className="flex-1"
                  onClick={() => setTheme('dark')}
                >
                  <Moon className="mr-2 h-4 w-4" />
                  Dark
                </Button>
                <Button
                  variant={theme === 'system' ? 'default' : 'outline'}
                  className="flex-1"
                  onClick={() => setTheme('system')}
                >
                  <Monitor className="mr-2 h-4 w-4" />
                  System
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sign Out */}
      <Card>
        <CardHeader>
          <CardTitle>Session</CardTitle>
          <CardDescription>Manage your current session.</CardDescription>
        </CardHeader>
        <CardContent>
          <SignOutButton className="w-full" />
        </CardContent>
      </Card>
    </div>
  );
}
