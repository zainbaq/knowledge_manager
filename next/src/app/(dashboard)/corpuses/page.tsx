'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { corpusApi } from '@/lib/api/client';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Library,
  Search,
  Globe,
  Lock,
  Key,
  CheckCircle,
  Clock,
  Loader2,
  MessageSquare,
} from 'lucide-react';
import Link from 'next/link';
import type { Corpus } from '@/types/api';

export default function BrowseCorpusesPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [approvedOnly, setApprovedOnly] = useState(true);
  const [queryDialog, setQueryDialog] = useState<{ open: boolean; corpus: Corpus | null }>({
    open: false,
    corpus: null,
  });
  const [corpusQuery, setCorpusQuery] = useState('');
  const [queryResult, setQueryResult] = useState<string | null>(null);

  const { data: corpuses, isLoading } = useQuery({
    queryKey: ['corpuses'],
    queryFn: corpusApi.list,
  });

  const subscribeMutation = useMutation({
    mutationFn: ({ id, tier }: { id: number; tier: 'free' | 'basic' | 'premium' }) =>
      corpusApi.subscribe(id, { tier }),
    onSuccess: () => {
      toast.success('Successfully subscribed!');
      queryClient.invalidateQueries({ queryKey: ['corpuses'] });
    },
    onError: (error: Error) => {
      toast.error('Subscription failed', { description: error.message });
    },
  });

  const unsubscribeMutation = useMutation({
    mutationFn: (id: number) => corpusApi.unsubscribe(id),
    onSuccess: () => {
      toast.success('Successfully unsubscribed');
      queryClient.invalidateQueries({ queryKey: ['corpuses'] });
    },
    onError: (error: Error) => {
      toast.error('Unsubscribe failed', { description: error.message });
    },
  });

  const corpusQueryMutation = useMutation({
    mutationFn: ({ id, query }: { id: number; query: string }) =>
      corpusApi.query(id, query),
    onSuccess: (data) => {
      setQueryResult(data.context);
    },
    onError: (error: Error) => {
      toast.error('Query failed', { description: error.message });
    },
  });

  // Get unique categories
  const categories = Array.from(
    new Set(corpuses?.map((c) => c.category).filter(Boolean) as string[])
  );

  // Filter corpuses
  const filteredCorpuses = corpuses?.filter((corpus) => {
    const matchesSearch =
      corpus.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      corpus.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      corpus.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === 'all' || corpus.category === categoryFilter;
    const matchesApproval = !approvedOnly || corpus.is_approved;
    return matchesSearch && matchesCategory && matchesApproval;
  });

  const handleQuery = () => {
    if (queryDialog.corpus && corpusQuery.trim()) {
      corpusQueryMutation.mutate({
        id: queryDialog.corpus.id,
        query: corpusQuery,
      });
    }
  };

  const getAccessBadge = (corpus: Corpus) => {
    if (corpus.is_owner) {
      return (
        <Badge variant="default" className="bg-purple-600">
          <Key className="mr-1 h-3 w-3" />
          Owner
        </Badge>
      );
    }
    if (corpus.user_permission) {
      return (
        <Badge variant="default" className="bg-green-600">
          <CheckCircle className="mr-1 h-3 w-3" />
          {corpus.user_permission}
        </Badge>
      );
    }
    if (corpus.is_public && corpus.is_approved) {
      return (
        <Badge variant="secondary">
          <Globe className="mr-1 h-3 w-3" />
          Public
        </Badge>
      );
    }
    return (
      <Badge variant="outline">
        <Lock className="mr-1 h-3 w-3" />
        Private
      </Badge>
    );
  };

  const hasAccess = (corpus: Corpus) =>
    corpus.is_owner || corpus.user_permission || (corpus.is_public && corpus.is_approved);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Browse Corpuses</h1>
          <p className="text-muted-foreground mt-2">
            Discover and subscribe to curated knowledge corpuses.
          </p>
        </div>
        <Button asChild>
          <Link href="/corpuses/manage">Manage My Corpuses</Link>
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search corpuses..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="flex items-center gap-2">
              <Checkbox
                id="approvedOnly"
                checked={approvedOnly}
                onCheckedChange={(checked) => setApprovedOnly(checked as boolean)}
              />
              <Label htmlFor="approvedOnly">Approved only</Label>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results count */}
      {filteredCorpuses && (
        <p className="text-sm text-muted-foreground">
          Showing {filteredCorpuses.length} corpus{filteredCorpuses.length !== 1 ? 'es' : ''}
        </p>
      )}

      {/* Corpus Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-48" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredCorpuses?.length ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredCorpuses.map((corpus) => (
            <Card key={corpus.id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Library className="h-5 w-5 text-primary" />
                    <CardTitle className="text-base">{corpus.display_name}</CardTitle>
                  </div>
                  {getAccessBadge(corpus)}
                </div>
                <CardDescription className="line-clamp-2">
                  {corpus.description || 'No description available'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-2 text-xs">
                  {corpus.category && (
                    <Badge variant="outline">{corpus.category}</Badge>
                  )}
                  <Badge variant="secondary">{corpus.num_chunks} chunks</Badge>
                  <Badge variant="secondary">{corpus.num_files} files</Badge>
                  {corpus.is_approved ? (
                    <Badge variant="default" className="bg-green-600">
                      <CheckCircle className="mr-1 h-3 w-3" />
                      Approved
                    </Badge>
                  ) : (
                    <Badge variant="outline">
                      <Clock className="mr-1 h-3 w-3" />
                      Pending
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {hasAccess(corpus) ? (
                    <>
                      <Button
                        variant="default"
                        size="sm"
                        className="flex-1"
                        onClick={() => {
                          setQueryDialog({ open: true, corpus });
                          setCorpusQuery('');
                          setQueryResult(null);
                        }}
                      >
                        <MessageSquare className="mr-2 h-4 w-4" />
                        Query
                      </Button>
                      {corpus.user_permission && !corpus.is_owner && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => unsubscribeMutation.mutate(corpus.id)}
                          disabled={unsubscribeMutation.isPending}
                        >
                          Unsubscribe
                        </Button>
                      )}
                    </>
                  ) : corpus.is_public && corpus.is_approved ? (
                    <Button
                      variant="default"
                      size="sm"
                      className="w-full"
                      onClick={() => subscribeMutation.mutate({ id: corpus.id, tier: 'free' })}
                      disabled={subscribeMutation.isPending}
                    >
                      {subscribeMutation.isPending ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : null}
                      Subscribe (Free)
                    </Button>
                  ) : (
                    <Button variant="outline" size="sm" className="w-full" disabled>
                      Not Available
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Library className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No corpuses found</h3>
            <p className="text-muted-foreground">
              {searchQuery || categoryFilter !== 'all' || approvedOnly
                ? 'Try adjusting your filters.'
                : 'No corpuses are available yet.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Query Dialog */}
      <Dialog
        open={queryDialog.open}
        onOpenChange={(open) => {
          setQueryDialog({ open, corpus: open ? queryDialog.corpus : null });
          if (!open) {
            setCorpusQuery('');
            setQueryResult(null);
          }
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Query {queryDialog.corpus?.display_name}</DialogTitle>
            <DialogDescription>
              Search this corpus using natural language.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="corpusQuery">Query</Label>
              <Textarea
                id="corpusQuery"
                placeholder="What would you like to know?"
                value={corpusQuery}
                onChange={(e) => setCorpusQuery(e.target.value)}
                rows={3}
              />
            </div>
            {queryResult && (
              <div className="space-y-2">
                <Label>Results</Label>
                <ScrollArea className="h-48 rounded-md border p-4">
                  <pre className="text-sm whitespace-pre-wrap">{queryResult}</pre>
                </ScrollArea>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setQueryDialog({ open: false, corpus: null })}
            >
              Close
            </Button>
            <Button
              onClick={handleQuery}
              disabled={!corpusQuery.trim() || corpusQueryMutation.isPending}
            >
              {corpusQueryMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Querying...
                </>
              ) : (
                <>
                  <Search className="mr-2 h-4 w-4" />
                  Query
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
