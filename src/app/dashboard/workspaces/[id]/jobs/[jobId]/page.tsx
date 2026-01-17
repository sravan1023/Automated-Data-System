'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ArrowLeft, Download, RefreshCw, FileText, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import apiClient from '@/lib/api-client';

interface Output {
  id: string;
  row_index: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  file_path: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

interface Job {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_rows: number;
  processed_rows: number;
  failed_rows: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  template: {
    id: string;
    name: string;
  };
  datasource: {
    id: string;
    name: string;
    original_filename: string;
  };
}

export default function JobDetailPage() {
  const router = useRouter();
  const params = useParams();
  const workspaceId = params.id as string;
  const jobId = params.jobId as string;
  
  const [job, setJob] = useState<Job | null>(null);
  const [outputs, setOutputs] = useState<Output[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchJob();
    fetchOutputs();
    
    // Poll for updates if job is still processing
    const interval = setInterval(() => {
      if (job?.status === 'pending' || job?.status === 'processing') {
        fetchJob();
        fetchOutputs();
      }
    }, 3000);
    
    return () => clearInterval(interval);
  }, [jobId, job?.status]);

  const fetchJob = async () => {
    try {
      const response = await apiClient.get(`/workspaces/${workspaceId}/jobs/${jobId}`);
      setJob(response.data);
    } catch (err) {
      setError('Failed to load job');
    } finally {
      setLoading(false);
    }
  };

  const fetchOutputs = async () => {
    try {
      const response = await apiClient.get(`/workspaces/${workspaceId}/jobs/${jobId}/outputs`);
      setOutputs(response.data);
    } catch (err) {
      console.error('Failed to load outputs', err);
    }
  };

  const handleDownloadAll = async () => {
    setDownloading(true);
    try {
      const response = await apiClient.get(`/workspaces/${workspaceId}/jobs/${jobId}/download`, {
        responseType: 'blob',
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `job-${jobId}-outputs.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed', err);
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadSingle = async (output: Output) => {
    try {
      const response = await apiClient.get(
        `/workspaces/${workspaceId}/jobs/${jobId}/outputs/${output.id}/download`,
        { responseType: 'blob' }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `output-row-${output.row_index + 1}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed', err);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-500"><CheckCircle className="h-3 w-3 mr-1" />Completed</Badge>;
      case 'failed':
        return <Badge variant="destructive"><XCircle className="h-3 w-3 mr-1" />Failed</Badge>;
      case 'processing':
        return <Badge className="bg-blue-500"><Loader2 className="h-3 w-3 mr-1 animate-spin" />Processing</Badge>;
      default:
        return <Badge variant="secondary"><Clock className="h-3 w-3 mr-1" />Pending</Badge>;
    }
  };

  const getProgressPercentage = () => {
    if (!job || job.total_rows === 0) return 0;
    return Math.round((job.processed_rows / job.total_rows) * 100);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="p-8">
        <div className="text-center text-muted-foreground">Job not found</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/dashboard/workspaces/${workspaceId}`)}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Workspace
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchJob}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          {job.status === 'completed' && job.processed_rows > 0 && (
            <Button onClick={handleDownloadAll} disabled={downloading}>
              <Download className="h-4 w-4 mr-2" />
              {downloading ? 'Downloading...' : 'Download All'}
            </Button>
          )}
        </div>
      </div>

      {/* Job Info Card */}
      <div className="bg-card rounded-lg border p-6 mb-8">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold mb-2">Generation Job</h1>
            <p className="text-sm text-muted-foreground">ID: {job.id}</p>
          </div>
          {getStatusBadge(job.status)}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Template</p>
            <p className="font-medium">{job.template.name}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">Data Source</p>
            <p className="font-medium">{job.datasource.name}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">Created</p>
            <p className="font-medium">{new Date(job.created_at).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">Completed</p>
            <p className="font-medium">
              {job.completed_at ? new Date(job.completed_at).toLocaleString() : '-'}
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-sm mb-2">
            <span>Progress</span>
            <span>{job.processed_rows} / {job.total_rows} rows ({getProgressPercentage()}%)</span>
          </div>
          <div className="w-full bg-muted rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all duration-300 ${
                job.status === 'failed' ? 'bg-red-500' : 'bg-primary'
              }`}
              style={{ width: `${getProgressPercentage()}%` }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="flex gap-6 text-sm">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-green-500" />
            <span>{job.processed_rows - job.failed_rows} Successful</span>
          </div>
          <div className="flex items-center gap-2">
            <XCircle className="h-4 w-4 text-red-500" />
            <span>{job.failed_rows} Failed</span>
          </div>
        </div>

        {job.error_message && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            <strong>Error:</strong> {job.error_message}
          </div>
        )}
      </div>

      {/* Outputs Table */}
      <div className="bg-card rounded-lg border">
        <div className="p-4 border-b">
          <h2 className="font-semibold">Generated Outputs</h2>
        </div>
        
        {outputs.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            {job.status === 'pending' || job.status === 'processing' 
              ? 'Waiting for outputs...' 
              : 'No outputs generated'}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Row</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Completed</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {outputs.map((output) => (
                <TableRow key={output.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      Row {output.row_index + 1}
                    </div>
                  </TableCell>
                  <TableCell>{getStatusBadge(output.status)}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(output.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {output.completed_at ? new Date(output.completed_at).toLocaleString() : '-'}
                  </TableCell>
                  <TableCell className="text-right">
                    {output.status === 'completed' && output.file_path && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownloadSingle(output)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    )}
                    {output.status === 'failed' && output.error_message && (
                      <span className="text-xs text-red-500" title={output.error_message}>
                        Error
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  );
}
