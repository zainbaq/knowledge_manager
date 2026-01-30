'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi } from '@/lib/api/client';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Shield,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  Users,
  BarChart3,
  Clock,
  Library,
} from 'lucide-react';
import type { PendingCorpus, UsageStats } from '@/types/api';

export default function AdminPage() {
  const queryClient = useQueryClient();
  const [corpusId, setCorpusId] = useState('');
  const [userId, setUserId] = useState('');
  const [corpusStats, setCorpusStats] = useState<UsageStats | null>(null);
  const [userStats, setUserStats] = useState<UsageStats | null>(null);

  const {
    data: pendingCorpuses,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['admin', 'pending-corpuses'],
    queryFn: adminApi.getPendingCorpuses,
    retry: false,
  });

  const approveMutation = useMutation({
    mutationFn: adminApi.approveCorpus,
    onSuccess: () => {
      toast.success('Corpus approved successfully');
      queryClient.invalidateQueries({ queryKey: ['admin', 'pending-corpuses'] });
    },
    onError: (error: Error) => {
      toast.error('Failed to approve corpus', { description: error.message });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: adminApi.rejectCorpus,
    onSuccess: () => {
      toast.success('Corpus rejected');
      queryClient.invalidateQueries({ queryKey: ['admin', 'pending-corpuses'] });
    },
    onError: (error: Error) => {
      toast.error('Failed to reject corpus', { description: error.message });
    },
  });

  const corpusStatsMutation = useMutation({
    mutationFn: (id: number) => adminApi.getCorpusUsage(id),
    onSuccess: (data) => {
      setCorpusStats(data);
    },
    onError: (error: Error) => {
      toast.error('Failed to fetch corpus stats', { description: error.message });
    },
  });

  const userStatsMutation = useMutation({
    mutationFn: (id: number) => adminApi.getUserUsage(id),
    onSuccess: (data) => {
      setUserStats(data);
    },
    onError: (error: Error) => {
      toast.error('Failed to fetch user stats', { description: error.message });
    },
  });

  // Check for 403 error (not admin)
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
        </div>
        <Card className="border-destructive">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <AlertCircle className="h-12 w-12 text-destructive mb-4" />
            <h3 className="text-lg font-semibold mb-2">Access Denied</h3>
            <p className="text-muted-foreground">
              You don&apos;t have permission to access the admin dashboard.
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Contact an administrator to be added to the ADMIN_USERS list.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
        <p className="text-muted-foreground mt-2">
          Manage corpus approvals and view usage statistics.
        </p>
      </div>

      <Tabs defaultValue="pending" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pending" className="gap-2">
            <Shield className="h-4 w-4" />
            Pending Approvals
          </TabsTrigger>
          <TabsTrigger value="corpus-stats" className="gap-2">
            <Library className="h-4 w-4" />
            Corpus Stats
          </TabsTrigger>
          <TabsTrigger value="user-stats" className="gap-2">
            <Users className="h-4 w-4" />
            User Stats
          </TabsTrigger>
        </TabsList>

        {/* Pending Approvals Tab */}
        <TabsContent value="pending" className="space-y-4">
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Card key={i}>
                  <CardHeader>
                    <Skeleton className="h-5 w-32" />
                  </CardHeader>
                  <CardContent>
                    <Skeleton className="h-16 w-full" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : pendingCorpuses?.length ? (
            <div className="space-y-4">
              {pendingCorpuses.map((corpus) => (
                <PendingCorpusCard
                  key={corpus.id}
                  corpus={corpus}
                  onApprove={() => approveMutation.mutate(corpus.id)}
                  onReject={() => rejectMutation.mutate(corpus.id)}
                  isApproving={approveMutation.isPending}
                  isRejecting={rejectMutation.isPending}
                />
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
                <h3 className="text-lg font-semibold mb-2">All caught up!</h3>
                <p className="text-muted-foreground">No corpuses pending approval.</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Corpus Stats Tab */}
        <TabsContent value="corpus-stats" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Corpus Usage Statistics</CardTitle>
              <CardDescription>
                Enter a corpus ID to view its usage statistics.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <div className="flex-1">
                  <Label htmlFor="corpusId">Corpus ID</Label>
                  <Input
                    id="corpusId"
                    type="number"
                    placeholder="Enter corpus ID"
                    value={corpusId}
                    onChange={(e) => setCorpusId(e.target.value)}
                  />
                </div>
                <Button
                  className="mt-6"
                  onClick={() => corpusStatsMutation.mutate(parseInt(corpusId))}
                  disabled={!corpusId || corpusStatsMutation.isPending}
                >
                  {corpusStatsMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <BarChart3 className="mr-2 h-4 w-4" />
                  )}
                  Get Stats
                </Button>
              </div>

              {corpusStats && (
                <div className="grid gap-4 md:grid-cols-4 mt-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Unique Users
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">
                        {corpusStats.unique_users ?? 'N/A'}
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Total Actions
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{corpusStats.total_actions}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Total Queries
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{corpusStats.total_queries}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Last Access
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-sm font-medium">
                        {corpusStats.last_access
                          ? new Date(corpusStats.last_access).toLocaleDateString()
                          : 'Never'}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* User Stats Tab */}
        <TabsContent value="user-stats" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>User Usage Statistics</CardTitle>
              <CardDescription>
                Enter a user ID to view their usage statistics.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4">
                <div className="flex-1">
                  <Label htmlFor="userId">User ID</Label>
                  <Input
                    id="userId"
                    type="number"
                    placeholder="Enter user ID"
                    value={userId}
                    onChange={(e) => setUserId(e.target.value)}
                  />
                </div>
                <Button
                  className="mt-6"
                  onClick={() => userStatsMutation.mutate(parseInt(userId))}
                  disabled={!userId || userStatsMutation.isPending}
                >
                  {userStatsMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <BarChart3 className="mr-2 h-4 w-4" />
                  )}
                  Get Stats
                </Button>
              </div>

              {userStats && (
                <div className="grid gap-4 md:grid-cols-3 mt-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Total Actions
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{userStats.total_actions}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Total Queries
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{userStats.total_queries}</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-muted-foreground">
                        Last Access
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-sm font-medium">
                        {userStats.last_access
                          ? new Date(userStats.last_access).toLocaleDateString()
                          : 'Never'}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function PendingCorpusCard({
  corpus,
  onApprove,
  onReject,
  isApproving,
  isRejecting,
}: {
  corpus: PendingCorpus;
  onApprove: () => void;
  onReject: () => void;
  isApproving: boolean;
  isRejecting: boolean;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-base">{corpus.display_name}</CardTitle>
            <CardDescription className="mt-1">
              by {corpus.owner_username} &bull; v{corpus.version}
            </CardDescription>
          </div>
          <Badge variant="outline">
            <Clock className="mr-1 h-3 w-3" />
            Pending
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {corpus.description && (
          <p className="text-sm text-muted-foreground">{corpus.description}</p>
        )}
        <div className="flex gap-2 text-xs">
          <Badge variant="secondary">ID: {corpus.id}</Badge>
          <Badge variant="secondary">{corpus.name}</Badge>
          {corpus.category && <Badge variant="outline">{corpus.category}</Badge>}
        </div>
        <div className="flex gap-2">
          <Button
            onClick={onApprove}
            disabled={isApproving || isRejecting}
            className="bg-green-600 hover:bg-green-700"
          >
            {isApproving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle className="mr-2 h-4 w-4" />
            )}
            Approve
          </Button>
          <Button
            variant="destructive"
            onClick={onReject}
            disabled={isApproving || isRejecting}
          >
            {isRejecting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <XCircle className="mr-2 h-4 w-4" />
            )}
            Reject
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
