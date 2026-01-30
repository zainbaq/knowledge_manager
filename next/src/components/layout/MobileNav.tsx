'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { useUIStore } from '@/lib/stores/ui-store';
import { cn } from '@/lib/utils';
import { Library } from 'lucide-react';
import { navigation } from './Sidebar';

export function MobileNav() {
  const pathname = usePathname();
  const { mobileMenuOpen, setMobileMenuOpen } = useUIStore();

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname, setMobileMenuOpen]);

  return (
    <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
      <SheetContent side="left" className="w-[280px] p-0">
        <SheetHeader className="h-16 flex flex-row items-center px-4 border-b">
          <Link
            href="/"
            className="flex items-center gap-2"
            onClick={() => setMobileMenuOpen(false)}
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Library className="h-5 w-5" />
            </div>
            <SheetTitle className="font-semibold text-lg">Knowledge</SheetTitle>
          </Link>
        </SheetHeader>
        <nav className="flex-1 space-y-1 p-2">
          {navigation.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== '/' && pathname.startsWith(item.href));

            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                <item.icon className="h-5 w-5 flex-shrink-0" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
        <div className="border-t p-4">
          <p className="text-xs text-muted-foreground text-center">
            Knowledge Manager v1.0
          </p>
        </div>
      </SheetContent>
    </Sheet>
  );
}
