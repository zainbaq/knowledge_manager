'use client';

import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import { UserMenu } from '@/components/auth/UserMenu';
import { useUIStore } from '@/lib/stores/ui-store';
import { cn } from '@/lib/utils';
import { Moon, Sun, Menu } from 'lucide-react';

export function Header() {
  const { theme, setTheme } = useTheme();
  const { sidebarCollapsed, toggleMobileMenu } = useUIStore();

  return (
    <header
      className={cn(
        'fixed top-0 z-30 flex h-16 items-center justify-between border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 md:px-6 transition-all duration-300 right-0',
        'left-0',
        sidebarCollapsed ? 'md:left-16' : 'md:left-64'
      )}
    >
      <div className="flex items-center gap-4">
        {/* Mobile menu button - shown only on small screens */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={toggleMobileMenu}
        >
          <Menu className="h-5 w-5" />
          <span className="sr-only">Toggle menu</span>
        </Button>
      </div>

      <div className="flex items-center gap-4">
        {/* Theme toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="h-9 w-9"
        >
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>

        {/* User menu */}
        <UserMenu />
      </div>
    </header>
  );
}
