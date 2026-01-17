'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ArrowLeft, Save, Eye, Code, Palette, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import apiClient from '@/lib/api-client';
import dynamic from 'next/dynamic';

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false });

interface TemplateVersion {
  id: string;
  content: string;
  css_content: string | null;
}

interface Template {
  id: string;
  name: string;
  description: string | null;
  content_type: string;
  workspace_id: string;
  active_version: TemplateVersion | null;
}

export default function EditTemplatePage() {
  const router = useRouter();
  const params = useParams();
  const workspaceId = params.id as string;
  const templateId = params.templateId as string;
  
  const [template, setTemplate] = useState<Template | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [htmlContent, setHtmlContent] = useState('');
  const [cssContent, setCssContent] = useState('');
  const [activeTab, setActiveTab] = useState<'html' | 'css' | 'preview'>('html');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchTemplate();
  }, [templateId]);

  const fetchTemplate = async () => {
    try {
      // Use the correct API endpoint
      const response = await apiClient.get(`/templates/${templateId}`);
      const data = response.data;
      setTemplate(data);
      setName(data.name);
      setDescription(data.description || '');
      // Content is in active_version
      setHtmlContent(data.active_version?.content || '');
      setCssContent(data.active_version?.css_content || '');
    } catch (err) {
      console.error('Failed to load template:', err);
      setError('Failed to load template');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError('Template name is required');
      return;
    }

    setSaving(true);
    setError('');

    try {
      // Update template metadata
      await apiClient.patch(`/templates/${templateId}`, {
        name: name.trim(),
        description: description.trim() || null,
      });
      
      // Create new version with updated content
      await apiClient.post(`/templates/${templateId}/versions`, {
        content: htmlContent,
        css_content: cssContent || null,
        change_notes: 'Updated via editor',
      });
      
      router.push(`/dashboard/workspaces/${workspaceId}`);
    } catch (err: any) {
      console.error('Failed to save template:', err);
      setError(err.response?.data?.detail || 'Failed to save template');
    } finally {
      setSaving(false);
    }
  };

  const getPreviewHtml = () => {
    return `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            body { font-family: system-ui, sans-serif; padding: 20px; }
            ${cssContent}
          </style>
        </head>
        <body>
          ${htmlContent}
        </body>
      </html>
    `;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b bg-background px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push(`/dashboard/workspaces/${workspaceId}`)}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="text-lg font-semibold h-auto py-1 px-2 border-transparent hover:border-input focus:border-input"
                placeholder="Template name"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={handleSave} disabled={saving}>
              <Save className="h-4 w-4 mr-2" />
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
        
        {error && (
          <div className="mt-2 text-sm text-red-500">{error}</div>
        )}
        
        <div className="mt-4">
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Template description (optional)"
            className="resize-none h-16"
          />
        </div>
      </div>

      {/* Editor Tabs */}
      <div className="border-b bg-muted/30">
        <div className="flex px-6">
          <button
            onClick={() => setActiveTab('html')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'html'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <Code className="h-4 w-4" />
            HTML
          </button>
          <button
            onClick={() => setActiveTab('css')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'css'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <Palette className="h-4 w-4" />
            CSS
          </button>
          <button
            onClick={() => setActiveTab('preview')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'preview'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <Eye className="h-4 w-4" />
            Preview
          </button>
        </div>
      </div>

      {/* Editor Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'html' && (
          <MonacoEditor
            height="100%"
            language="html"
            value={htmlContent}
            onChange={(value) => setHtmlContent(value || '')}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              wordWrap: 'on',
              automaticLayout: true,
            }}
          />
        )}

        {activeTab === 'css' && (
          <MonacoEditor
            height="100%"
            language="css"
            value={cssContent}
            onChange={(value) => setCssContent(value || '')}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              lineNumbers: 'on',
              wordWrap: 'on',
              automaticLayout: true,
            }}
          />
        )}

        {activeTab === 'preview' && (
          <div className="h-full bg-white">
            <iframe
              srcDoc={getPreviewHtml()}
              className="w-full h-full border-0"
              title="Template Preview"
              sandbox="allow-scripts"
            />
          </div>
        )}
      </div>

      {/* Variable Help */}
      <div className="border-t bg-muted/30 px-6 py-3">
        <div className="text-sm text-muted-foreground">
          <strong>Template Variables:</strong> Use <code className="bg-muted px-1 rounded">{'{{column_name}}'}</code> to insert data from your CSV/Excel columns.
          Example: <code className="bg-muted px-1 rounded">{'{{name}}'}</code>, <code className="bg-muted px-1 rounded">{'{{email}}'}</code>, <code className="bg-muted px-1 rounded">{'{{date}}'}</code>
        </div>
      </div>
    </div>
  );
}
