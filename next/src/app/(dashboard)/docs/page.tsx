'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Copy, Check, ExternalLink, Code, Book, Key, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// API Key examples (for external/script usage)
const pythonApiKeyExample = `import requests

# Configuration
API_URL = "${API_URL}"
API_KEY = "your-api-key-here"  # Get from Account > API Keys

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Query your knowledge base
response = requests.post(
    f"{API_URL}/api/v1/query/",
    headers=headers,
    json={
        "query": "What are the key features?",
        "collection": "my_documents"  # optional
    }
)

result = response.json()
context = result["context"]  # Use this with your LLM

# Example: Use with OpenAI
from openai import OpenAI
client = OpenAI()

completion = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": f"Answer based on this context:\\n\\n{context}"},
        {"role": "user", "content": "What are the key features?"}
    ]
)

print(completion.choices[0].message.content)`;

const curlApiKeyExample = `# Query your knowledge base
curl -X POST "${API_URL}/api/v1/query/" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "What are the key features?",
    "collection": "my_documents"
  }'

# Upload files to create an index
curl -X POST "${API_URL}/api/v1/create-index/" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -F "collection=my_documents" \\
  -F "files=@document1.pdf" \\
  -F "files=@document2.txt"

# List all indexes
curl -X GET "${API_URL}/api/v1/list-indexes/" \\
  -H "X-API-Key: YOUR_API_KEY"

# Delete an index
curl -X DELETE "${API_URL}/api/v1/delete-index/my_documents" \\
  -H "X-API-Key: YOUR_API_KEY"`;

const jsApiKeyExample = `// API Client for Knowledge Manager
const API_URL = "${API_URL}";
const API_KEY = "your-api-key-here"; // Get from Account > API Keys

async function queryKnowledge(query, collection) {
  const response = await fetch(\`\${API_URL}/api/v1/query/\`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      collection, // optional
    }),
  });

  if (!response.ok) {
    throw new Error(\`Query failed: \${response.statusText}\`);
  }

  const result = await response.json();
  return result.context; // Compiled context from matching chunks
}

// List all indexes
async function listIndexes() {
  const response = await fetch(\`\${API_URL}/api/v1/list-indexes/\`, {
    headers: { "X-API-Key": API_KEY },
  });
  return response.json();
}

// Usage
const context = await queryKnowledge("What is the main topic?");
console.log(context);`;

