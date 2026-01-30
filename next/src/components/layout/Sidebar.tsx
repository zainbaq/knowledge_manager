'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useUIStore } from '@/lib/stores/ui-store';
import { Button } from '@/components/ui/button';
import {
  LayoutDashboard,
  Upload,
  Search,
  FolderOpen,
  Library,
  Settings2,
  Shield,
  BookOpen,
  User,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

export const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Upload', href: '/upload', icon: Upload },
  { name: 'Query', href: '/query', icon: Search },
  { name: 'Indexes', href: '/indexes', icon: FolderOpen },
  { name: 'Corpuses', href: '/corpuses', icon: Library },
  { name: 'Manage Corpuses', href: '/corpuses/manage', icon: Settings2 },
  { name: 'Admin', href: '/admin', icon: Shield },
  { name: 'Docs', href: '/docs', icon: BookOpen },
  { name: 'Account', href: '/account', icon: User },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen border-r bg-sidebar transition-all duration-300',
        'hidden md:flex flex-col',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      <div className="flex h-full flex-col">
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b px-4">
          {!sidebarCollapsed && (
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Library className="h-5 w-5" />
              </div>
              <span className="font-semibold text-lg">Knowledge</span>
            </Link>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className={cn('h-8 w-8', sidebarCollapsed && 'mx-auto')}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <ChevronLeft className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2">
          {navigation.map((item) => {
            const isActive = pathname === item.href ||
              (item.href !== '/' && pathname.startsWith(item.href));

            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                  sidebarCollapsed && 'justify-center px-2'
                )}
                title={sidebarCollapsed ? item.name : undefined}
              >
                <item.icon className="h-5 w-5 flex-shrink-0" />
                {!sidebarCollapsed && <span>{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        {!sidebarCollapsed && (
          <div className="border-t p-4">
            <p className="text-xs text-muted-foreground text-center">
              Knowledge Manager v1.0
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}
