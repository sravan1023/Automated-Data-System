'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { workspacesApi, api, type Workspace } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { DashboardHeader } from '@/components/dashboard/header';
import {
  FileText,
  FolderOpen,
  Plus,
  Loader2,
  ArrowRight,
} from 'lucide-react';
import { formatDate } from '@/lib/utils';

interface DashboardStats {
  workspaces: number;
  templates: number;
  documents_generated: number;
}

export default function DashboardPage() {
  const { user, isGuest } = useAuth();

  const { data: workspaces, isLoading } = useQuery({
    queryKey: ['workspaces', user?.id],
    queryFn: async () => {
      const response = await workspacesApi.list();
      return response.data;
    },
    enabled: !!user,
  });

  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats', user?.id],
    queryFn: async () => {
      const response = await api.get<DashboardStats>('/users/me/stats');
      return response.data;
    },
    enabled: !!user,
  });

  return (
    <div className="min-h-screen bg-muted/30">
      <DashboardHeader />
      
      <main className="container py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">
            Welcome{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
          </h1>
          <p className="mt-2 text-muted-foreground">
            Create templates. Generate documents
          </p>
        </div>

        {/* Quick Stats */}
        <div className="mb-8 grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Workspaces</CardTitle>
              <FolderOpen className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.workspaces ?? 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Templates</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.templates ?? 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">
                Documents Generated
              </CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.documents_generated ?? 0}</div>
            </CardContent>
          </Card>
        </div>

        {/* Workspaces */}
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Your Workspaces</h2>
          <Link href="/dashboard/workspaces/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Workspace
            </Button>
          </Link>
        </div>

        {isLoading ? (
          <div className="mt-8 flex justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : workspaces?.length === 0 ? (
          <Card className="mt-8">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FolderOpen className="h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-semibold">No workspaces yet</h3>
              <p className="mt-2 text-center text-muted-foreground">
                Create your first workspace to start generating documents
              </p>
              <Link href="/dashboard/workspaces/new">
                <Button className="mt-4">
                  <Plus className="mr-2 h-4 w-4" />
                  Create Workspace
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {workspaces?.map((workspace: Workspace) => (
              <Link
                key={workspace.id}
                href={`/dashboard/workspaces/${workspace.id}`}
              >
                <Card className="cursor-pointer transition-shadow hover:shadow-md">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>{workspace.name}</span>
                      <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    </CardTitle>
                    <CardDescription>
                      Created {formatDate(workspace.created_at)}
                    </CardDescription>
                  </CardHeader>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
