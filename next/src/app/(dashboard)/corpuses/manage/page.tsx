'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { corpusApi } from '@/lib/api/client';
import { toast } from 'sonner';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Checkbox } from '@/components/ui/checkbox';
import { Separator } from '@/components/ui/separator';
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
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Library,
  Plus,
  Trash2,
  ChevronDown,
  Globe,
  Lock,
  CheckCircle,
  Clock,
  Loader2,
  History,
  Save,
} from 'lucide-react';
import type { Corpus, CorpusVersion } from '@/types/api';

const createCorpusSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .max(64)
    .regex(/^[a-zA-Z0-9_-]+$/, 'Only letters, numbers, hyphens, and underscores'),
  display_name: z.string().min(1, 'Display name is required').max(255),
  description: z.string().optional(),
  category: z.string().optional(),
  is_public: z.boolean(),
});

type CreateCorpusForm = z.infer<typeof createCorpusSchema>;

export default function ManageCorpusesPage() {
  const queryClient = useQueryClient();
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; corpus: Corpus | null }>({
    open: false,
    corpus: null,
  });
  const [versionDialog, setVersionDialog] = useState<{ open: boolean; corpusId: number | null }>({
    open: false,
    corpusId: null,
  });
  const [versionDescription, setVersionDescription] = useState('');

  const form = useForm<CreateCorpusForm>({
    resolver: zodResolver(createCorpusSchema),
    defaultValues: {
      name: '',
      display_name: '',
      description: '',
      category: '',
      is_public: false,
    },
  });

  const { data: corpuses, isLoading } = useQuery({
    queryKey: ['corpuses'],
    queryFn: corpusApi.list,
  });

  const myCorpuses = corpuses?.filter((c) => c.is_owner);

  const createMutation = useMutation({
    mutationFn: corpusApi.create,
    onSuccess: () => {
      toast.success('Corpus created successfully');
      form.reset();
      queryClient.invalidateQueries({ queryKey: ['corpuses'] });
    },
    onError: (error: Error) => {
      toast.error('Failed to create corpus', { description: error.message });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CreateCorpusForm> }) =>
      corpusApi.update(id, data),
    onSuccess: () => {
      toast.success('Corpus updated successfully');
      queryClient.invalidateQueries({ queryKey: ['corpuses'] });
    },
    onError: (error: Error) => {
      toast.error('Failed to update corpus', { description: error.message });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => corpusApi.delete(id),
    onSuccess: () => {
      toast.success('Corpus deleted successfully');
      setDeleteDialog({ open: false, corpus: null });
      queryClient.invalidateQueries({ queryKey: ['corpuses'] });
    },
    onError: (error: Error) => {
      toast.error('Failed to delete corpus', { description: error.message });
    },
  });

  const createVersionMutation = useMutation({
    mutationFn: ({ id, description }: { id: number; description?: string }) =>
      corpusApi.createVersion(id, description),
    onSuccess: (data) => {
      toast.success(`Version ${data.version} created successfully`);
      setVersionDialog({ open: false, corpusId: null });
      setVersionDescription('');
    },
    onError: (error: Error) => {
      toast.error('Failed to create version', { description: error.message });
    },
  });

  const onSubmit = (data: CreateCorpusForm) => {
    createMutation.mutate(data);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Manage Corpuses</h1>
        <p className="text-muted-foreground mt-2">
          Create and manage your knowledge corpuses.
        </p>
      </div>

      {/* Create New Corpus */}
      <Card>
        <CardHeader>
          <CardTitle>Create New Corpus</CardTitle>
          <CardDescription>
            Create a new corpus to organize and share your knowledge.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Corpus Name *</FormLabel>
                      <FormControl>
                        <Input placeholder="my_legal_corpus" {...field} />
                      </FormControl>
                      <FormDescription>
                        Unique identifier (lowercase, no spaces)
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="display_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Display Name *</FormLabel>
                      <FormControl>
                        <Input placeholder="Legal Knowledge Base" {...field} />
                      </FormControl>
                      <FormDescription>Human-readable name</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="A comprehensive collection of legal documents..."
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="grid gap-4 md:grid-cols-2">
                <FormField
                  control={form.control}
                  name="category"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Category</FormLabel>
                      <FormControl>
                        <Input placeholder="Legal" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="is_public"
                  render={({ field }) => (
                    <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                      <FormControl>
                        <Checkbox
                          checked={field.value}
                          onCheckedChange={field.onChange}
                        />
                      </FormControl>
                      <div className="space-y-1 leading-none">
                        <FormLabel>Make Public</FormLabel>
                        <FormDescription>
                          Public corpuses require admin approval
                        </FormDescription>
                      </div>
                    </FormItem>
                  )}
                />
              </div>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="mr-2 h-4 w-4" />
                    Create Corpus
                  </>
                )}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      {/* My Corpuses */}
      <div>
        <h2 className="text-xl font-semibold mb-4">My Corpuses</h2>
        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-32" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-20 w-full" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : myCorpuses?.length ? (
          <div className="space-y-4">
            {myCorpuses.map((corpus) => (
              <CorpusCard
                key={corpus.id}
                corpus={corpus}
                onUpdate={(data) => updateMutation.mutate({ id: corpus.id, data })}
                onDelete={() => setDeleteDialog({ open: true, corpus })}
                onCreateVersion={() => setVersionDialog({ open: true, corpusId: corpus.id })}
                isUpdating={updateMutation.isPending}
              />
            ))}
          </div>
        ) : (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <Library className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No corpuses yet</h3>
              <p className="text-muted-foreground">
                Create your first corpus above to get started.
              </p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Delete Dialog */}
      <Dialog
        open={deleteDialog.open}
        onOpenChange={(open) => setDeleteDialog({ open, corpus: open ? deleteDialog.corpus : null })}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Corpus</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{deleteDialog.corpus?.display_name}&quot;? This
              action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialog({ open: false, corpus: null })}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteDialog.corpus && deleteMutation.mutate(deleteDialog.corpus.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Version Dialog */}
      <Dialog
        open={versionDialog.open}
        onOpenChange={(open) => {
          setVersionDialog({ open, corpusId: open ? versionDialog.corpusId : null });
          if (!open) setVersionDescription('');
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Version Snapshot</DialogTitle>
            <DialogDescription>
              Create a new version of this corpus to preserve its current state.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="versionDesc">Version Description (optional)</Label>
              <Textarea
                id="versionDesc"
                placeholder="What changed in this version..."
                value={versionDescription}
                onChange={(e) => setVersionDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setVersionDialog({ open: false, corpusId: null })}
            >
              Cancel
            </Button>
            <Button
              onClick={() =>
                versionDialog.corpusId &&
                createVersionMutation.mutate({
                  id: versionDialog.corpusId,
                  description: versionDescription || undefined,
                })
              }
              disabled={createVersionMutation.isPending}
            >
              {createVersionMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <History className="mr-2 h-4 w-4" />
              )}
              Create Version
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function CorpusCard({
  corpus,
  onUpdate,
  onDelete,
  onCreateVersion,
  isUpdating,
}: {
  corpus: Corpus;
  onUpdate: (data: Partial<CreateCorpusForm>) => void;
  onDelete: () => void;
  onCreateVersion: () => void;
  isUpdating: boolean;
}) {
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({
    display_name: corpus.display_name,
    description: corpus.description || '',
    category: corpus.category || '',
    is_public: corpus.is_public,
  });

  const { data: versions } = useQuery({
    queryKey: ['corpus-versions', corpus.id],
    queryFn: () => corpusApi.listVersions(corpus.id),
    enabled: editMode,
  });

  const handleSave = () => {
    onUpdate(editData);
    setEditMode(false);
  };

  return (
    <Card>
      <Collapsible>
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <Library className="h-5 w-5 text-primary" />
              <CardTitle className="text-base">{corpus.display_name}</CardTitle>
            </div>
            <div className="flex items-center gap-2">
              {corpus.is_public ? (
                corpus.is_approved ? (
                  <Badge variant="default" className="bg-green-600">
                    <Globe className="mr-1 h-3 w-3" />
                    Public (Approved)
                  </Badge>
                ) : (
                  <Badge variant="outline">
                    <Clock className="mr-1 h-3 w-3" />
                    Pending Approval
                  </Badge>
                )
              ) : (
                <Badge variant="secondary">
                  <Lock className="mr-1 h-3 w-3" />
                  Private
                </Badge>
              )}
              <CollapsibleTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </CollapsibleTrigger>
            </div>
          </div>
          <div className="flex gap-2 text-xs mt-2">
            <Badge variant="secondary">{corpus.num_chunks} chunks</Badge>
            <Badge variant="secondary">{corpus.num_files} files</Badge>
            {corpus.category && <Badge variant="outline">{corpus.category}</Badge>}
          </div>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="pt-2 space-y-4">
            {editMode ? (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Display Name</Label>
                  <Input
                    value={editData.display_name}
                    onChange={(e) =>
                      setEditData((prev) => ({ ...prev, display_name: e.target.value }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    value={editData.description}
                    onChange={(e) =>
                      setEditData((prev) => ({ ...prev, description: e.target.value }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Input
                    value={editData.category}
                    onChange={(e) =>
                      setEditData((prev) => ({ ...prev, category: e.target.value }))
                    }
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Checkbox
                    checked={editData.is_public}
                    onCheckedChange={(checked) =>
                      setEditData((prev) => ({ ...prev, is_public: checked as boolean }))
                    }
                  />
                  <Label>Make Public</Label>
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleSave} disabled={isUpdating}>
                    {isUpdating ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Save className="mr-2 h-4 w-4" />
                    )}
                    Save
                  </Button>
                  <Button variant="outline" onClick={() => setEditMode(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <>
                {corpus.description && (
                  <p className="text-sm text-muted-foreground">{corpus.description}</p>
                )}

                {/* Version History */}
                {versions?.versions && versions.versions.length > 0 && (
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">Version History</Label>
                    <div className="space-y-1 max-h-32 overflow-y-auto">
                      {versions.versions.map((version) => (
                        <div
                          key={version.version}
                          className="flex items-center justify-between text-xs py-1 px-2 rounded bg-muted/50"
                        >
                          <span>v{version.version}</span>
                          <span className="text-muted-foreground">
                            {version.num_chunks} chunks
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <Separator />

                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={() => setEditMode(true)}>
                    Edit
                  </Button>
                  <Button variant="outline" size="sm" onClick={onCreateVersion}>
                    <History className="mr-2 h-4 w-4" />
                    Create Version
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
                    onClick={onDelete}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
