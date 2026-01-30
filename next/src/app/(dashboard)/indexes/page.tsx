'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { indexApi } from '@/lib/api/client';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  FolderOpen,
  Search,
  Trash2,
  ChevronDown,
  FileText,
  Plus,
  LayoutGrid,
  List,
  Loader2,
} from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

export default function IndexesPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; name: string | null }>({
    open: false,
    name: null,
  });

  const { data: indexesData, isLoading } = useQuery({
    queryKey: ['indexes'],
    queryFn: indexApi.list,
  });

  const deleteMutation = useMutation({
    mutationFn: (name: string) => indexApi.delete(name),
    onSuccess: () => {
      toast.success('Index deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['indexes'] });
      setDeleteDialog({ open: false, name: null });
    },
    onError: (error: Error) => {
      toast.error('Failed to delete index', {
        description: error.message,
      });
    },
  });

  const filteredCollections = indexesData?.collections?.filter((collection) =>
    collection.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = () => {
    if (deleteDialog.name) {
      deleteMutation.mutate(deleteDialog.name);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Indexes</h1>
          <p className="text-muted-foreground mt-2">
            Manage your document indexes and collections.
          </p>
        </div>
        <Button asChild>
          <Link href="/upload">
            <Plus className="mr-2 h-4 w-4" />
            New Index
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search indexes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-1 border rounded-md p-1">
          <Button
            variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
            size="icon"
            className="h-8 w-8"
            onClick={() => setViewMode('grid')}
          >
            <LayoutGrid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'secondary' : 'ghost'}
            size="icon"
            className="h-8 w-8"
            onClick={() => setViewMode('list')}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className={cn(
          'gap-4',
          viewMode === 'grid' ? 'grid md:grid-cols-2 lg:grid-cols-3' : 'space-y-4'
        )}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredCollections?.length ? (
        <div className={cn(
          'gap-4',
          viewMode === 'grid' ? 'grid md:grid-cols-2 lg:grid-cols-3' : 'space-y-4'
        )}>
          {filteredCollections.map((collection) => (
            <Card key={collection.name}>
              <Collapsible>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FolderOpen className="h-5 w-5 text-primary" />
                      <CardTitle className="text-base">{collection.name}</CardTitle>
                    </div>
                    <CollapsibleTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <ChevronDown className="h-4 w-4" />
                      </Button>
                    </CollapsibleTrigger>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary">{collection.files.length} files</Badge>
                    <Badge variant="outline">{collection.num_chunks} chunks</Badge>
                  </div>
                </CardHeader>

                <CollapsibleContent>
                  <CardContent className="pt-2">
                    <div className="space-y-3">
                      {/* Files list */}
                      <div className="space-y-1">
                        <p className="text-sm font-medium text-muted-foreground mb-2">Files</p>
                        <div className="space-y-1 max-h-40 overflow-y-auto">
                          {collection.files.map((file, index) => (
                            <div
                              key={index}
                              className="flex items-center gap-2 text-sm py-1 px-2 rounded bg-muted/50"
                            >
                              <FileText className="h-4 w-4 text-muted-foreground" />
                              <span className="truncate">{file}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 pt-2 border-t">
                        <Button asChild variant="outline" size="sm" className="flex-1">
                          <Link href={`/query?collection=${collection.name}`}>
                            <Search className="mr-2 h-4 w-4" />
                            Query
                          </Link>
                        </Button>
                        <Button asChild variant="outline" size="sm" className="flex-1">
                          <Link href={`/upload?index=${collection.name}`}>
                            <Plus className="mr-2 h-4 w-4" />
                            Add Files
                          </Link>
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          className="h-8 w-8 text-destructive hover:bg-destructive hover:text-destructive-foreground"
                          onClick={() => setDeleteDialog({ open: true, name: collection.name })}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </CollapsibleContent>
              </Collapsible>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              {searchQuery ? 'No indexes found' : 'No indexes yet'}
            </h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery
                ? 'Try a different search term.'
                : 'Upload your first documents to create an index.'}
            </p>
            {!searchQuery && (
              <Button asChild>
                <Link href="/upload">
                  <Plus className="mr-2 h-4 w-4" />
                  Create Index
                </Link>
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onOpenChange={(open) => setDeleteDialog({ open, name: open ? deleteDialog.name : null })}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Index</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{deleteDialog.name}&quot;? This action cannot be
              undone and all indexed data will be permanently removed.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialog({ open: false, name: null })}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