export default function DocsPage() {
  const [copiedTab, setCopiedTab] = useState<string | null>(null);

  const copyToClipboard = async (text: string, tab: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedTab(tab);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopiedTab(null), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Documentation</h1>
        <p className="text-muted-foreground mt-2">
          Learn how to use the Knowledge Manager API.
        </p>
      </div>

      {/* Authentication Methods */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5" />
            Authentication
          </CardTitle>
          <CardDescription>
            The API supports two authentication methods depending on your use case.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid md:grid-cols-2 gap-4">
            <div className="p-4 border rounded-lg space-y-2">
              <div className="flex items-center gap-2">
                <Key className="h-5 w-5 text-blue-600" />
                <h4 className="font-semibold">API Key (Recommended for Scripts)</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                Use API keys for external applications, scripts, and integrations.
                API keys are long-lived and ideal for server-to-server communication.
              </p>
              <code className="block text-xs bg-muted p-2 rounded mt-2">
                X-API-Key: your-api-key-here
              </code>
              <Button variant="outline" size="sm" asChild className="mt-2">
                <Link href="/account">
                  <Key className="mr-2 h-4 w-4" />
                  Manage API Keys
                </Link>
              </Button>
            </div>
            <div className="p-4 border rounded-lg space-y-2">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-green-600" />
                <h4 className="font-semibold">Bearer Token (Browser/Frontend)</h4>
              </div>
              <p className="text-sm text-muted-foreground">
                Used automatically by this web application via Cognito authentication.
                Best for browser-based applications with user sessions.
              </p>
              <code className="block text-xs bg-muted p-2 rounded mt-2">
                Authorization: Bearer &lt;cognito-jwt&gt;
              </code>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* API Reference Links */}
      <Card>
        <CardHeader>
          <CardTitle>API Reference</CardTitle>
          <CardDescription>
            Interactive API documentation with request/response examples.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex gap-4">
          <Button asChild>
            <a href={`${API_URL}/docs`} target="_blank" rel="noopener noreferrer">
              <Book className="mr-2 h-4 w-4" />
              Swagger UI
              <ExternalLink className="ml-2 h-4 w-4" />
            </a>
          </Button>
          <Button variant="outline" asChild>
            <a href={`${API_URL}/redoc`} target="_blank" rel="noopener noreferrer">
              <Code className="mr-2 h-4 w-4" />
              ReDoc
              <ExternalLink className="ml-2 h-4 w-4" />
            </a>
          </Button>
        </CardContent>
      </Card>

      {/* Quick Start */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Start with API Keys</CardTitle>
          <CardDescription>
            Get started with the Knowledge Manager API in your preferred language.
            These examples use API key authentication for external access.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="python" className="space-y-4">
            <TabsList>
              <TabsTrigger value="python">Python</TabsTrigger>
              <TabsTrigger value="curl">cURL</TabsTrigger>
              <TabsTrigger value="javascript">JavaScript</TabsTrigger>
            </TabsList>

            <TabsContent value="python">
              <div className="relative">
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-2 right-2 z-10"
                  onClick={() => copyToClipboard(pythonApiKeyExample, 'python')}
                >
                  {copiedTab === 'python' ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
                <ScrollArea className="h-[400px] rounded-lg border bg-muted p-4">
                  <pre className="text-sm font-mono">{pythonApiKeyExample}</pre>
                </ScrollArea>
              </div>
            </TabsContent>

            <TabsContent value="curl">
              <div className="relative">
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-2 right-2 z-10"
                  onClick={() => copyToClipboard(curlApiKeyExample, 'curl')}
                >
                  {copiedTab === 'curl' ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
                <ScrollArea className="h-[400px] rounded-lg border bg-muted p-4">
                  <pre className="text-sm font-mono">{curlApiKeyExample}</pre>
                </ScrollArea>
              </div>
            </TabsContent>

            <TabsContent value="javascript">
              <div className="relative">
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-2 right-2 z-10"
                  onClick={() => copyToClipboard(jsApiKeyExample, 'javascript')}
                >
                  {copiedTab === 'javascript' ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
                <ScrollArea className="h-[400px] rounded-lg border bg-muted p-4">
                  <pre className="text-sm font-mono">{jsApiKeyExample}</pre>
                </ScrollArea>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Endpoints Overview */}
      <Card>
        <CardHeader>
          <CardTitle>API Endpoints</CardTitle>
          <CardDescription>Overview of available endpoints.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <h4 className="font-medium">Index Management</h4>
              <div className="grid gap-2">
                <EndpointRow method="POST" path="/api/v1/create-index/" description="Create new index with files" />
                <EndpointRow method="POST" path="/api/v1/update-index/" description="Add files to existing index" />
                <EndpointRow method="GET" path="/api/v1/list-indexes/" description="List all indexes" />
                <EndpointRow method="DELETE" path="/api/v1/delete-index/{name}" description="Delete an index" />
                <EndpointRow method="POST" path="/api/v1/query/" description="Query indexes" />
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium">Corpus Management</h4>
              <div className="grid gap-2">
                <EndpointRow method="GET" path="/api/v1/corpus/" description="List all corpuses" />
                <EndpointRow method="POST" path="/api/v1/corpus/" description="Create new corpus" />
                <EndpointRow method="PATCH" path="/api/v1/corpus/{id}" description="Update corpus" />
                <EndpointRow method="DELETE" path="/api/v1/corpus/{id}" description="Delete corpus" />
                <EndpointRow method="POST" path="/api/v1/corpus/{id}/subscribe" description="Subscribe to corpus" />
                <EndpointRow method="POST" path="/api/v1/corpus/{id}/query" description="Query specific corpus" />
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="font-medium">API Key Management</h4>
              <div className="grid gap-2">
                <EndpointRow method="GET" path="/api/v1/user/api-keys" description="List your API keys" />
                <EndpointRow method="POST" path="/api/v1/user/api-keys" description="Create new API key" />
                <EndpointRow method="DELETE" path="/api/v1/user/api-keys/{id}" description="Revoke API key" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function EndpointRow({
  method,
  path,
  description,
}: {
  method: string;
  path: string;
  description: string;
}) {
  const methodColors: Record<string, string> = {
    GET: 'bg-green-500/10 text-green-700 dark:text-green-400',
    POST: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    PATCH: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400',
    DELETE: 'bg-red-500/10 text-red-700 dark:text-red-400',
  };

  return (
    <div className="flex items-center gap-4 p-2 rounded-lg bg-muted/50">
      <Badge className={methodColors[method]} variant="outline">
        {method}
      </Badge>
      <code className="text-sm flex-1">{path}</code>
      <span className="text-sm text-muted-foreground">{description}</span>
    </div>
  );
}
