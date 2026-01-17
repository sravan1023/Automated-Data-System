'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { workspacesApi } from '@/lib/api-client';
import { DashboardHeader } from '@/components/dashboard/header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { ArrowLeft, Loader2 } from 'lucide-react';
import Link from 'next/link';

const workspaceSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
});

type WorkspaceFormData = z.infer<typeof workspaceSchema>;

export default function NewWorkspacePage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<WorkspaceFormData>({
    resolver: zodResolver(workspaceSchema),
  });

  const createMutation = useMutation({
    mutationFn: (data: WorkspaceFormData) => workspacesApi.create(data),
    onSuccess: (response) => {
      router.push(`/dashboard/workspaces/${response.data.id}`);
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to create workspace');
    },
  });

  const onSubmit = (data: WorkspaceFormData) => {
    setError(null);
    createMutation.mutate(data);
  };

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

        <Card className="mx-auto max-w-lg">
          <CardHeader>
            <CardTitle>Create Workspace</CardTitle>
            <CardDescription>
              Create a new workspace to organize your data sources, templates,
              and generated documents.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit(onSubmit)}>
            <CardContent className="space-y-4">
              {error && (
                <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                  {error}
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="name">Workspace Name</Label>
                <Input
                  id="name"
                  placeholder="My Project"
                  {...register('name')}
                />
                {errors.name && (
                  <p className="text-sm text-destructive">
                    {errors.name.message}
                  </p>
                )}
              </div>
              <Button
                type="submit"
                className="w-full"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Create Workspace
              </Button>
            </CardContent>
          </form>
        </Card>
      </main>
    </div>
  );
}
