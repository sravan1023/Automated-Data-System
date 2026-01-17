'use client';

import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { datasourcesApi } from '@/lib/api-client';
import { DashboardHeader } from '@/components/dashboard/header';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export default function DataSourceDetailPage() {
  const params = useParams();
  const workspaceId = params.id as string;
  const datasourceId = params.datasourceId as string;

  // Fetch datasource
  const { data: datasource, isLoading: datasourceLoading } = useQuery({
    queryKey: ['datasource', datasourceId],
    queryFn: async () => {
      const response = await datasourcesApi.get(datasourceId);
      return response.data;
    },
  });

  // Fetch rows
  const { data: rowsData, isLoading: rowsLoading } = useQuery({
    queryKey: ['datasource-rows', datasourceId],
    queryFn: async () => {
      const response = await datasourcesApi.getRows(datasourceId, 0, 50);
      return response.data;
    },
    enabled: datasource?.status === 'ready',
  });

  if (datasourceLoading) {
    return (
      <div className="min-h-screen bg-muted/30">
        <DashboardHeader />
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  const schema = rowsData?.schema || datasource?.column_schema;
  const columns = schema?.columns?.map((c: { name: string }) => c.name) || (schema ? Object.keys(schema) : []);
  const rows = rowsData?.preview_rows || [];

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

        <div className="mb-8">
          <div className="flex items-center gap-4">
            <h1 className="text-3xl font-bold">{datasource?.name}</h1>
            <Badge variant={datasource?.status === 'ready' ? 'default' : 'secondary'}>
              {datasource?.status}
            </Badge>
          </div>
          <p className="mt-2 text-muted-foreground">
            {datasource?.file_type?.toUpperCase()} • {datasource?.row_count?.toLocaleString()} rows •
            Created {datasource?.created_at && formatDate(datasource.created_at)}
          </p>
        </div>

        {/* Column Schema */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Column Schema</CardTitle>
            <CardDescription>
              Use these column names as variables in your templates: {'{{ column_name }}'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {columns.map((col) => (
                <Badge key={col} variant="outline" className="font-mono">
                  {col}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Data Preview */}
        <Card>
          <CardHeader>
            <CardTitle>Data Preview</CardTitle>
            <CardDescription>
              Showing first 50 rows of your data
            </CardDescription>
          </CardHeader>
          <CardContent>
            {rowsLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : rows.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                No data available
              </p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-16">#</TableHead>
                      {columns.map((col) => (
                        <TableHead key={col}>{col}</TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((row: Record<string, unknown>, idx: number) => (
                      <TableRow key={idx}>
                        <TableCell className="font-mono text-muted-foreground">
                          {idx + 1}
                        </TableCell>
                        {columns.map((col) => (
                          <TableCell key={col} className="max-w-xs truncate">
                            {String(row[col] ?? '')}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
