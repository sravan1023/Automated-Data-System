'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Link from 'next/link';
import { templatesApi } from '@/lib/api-client';
import { DashboardHeader } from '@/components/dashboard/header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { ArrowLeft, Code, Eye, Loader2, Save } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import Editor from '@monaco-editor/react';

const templateSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  description: z.string().optional(),
});

type TemplateFormData = z.infer<typeof templateSchema>;

const defaultHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{{ title }}</title>
</head>
<body>
  <div class="container">
    <header>
      <h1>{{ title }}</h1>
      <p class="date">Generated: {{ date }}</p>
    </header>
    
    <section class="content">
      <h2>Hello, {{ name }}!</h2>
      <p>This is your personalized document.</p>
      
      <div class="details">
        <p><strong>Email:</strong> {{ email }}</p>
        <p><strong>Company:</strong> {{ company }}</p>
        <p><strong>Amount:</strong> \${{ amount }}</p>
      </div>
    </section>
    
    <footer>
      <p>Thank you for your business!</p>
    </footer>
  </div>
</body>
</html>`;

const defaultCss = `/* Document Styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  color: #333;
  padding: 40px;
  background: white;
}

.container {
  max-width: 800px;
  margin: 0 auto;
}

header {
  border-bottom: 3px solid #2563eb;
  padding-bottom: 20px;
  margin-bottom: 30px;
}

h1 {
  color: #1e40af;
  font-size: 28px;
  margin-bottom: 8px;
}

.date {
  color: #6b7280;
  font-size: 12px;
}

.content {
  margin-bottom: 40px;
}

h2 {
  color: #374151;
  font-size: 20px;
  margin-bottom: 16px;
}

.details {
  background: #f3f4f6;
  padding: 20px;
  border-radius: 8px;
  margin-top: 20px;
}

.details p {
  margin: 8px 0;
}

footer {
  border-top: 1px solid #e5e7eb;
  padding-top: 20px;
  text-align: center;
  color: #6b7280;
  font-size: 12px;
}`;

export default function NewTemplatePage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const workspaceId = params.id as string;

  const [html, setHtml] = useState(defaultHtml);
  const [css, setCss] = useState(defaultCss);
  const [activeTab, setActiveTab] = useState('html');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TemplateFormData>({
    resolver: zodResolver(templateSchema),
    defaultValues: {
      name: '',
      description: '',
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: TemplateFormData) =>
      templatesApi.create({
        workspace_id: workspaceId,
        name: data.name,
        description: data.description,
        content_type: 'html',
        content: html,
        css_content: css,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates', workspaceId] });
      toast({
        title: 'Template created',
        description: 'Your template has been saved successfully.',
      });
      router.push(`/dashboard/workspaces/${workspaceId}`);
    },
    onError: (err: Error) => {
      toast({
        title: 'Failed to create template',
        description: err.message,
        variant: 'destructive',
      });
    },
  });

  const onSubmit = (data: TemplateFormData) => {
    createMutation.mutate(data);
  };

  const previewHtml = `
    <html>
      <head>
        <style>${css}</style>
      </head>
      <body>
        ${html.replace(/<!DOCTYPE.*?>|<html>|<\/html>|<head>.*?<\/head>|<body>|<\/body>/gs, '')}
      </body>
    </html>
  `;

  return (
    <div className="min-h-screen bg-muted/30">
      <DashboardHeader />

      <main className="container py-8">
        <Link
          href={`/dashboard/workspaces/${workspaceId}`}
          className="mb-6 inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Workspace
        </Link>

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">Create Template</h1>
              <p className="mt-1 text-muted-foreground">
                Design your document template with HTML and CSS
              </p>
            </div>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save Template
            </Button>
          </div>

          {/* Template Info */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Template Details</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Template Name</Label>
                <Input
                  id="name"
                  placeholder="Invoice Template"
                  {...register('name')}
                />
                {errors.name && (
                  <p className="text-sm text-destructive">{errors.name.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description (optional)</Label>
                <Input
                  id="description"
                  placeholder="Template for generating invoices"
                  {...register('description')}
                />
              </div>
            </CardContent>
          </Card>

          {/* Editor */}
          <Card>
            <CardHeader>
              <CardTitle>Template Editor</CardTitle>
              <CardDescription>
                Use Jinja2 syntax for variables: {'{{ variable_name }}'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                  <TabsTrigger value="html" className="flex items-center gap-2">
                    <Code className="h-4 w-4" />
                    HTML
                  </TabsTrigger>
                  <TabsTrigger value="css" className="flex items-center gap-2">
                    <Code className="h-4 w-4" />
                    CSS
                  </TabsTrigger>
                  <TabsTrigger value="preview" className="flex items-center gap-2">
                    <Eye className="h-4 w-4" />
                    Preview
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="html" className="mt-4">
                  <div className="h-[500px] overflow-hidden rounded-md border">
                    <Editor
                      height="100%"
                      language="html"
                      theme="vs-dark"
                      value={html}
                      onChange={(value) => setHtml(value || '')}
                      options={{
                        minimap: { enabled: false },
                        fontSize: 14,
                        lineNumbers: 'on',
                        wordWrap: 'on',
                        automaticLayout: true,
                      }}
                    />
                  </div>
                </TabsContent>

                <TabsContent value="css" className="mt-4">
                  <div className="h-[500px] overflow-hidden rounded-md border">
                    <Editor
                      height="100%"
                      language="css"
                      theme="vs-dark"
                      value={css}
                      onChange={(value) => setCss(value || '')}
                      options={{
                        minimap: { enabled: false },
                        fontSize: 14,
                        lineNumbers: 'on',
                        wordWrap: 'on',
                        automaticLayout: true,
                      }}
                    />
                  </div>
                </TabsContent>

                <TabsContent value="preview" className="mt-4">
                  <div className="h-[500px] overflow-auto rounded-md border bg-white">
                    <iframe
                      srcDoc={previewHtml}
                      className="h-full w-full"
                      title="Template Preview"
                    />
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </form>
      </main>
    </div>
  );
}
