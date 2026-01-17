'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { jobsApi, type Job } from '@/lib/api-client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Download,
  RefreshCw,
  StopCircle,
} from 'lucide-react';
import { formatDate } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface JobStatusProps {
  jobId: string;
  onComplete?: () => void;
}

const statusConfig: Record<
  Job['status'],
  { icon: React.ReactNode; label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  pending: {
    icon: <Clock className="h-4 w-4" />,
    label: 'Pending',
    variant: 'secondary',
  },
  queued: {
    icon: <Clock className="h-4 w-4" />,
    label: 'Queued',
    variant: 'secondary',
  },
  processing: {
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
    label: 'Processing',
    variant: 'default',
  },
  completed: {
    icon: <CheckCircle className="h-4 w-4" />,
    label: 'Completed',
    variant: 'default',
  },
  failed: {
    icon: <XCircle className="h-4 w-4" />,
    label: 'Failed',
    variant: 'destructive',
  },
  cancelled: {
    icon: <StopCircle className="h-4 w-4" />,
    label: 'Cancelled',
    variant: 'outline',
  },
};

export function JobStatus({ jobId, onComplete }: JobStatusProps) {
  const [hasCompleted, setHasCompleted] = useState(false);

  const { data: job, isLoading, refetch } = useQuery({
    queryKey: ['job', jobId],
    queryFn: async () => {
      const response = await jobsApi.get(jobId);
      return response.data;
    },
    refetchInterval: (data) => {
      // Poll every 2 seconds while processing
      if (data?.status === 'processing' || data?.status === 'queued') {
        return 2000;
      }
      return false;
    },
  });

  useEffect(() => {
    if (job?.status === 'completed' && !hasCompleted) {
      setHasCompleted(true);
      onComplete?.();
    }
  }, [job?.status, hasCompleted, onComplete]);

  if (isLoading || !job) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  const progress =
    job.total_items > 0
      ? Math.round((job.completed_items / job.total_items) * 100)
      : 0;

  const status = statusConfig[job.status];

  const handleCancel = async () => {
    try {
      await jobsApi.cancel(jobId);
      refetch();
    } catch (error) {
      console.error('Failed to cancel job:', error);
    }
  };

  const handleRetry = async () => {
    try {
      await jobsApi.retry(jobId);
      refetch();
    } catch (error) {
      console.error('Failed to retry job:', error);
    }
  };

  const handleDownload = async () => {
    try {
      const response = await jobsApi.downloadBundle(jobId);
      const blob = new Blob([response.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `job-${jobId}-bundle.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download bundle:', error);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Job Status</CardTitle>
          <Badge
            variant={status.variant}
            className={cn(
              'flex items-center gap-1',
              job.status === 'completed' && 'bg-green-500 hover:bg-green-600'
            )}
          >
            {status.icon}
            {status.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Progress */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Progress</span>
            <span>
              {job.completed_items} / {job.total_items} documents
            </span>
          </div>
          <Progress value={progress} className="h-2" />
          <p className="text-right text-sm text-muted-foreground">{progress}%</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-green-500">
              {job.completed_items - job.failed_items}
            </p>
            <p className="text-sm text-muted-foreground">Successful</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-red-500">{job.failed_items}</p>
            <p className="text-sm text-muted-foreground">Failed</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-muted-foreground">
              {job.total_items - job.completed_items}
            </p>
            <p className="text-sm text-muted-foreground">Remaining</p>
          </div>
        </div>

        {/* Timestamps */}
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Created:</span>
            <span>{formatDate(job.created_at)}</span>
          </div>
          {job.started_at && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Started:</span>
              <span>{formatDate(job.started_at)}</span>
            </div>
          )}
          {job.completed_at && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Completed:</span>
              <span>{formatDate(job.completed_at)}</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {job.status === 'processing' && (
            <Button variant="destructive" onClick={handleCancel}>
              <StopCircle className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}
          {job.status === 'failed' && (
            <Button variant="outline" onClick={handleRetry}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Retry Failed
            </Button>
          )}
          {job.status === 'completed' && (
            <Button onClick={handleDownload}>
              <Download className="mr-2 h-4 w-4" />
              Download All
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
