'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { indexApi } from '@/lib/api/client';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, Copy, Check, ChevronDown, FileText, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { QueryResponse } from '@/types/api';

export default function QueryPage() {
  const [query, setQuery] = useState('');
  const [selectedCollections, setSelectedCollections] = useState<string[]>([]);
  const [results, setResults] = useState<QueryResponse | null>(null);
  const [copiedContext, setCopiedContext] = useState(false);

  const { data: indexesData, isLoading: isLoadingIndexes } = useQuery({
    queryKey: ['indexes'],
    queryFn: indexApi.list,
  });

  const queryMutation = useMutation({
    mutationFn: async () => {
      const payload: { query: string; collection?: string; collections?: string[] } = {
        query,
      };

      if (selectedCollections.length === 1) {
        payload.collection = selectedCollections[0];
      } else if (selectedCollections.length > 1) {
        payload.collections = selectedCollections;
      }

      return indexApi.query(payload);
    },
    onSuccess: (data) => {
      setResults(data);
      toast.success('Query completed!');
    },
    onError: (error: Error) => {
      toast.error('Query failed', {
        description: error.message,
      });
    },
  });

  const toggleCollection = (name: string) => {
    setSelectedCollections((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      queryMutation.mutate();
    }
  };

  const copyContext = async () => {
    if (results?.context) {
      await navigator.clipboard.writeText(results.context);
      setCopiedContext(true);
      toast.success('Context copied to clipboard');
      setTimeout(() => setCopiedContext(false), 2000);
    }
  };

  const calculateSimilarity = (distance: number) => {
    // Convert cosine distance to similarity percentage
    return Math.max(0, Math.min(100, (1 - distance) * 100));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Query Knowledge</h1>
        <p className="text-muted-foreground mt-2">
          Search across your indexed documents using natural language.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Search Query</CardTitle>
              <CardDescription>
                Enter your question or search terms. Use Cmd/Ctrl + Enter to submit.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="query">Query</Label>
                  <Textarea
                    id="query"
                    placeholder="What would you like to know?"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                        handleSubmit(e);
                      }
                    }}
                    rows={4}
                    className="resize-none"
                  />
                </div>

                <Button
                  type="submit"
                  disabled={!query.trim() || queryMutation.isPending}
                  className="w-full"
                >
                  {queryMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <Search className="mr-2 h-4 w-4" />
                      Search
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Results */}
          {results && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Results</CardTitle>
                  <CardDescription>
                    {results.raw_results.documents[0]?.length || 0} matching chunks found
                  </CardDescription>
                </div>
                <Button variant="outline" size="sm" onClick={copyContext}>
                  {copiedContext ? (
                    <Check className="mr-2 h-4 w-4" />
                  ) : (
                    <Copy className="mr-2 h-4 w-4" />
                  )}
                  Copy Context
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Context */}
                <div className="space-y-2">
                  <Label>Compiled Context</Label>
                  <ScrollArea className="h-48 rounded-md border p-4">
                    <pre className="text-sm whitespace-pre-wrap font-mono">
                      {results.context}
                    </pre>
                  </ScrollArea>
                </div>

                {/* Source Documents */}
                <div className="space-y-2">
                  <Label>Source Documents</Label>
                  <div className="space-y-2">
                    {results.raw_results.documents[0]?.map((doc, index) => {
                      const metadata = results.raw_results.metadatas[0]?.[index] || {};
                      const distance = results.raw_results.distances[0]?.[index] || 0;
                      const similarity = calculateSimilarity(distance);

                      return (
                        <Collapsible key={index}>
                          <Card>
                            <CollapsibleTrigger className="w-full">
                              <CardHeader className="py-3 px-4">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <FileText className="h-4 w-4 text-muted-foreground" />
                                    <span className="font-medium text-sm">
                                      {(metadata.source as string) || 'Unknown'}
                                    </span>
                                    <Badge variant="outline" className="text-xs">
                                      Chunk {(metadata.chunk_index as number) || 0}
                                    </Badge>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <Badge
                                      variant={similarity > 80 ? 'default' : 'secondary'}
                                      className={cn(
                                        'text-xs',
                                        similarity > 80 && 'bg-green-600'
                                      )}
                                    >
                                      {similarity.toFixed(1)}% match
                                    </Badge>
                                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                  </div>
                                </div>
                              </CardHeader>
                            </CollapsibleTrigger>
                            <CollapsibleContent>
                              <CardContent className="pt-0 px-4 pb-4">
                                <ScrollArea className="h-32">
                                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                                    {doc}
                                  </p>
                                </ScrollArea>
                              </CardContent>
                            </CollapsibleContent>
                          </Card>
                        </Collapsible>
                      );
                    })}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Collections Sidebar */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-base">Collections</CardTitle>
            <CardDescription>
              Select collections to search. Leave empty to search all.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingIndexes ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : indexesData?.collections?.length ? (
              <div className="space-y-2">
                {selectedCollections.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedCollections([])}
                    className="w-full justify-start text-muted-foreground"
                  >
                    Clear selection
                  </Button>
                )}
                {indexesData.collections.map((collection) => (
                  <Button
                    key={collection.name}
                    variant={selectedCollections.includes(collection.name) ? 'default' : 'outline'}
                    className="w-full justify-start"
                    onClick={() => toggleCollection(collection.name)}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="truncate">{collection.name}</span>
                      <Badge variant="secondary" className="ml-2">
                        {collection.num_chunks}
                      </Badge>
                    </div>
                  </Button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                No collections found. Upload documents first.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
