'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { indexApi } from '@/lib/api/client';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Upload, File, X, Loader2, CheckCircle, FolderPlus } from 'lucide-react';
import { cn } from '@/lib/utils';

const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md'];
const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25MB

export default function UploadPage() {
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<File[]>([]);
  const [indexName, setIndexName] = useState('');
  const [mode, setMode] = useState<'new' | 'existing'>('new');
  const [selectedIndex, setSelectedIndex] = useState('');

  const { data: indexesData } = useQuery({
    queryKey: ['indexes'],
    queryFn: indexApi.list,
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const collection = mode === 'new' ? indexName : selectedIndex;
      if (mode === 'new') {
        return indexApi.create(collection, files);
      } else {
        return indexApi.update(collection, files);
      }
    },
    onSuccess: (data) => {
      toast.success('Upload successful!', {
        description: `Indexed ${data.indexed_chunks} chunks from ${files.length} file(s)`,
      });
      setFiles([]);
      setIndexName('');
      setSelectedIndex('');
      queryClient.invalidateQueries({ queryKey: ['indexes'] });
    },
    onError: (error: Error) => {
      toast.error('Upload failed', {
        description: error.message,
      });
    },
  });

  const onDrop = useCallback((acceptedFiles: File[], fileRejections: import('react-dropzone').FileRejection[]) => {
    // Handle rejected files
    fileRejections.forEach(({ file, errors }) => {
      errors.forEach((error) => {
        toast.error(`${file.name}: ${error.message}`);
      });
    });

    // Add accepted files
    setFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
    },
    maxSize: MAX_FILE_SIZE,
  });

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const canSubmit = files.length > 0 && (mode === 'new' ? indexName.trim() : selectedIndex);

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Upload Documents</h1>
        <p className="text-muted-foreground mt-2">
          Upload documents to create or update a knowledge index.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Index Settings</CardTitle>
          <CardDescription>
            Choose whether to create a new index or add to an existing one.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <Button
              variant={mode === 'new' ? 'default' : 'outline'}
              onClick={() => setMode('new')}
              className="flex-1"
            >
              <FolderPlus className="mr-2 h-4 w-4" />
              Create New Index
            </Button>
            <Button
              variant={mode === 'existing' ? 'default' : 'outline'}
              onClick={() => setMode('existing')}
              className="flex-1"
              disabled={!indexesData?.collections?.length}
            >
              <Upload className="mr-2 h-4 w-4" />
              Add to Existing
            </Button>
          </div>

          {mode === 'new' ? (
            <div className="space-y-2">
              <Label htmlFor="indexName">Index Name</Label>
              <Input
                id="indexName"
                placeholder="e.g., research_papers"
                value={indexName}
                onChange={(e) => setIndexName(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Use lowercase letters, numbers, and underscores only.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <Label htmlFor="existingIndex">Select Index</Label>
              <Select value={selectedIndex} onValueChange={setSelectedIndex}>
                <SelectTrigger id="existingIndex">
                  <SelectValue placeholder="Select an index" />
                </SelectTrigger>
                <SelectContent>
                  {indexesData?.collections?.map((collection) => (
                    <SelectItem key={collection.name} value={collection.name}>
                      {collection.name} ({collection.num_chunks} chunks)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Documents</CardTitle>
          <CardDescription>
            Drag and drop files or click to browse. Supported: PDF, DOCX, TXT, MD (max 25MB).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            {...getRootProps()}
            className={cn(
              'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
              isDragActive
                ? 'border-primary bg-primary/5'
                : 'border-muted-foreground/25 hover:border-primary/50'
            )}
          >
            <input {...getInputProps()} />
            <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-4 text-sm font-medium">
              {isDragActive ? 'Drop files here...' : 'Drag & drop files here, or click to select'}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {ALLOWED_EXTENSIONS.join(', ')} (max 25MB each)
            </p>
          </div>

          {files.length > 0 && (
            <div className="space-y-2">
              <Label>Selected Files ({files.length})</Label>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {files.map((file, index) => (
                  <div
                    key={`${file.name}-${index}`}
                    className="flex items-center justify-between p-3 bg-muted rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <File className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium">{file.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatFileSize(file.size)}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeFile(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <Button
            onClick={() => uploadMutation.mutate()}
            disabled={!canSubmit || uploadMutation.isPending}
            className="w-full"
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload {files.length} File{files.length !== 1 ? 's' : ''}
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {uploadMutation.isSuccess && (
        <Card className="border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950">
          <CardContent className="flex items-center gap-4 pt-6">
            <CheckCircle className="h-8 w-8 text-green-600" />
            <div>
              <p className="font-medium text-green-800 dark:text-green-200">
                Upload Complete!
              </p>
              <p className="text-sm text-green-600 dark:text-green-400">
                Your documents have been indexed and are ready for querying.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
