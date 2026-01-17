'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  workspacesApi,
  datasourcesApi,
  templatesApi,
  jobsApi,
  type DataSource,
  type Template,
  type Job,
} from '@/lib/api-client';
import { DashboardHeader } from '@/components/dashboard/header';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { FileUpload } from '@/components/upload/file-upload';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  ArrowLeft,
  Database,
  FileText,
  Play,
  Plus,
  Loader2,
  Download,
  Trash2,
  Eye,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  StopCircle,
} from 'lucide-react';
import { formatDate, formatFileSize } from '@/lib/utils';
import { useToast } from '@/hooks/use-toast';

export default function WorkspaceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const workspaceId = params.id as string;
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [createJobDialogOpen, setCreateJobDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [selectedDatasource, setSelectedDatasource] = useState<string | null>(null);
  const [generationMode, setGenerationMode] = useState<'per_row' | 'per_datasource'>('per_row');

  // Fetch workspace
  const { data: workspace, isLoading: workspaceLoading } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: async () => {
      const response = await workspacesApi.get(workspaceId);
      return response.data;
    },
  });

  // Fetch datasources
  const { data: datasources, isLoading: datasourcesLoading } = useQuery({
    queryKey: ['datasources', workspaceId],
    queryFn: async () => {
      const response = await datasourcesApi.list(workspaceId);
      return response.data;
    },
  });

  // Fetch templates
  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['templates', workspaceId],
    queryFn: async () => {
      const response = await templatesApi.list(workspaceId);
      return response.data;
    },
  });

  // Fetch jobs
  const { data: jobs, isLoading: jobsLoading, refetch: refetchJobs } = useQuery({
    queryKey: ['jobs', workspaceId],
    queryFn: async () => {
      const response = await jobsApi.list(workspaceId);
      return response.data;
    },
    refetchInterval: 5000, // Poll every 5 seconds
  });

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const name = file.name.replace(/\.[^/.]+$/, ""); // Remove extension for display name
      return datasourcesApi.upload(workspaceId, name, file);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasources', workspaceId] });
      setUploadDialogOpen(false);
      toast({
        title: 'Upload successful',
        description: 'Your data source is being processed.',
      });
    },
    onError: (err: Error) => {
      toast({
        title: 'Upload failed',
        description: err.message,
        variant: 'destructive',
      });
    },
  });

  // Delete datasource mutation
  const deleteDatasourceMutation = useMutation({
    mutationFn: (id: string) => datasourcesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasources', workspaceId] });
      toast({ title: 'Data source deleted' });
    },
  });

  // Delete template mutation
  const deleteTemplateMutation = useMutation({
    mutationFn: (id: string) => templatesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates', workspaceId] });
      toast({ title: 'Template deleted' });
    },
  });

  // Delete workspace mutation
  const deleteWorkspaceMutation = useMutation({
    mutationFn: () => workspacesApi.delete(workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      toast({ title: 'Workspace deleted' });
      router.push('/dashboard');
    },
    onError: (err: Error) => {
      toast({
        title: 'Failed to delete workspace',
        description: err.message,
        variant: 'destructive',
      });
    },
  });

  // Create job mutation
  const createJobMutation = useMutation({
    mutationFn: (data: { template_id: string; datasource_id: string; generation_mode: 'per_row' | 'per_datasource' }) =>
      jobsApi.create({
        workspace_id: workspaceId,
        template_id: data.template_id,
        datasource_id: data.datasource_id,
        generation_mode: data.generation_mode,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs', workspaceId] });
      setCreateJobDialogOpen(false);
      setSelectedTemplate(null);
      setSelectedDatasource(null);
      setGenerationMode('per_row');
      toast({
        title: 'Job started',
        description: 'Document generation has begun.',
      });
    },
    onError: (err: Error) => {
      toast({
        title: 'Failed to start job',
        description: err.message,
        variant: 'destructive',
      });
    },
  });

  // Cancel job mutation
  const cancelJobMutation = useMutation({
    mutationFn: (jobId: string) => jobsApi.cancel(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs', workspaceId] });
      toast({
        title: 'Job cancelled',
        description: 'The generation job has been stopped.',
      });
    },
    onError: (err: Error) => {
      toast({
        title: 'Failed to cancel job',
        description: err.message,
        variant: 'destructive',
      });
    },
  });

  // Download bundle or single document
  const downloadBundle = async (jobId: string, job?: Job) => {
    try {
      const response = await jobsApi.downloadBundle(jobId);
      
      // Get content type from response headers
      const contentType = response.headers['content-type'] || 'application/octet-stream';
      const isPdf = contentType.includes('pdf');
      
      // Determine file extension based on content type or job mode
      const isSinglePdf = job?.generation_mode === 'per_datasource' || isPdf;
      const extension = isSinglePdf ? 'pdf' : 'zip';
      const mimeType = isSinglePdf ? 'application/pdf' : 'application/zip';
      
      const blob = new Blob([response.data], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `documents-${jobId.slice(0, 8)}.${extension}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      toast({
        title: 'Download failed',
        description: error.response?.data?.detail || 'Failed to download documents.',
        variant: 'destructive',
      });
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: React.ReactNode }> = {
      pending: { variant: 'secondary', icon: <Clock className="h-3 w-3" /> },
      processing: { variant: 'default', icon: <Loader2 className="h-3 w-3 animate-spin" /> },
      ready: { variant: 'default', icon: <CheckCircle className="h-3 w-3" /> },
      completed: { variant: 'default', icon: <CheckCircle className="h-3 w-3" /> },
      error: { variant: 'destructive', icon: <XCircle className="h-3 w-3" /> },
      failed: { variant: 'destructive', icon: <XCircle className="h-3 w-3" /> },
    };
    const config = statusConfig[status] || statusConfig.pending;
    return (
      <Badge variant={config.variant} className="flex items-center gap-1">
        {config.icon}
        {status}
      </Badge>
    );
  };

  if (workspaceLoading) {
    return (
      <div className="min-h-screen bg-muted/30">
        <DashboardHeader />
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <DashboardHeader />

      <main className="container py-8">
        <Link
          href="/dashboard"
          className="mb-6 inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Dashboard
        </Link>

        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">{workspace?.name}</h1>
            <p className="mt-1 text-muted-foreground">
              Created {workspace?.created_at && formatDate(workspace.created_at)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="destructive" size="icon">
                  <Trash2 className="h-4 w-4" />
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Delete Workspace</DialogTitle>
                  <DialogDescription>
                    Are you sure you want to delete &quot;{workspace?.name}&quot;? This action cannot be undone.
                    All data sources, templates, and jobs in this workspace will be permanently deleted.
                  </DialogDescription>
                </DialogHeader>
                <div className="flex justify-end gap-2 mt-4">
                  <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => deleteWorkspaceMutation.mutate()}
                    disabled={deleteWorkspaceMutation.isPending}
                  >
                    {deleteWorkspaceMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="mr-2 h-4 w-4" />
                    )}
                    Delete
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
            <Dialog open={createJobDialogOpen} onOpenChange={setCreateJobDialogOpen}>
              <DialogTrigger asChild>
                <Button disabled={!templates?.length || !datasources?.length}>
                  <Play className="mr-2 h-4 w-4" />
                  Run Generation
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Start Generation Job</DialogTitle>
                  <DialogDescription>
                    Select a template and data source to generate documents.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Template</label>
                    <select
                      className="w-full rounded-md border p-2"
                      value={selectedTemplate || ''}
                      onChange={(e) => setSelectedTemplate(e.target.value)}
                    >
                      <option value="">Select a template</option>
                      {templates?.map((t: Template) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Data Source</label>
                    <select
                      className="w-full rounded-md border p-2"
                      value={selectedDatasource || ''}
                      onChange={(e) => setSelectedDatasource(e.target.value)}
                    >
                      <option value="">Select a data source</option>
                      {datasources
                        ?.filter((d: DataSource) => d.status === 'ready')
                        .map((d: DataSource) => (
                          <option key={d.id} value={d.id}>
                            {d.name} ({d.row_count} rows)
                          </option>
                        ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Generation Mode</label>
                    <div className="flex rounded-md border overflow-hidden">
                      <button
                        type="button"
                        className={`flex-1 py-2 px-3 text-sm font-medium transition-colors ${
                          generationMode === 'per_row'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-background hover:bg-muted'
                        }`}
                        onClick={() => setGenerationMode('per_row')}
                      >
                        <div className="flex flex-col items-center gap-1">
                          <span>Per Row</span>
                          <span className="text-xs opacity-70">Multiple PDFs</span>
                        </div>
                      </button>
                      <button
                        type="button"
                        className={`flex-1 py-2 px-3 text-sm font-medium transition-colors ${
                          generationMode === 'per_datasource'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-background hover:bg-muted'
                        }`}
                        onClick={() => setGenerationMode('per_datasource')}
                      >
                        <div className="flex flex-col items-center gap-1">
                          <span>Per Data Source</span>
                          <span className="text-xs opacity-70">Single PDF, multiple pages</span>
                        </div>
                      </button>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {generationMode === 'per_row'
                        ? 'Creates one PDF file for each row in your data source.'
                        : 'Creates a single PDF file with one page per row.'}
                    </p>
                  </div>
                  <Button
                    className="w-full"
                    disabled={!selectedTemplate || !selectedDatasource || createJobMutation.isPending}
                    onClick={() => {
                      if (selectedTemplate && selectedDatasource) {
                        createJobMutation.mutate({
                          template_id: selectedTemplate,
                          datasource_id: selectedDatasource,
                          generation_mode: generationMode,
                        });
                      }
                    }}
                  >
                    {createJobMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-4 w-4" />
                    )}
                    Start Generation
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        <Tabs defaultValue="datasources" className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 gap-4 bg-transparent h-auto p-0">
            <TabsTrigger 
              value="datasources" 
              className="flex items-center justify-between rounded-lg border bg-card p-3 shadow-sm data-[state=active]:border-primary data-[state=active]:bg-primary/5 data-[state=active]:shadow-md transition-all"
            >
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                <span className="text-sm font-semibold">Data Sources</span>
              </div>
              <span className="text-xl font-bold">{datasources?.length || 0}</span>
            </TabsTrigger>
            <TabsTrigger 
              value="templates" 
              className="flex items-center justify-between rounded-lg border bg-card p-3 shadow-sm data-[state=active]:border-primary data-[state=active]:bg-primary/5 data-[state=active]:shadow-md transition-all"
            >
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                <span className="text-sm font-semibold">Templates</span>
              </div>
              <span className="text-xl font-bold">{templates?.length || 0}</span>
            </TabsTrigger>
            <TabsTrigger 
              value="jobs" 
              className="flex items-center justify-between rounded-lg border bg-card p-3 shadow-sm data-[state=active]:border-primary data-[state=active]:bg-primary/5 data-[state=active]:shadow-md transition-all"
            >
              <div className="flex items-center gap-2">
                <Play className="h-5 w-5" />
                <span className="text-sm font-semibold">Jobs</span>
              </div>
              <span className="text-xl font-bold">{jobs?.length || 0}</span>
            </TabsTrigger>
          </TabsList>

          {/* Data Sources Tab */}
          <TabsContent value="datasources">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Data Sources</h2>
              <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Upload Data
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Upload Data Source</DialogTitle>
                    <DialogDescription>
                      Upload a CSV or Excel file to use as your data source.
                    </DialogDescription>
                  </DialogHeader>
                  <FileUpload
                    onUpload={async (file) => {
                      await uploadMutation.mutateAsync(file);
                    }}
                  />
                </DialogContent>
              </Dialog>
            </div>

            {datasourcesLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : datasources?.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Database className="h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-semibold">No data sources</h3>
                  <p className="mt-2 text-center text-muted-foreground">
                    Upload your first CSV or Excel file to get started.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {datasources?.map((ds: DataSource) => (
                  <Card key={ds.id}>
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-base">{ds.name}</CardTitle>
                        {getStatusBadge(ds.status)}
                      </div>
                      <CardDescription>
                        {ds.file_type?.toUpperCase()} • {formatDate(ds.created_at)}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2 text-sm">
                        {ds.row_count && (
                          <p className="text-muted-foreground">
                            {ds.row_count.toLocaleString()} rows
                          </p>
                        )}
                      </div>
                      <div className="mt-4 flex gap-2">
                        <Link href={`/dashboard/workspaces/${workspaceId}/datasources/${ds.id}`}>
                          <Button variant="outline" size="sm">
                            <Eye className="mr-2 h-4 w-4" />
                            View
                          </Button>
                        </Link>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => deleteDatasourceMutation.mutate(ds.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Templates Tab */}
          <TabsContent value="templates">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Templates</h2>
              <Link href={`/dashboard/workspaces/${workspaceId}/templates/new`}>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Template
                </Button>
              </Link>
            </div>

            {templatesLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : templates?.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <FileText className="h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-semibold">No templates</h3>
                  <p className="mt-2 text-center text-muted-foreground">
                    Create your first template to generate documents.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {templates?.map((template: Template) => (
                  <Card key={template.id}>
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-base">{template.name}</CardTitle>
                        <Badge variant="secondary">{template.output_format?.toUpperCase() || 'PDF'}</Badge>
                      </div>
                      <CardDescription>
                        {template.description || 'No description'}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-muted-foreground">
                        Created {formatDate(template.created_at)}
                      </p>
                      <div className="mt-4 flex gap-2">
                        <Link href={`/dashboard/workspaces/${workspaceId}/templates/${template.id}`}>
                          <Button variant="outline" size="sm">
                            <Eye className="mr-2 h-4 w-4" />
                            Edit
                          </Button>
                        </Link>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => deleteTemplateMutation.mutate(template.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* Jobs Tab */}
          <TabsContent value="jobs">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Generation Jobs</h2>
              <Button variant="outline" onClick={() => refetchJobs()}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </div>

            {jobsLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : jobs?.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Play className="h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-semibold">No jobs yet</h3>
                  <p className="mt-2 text-center text-muted-foreground">
                    Run a generation job to create documents.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {jobs?.map((job: Job) => {
                  const progress = job.total_items > 0
                    ? Math.round((job.completed_items / job.total_items) * 100)
                    : 0;
                  return (
                    <Card key={job.id}>
                      <CardContent className="py-4">
                        <div className="flex items-center justify-between">
                          <div className="space-y-1">
                            <div className="flex items-center gap-3">
                              <p className="font-medium">Job {job.id.slice(0, 8)}</p>
                              {getStatusBadge(job.status)}
                              <Badge variant="outline" className="text-xs">
                                {job.generation_mode === 'per_datasource' ? 'Single PDF' : 'Multiple PDFs'}
                              </Badge>
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {formatDate(job.created_at)}
                            </p>
                          </div>
                          <div className="flex items-center gap-4">
                            <div className="text-right">
                              <p className="text-sm font-medium">
                                {job.generation_mode === 'per_datasource' 
                                  ? (job.status === 'completed' ? '1 document' : 'Processing...')
                                  : `${job.completed_items} / ${job.total_items}`
                                }
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {job.failed_items > 0 && `${job.failed_items} failed`}
                              </p>
                            </div>
                            {(job.status === 'processing' || job.status === 'queued' || job.status === 'pending') && (
                              <Button 
                                size="sm" 
                                variant="destructive"
                                onClick={() => cancelJobMutation.mutate(job.id)}
                                disabled={cancelJobMutation.isPending}
                              >
                                {cancelJobMutation.isPending ? (
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : (
                                  <StopCircle className="mr-2 h-4 w-4" />
                                )}
                                Stop
                              </Button>
                            )}
                            {job.status === 'completed' && (
                              <Button size="sm" onClick={() => downloadBundle(job.id, job)}>
                                <Download className="mr-2 h-4 w-4" />
                                Download
                              </Button>
                            )}
                          </div>
                        </div>
                        {(job.status === 'processing' || job.status === 'queued') && (
                          <div className="mt-4">
                            <Progress value={progress} className="h-2" />
                            <p className="mt-1 text-right text-xs text-muted-foreground">
                              {progress}%
                            </p>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
