'use client';

import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/components/auth/AuthProvider';
import { indexApi } from '@/lib/api/client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Upload, Search, FolderOpen, Library, ArrowRight } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const { user, isAuthenticated } = useAuth();

  const { data: indexesData, isLoading } = useQuery({
    queryKey: ['indexes'],
    queryFn: indexApi.list,
    enabled: isAuthenticated,
  });

  const totalIndexes = indexesData?.collections?.length || 0;
  const totalChunks = indexesData?.collections?.reduce((acc, col) => acc + col.num_chunks, 0) || 0;
  const totalFiles = indexesData?.collections?.reduce((acc, col) => acc + col.files.length, 0) || 0;

  const quickActions = [
    {
      title: 'Upload Documents',
      description: 'Add new documents to your knowledge base',
      icon: Upload,
      href: '/upload',
      color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
    },
    {
      title: 'Query Knowledge',
      description: 'Search across your indexed documents',
      icon: Search,
      href: '/query',
      color: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
    },
    {
      title: 'Manage Indexes',
      description: 'View and manage your document indexes',
      icon: FolderOpen,
      href: '/indexes',
      color: 'bg-green-500/10 text-green-600 dark:text-green-400',
    },
    {
      title: 'Browse Corpuses',
      description: 'Discover and subscribe to public corpuses',
      icon: Library,
      href: '/corpuses',
      color: 'bg-orange-500/10 text-orange-600 dark:text-orange-400',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          Welcome back{user?.attributes?.name ? `, ${user.attributes.name.split(' ')[0]}` : ''}!
        </h1>
        <p className="text-muted-foreground mt-2">
          Manage your knowledge base and query your documents with AI-powered semantic search.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Indexes</CardTitle>
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">{totalIndexes}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <Upload className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">{totalFiles}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Chunks</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <div className="text-2xl font-bold">{totalChunks.toLocaleString()}</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
        <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
          {quickActions.map((action) => (
            <Card key={action.href} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${action.color}`}>
                  <action.icon className="h-6 w-6" />
                </div>
                <CardTitle className="text-lg">{action.title}</CardTitle>
                <CardDescription>{action.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button asChild variant="ghost" className="w-full justify-between">
                  <Link href={action.href}>
                    Get Started
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Recent Indexes */}
      {indexesData?.collections && indexesData.collections.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Recent Indexes</h2>
            <Button asChild variant="outline" size="sm">
              <Link href="/indexes">View All</Link>
            </Button>
          </div>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {indexesData.collections.slice(0, 6).map((collection) => (
              <Card key={collection.name}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base font-medium">{collection.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>{collection.files.length} files</span>
                    <span>{collection.num_chunks} chunks</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
