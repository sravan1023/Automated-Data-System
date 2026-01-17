'use client';

import { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Play, Save, Code, Eye, Settings } from 'lucide-react';

interface TemplateEditorProps {
  initialHtml?: string;
  initialCss?: string;
  availableFields?: string[];
  onSave?: (html: string, css: string) => void;
  onPreview?: (html: string, css: string) => void;
}

const defaultHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Document</title>
</head>
<body>
  <div class="container">
    <h1>Hello, {{ name }}!</h1>
    <p>This is your personalized document.</p>
    
    <div class="details">
      <p><strong>Email:</strong> {{ email }}</p>
      <p><strong>Date:</strong> {{ date }}</p>
    </div>
  </div>
</body>
</html>`;

const defaultCss = `/* Template Styles */
body {
  font-family: 'Arial', sans-serif;
  margin: 0;
  padding: 40px;
  color: #333;
}

.container {
  max-width: 800px;
  margin: 0 auto;
}

h1 {
  color: #2563eb;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 16px;
}

.details {
  background: #f9fafb;
  padding: 20px;
  border-radius: 8px;
  margin-top: 24px;
}

.details p {
  margin: 8px 0;
}`;

export function TemplateEditor({
  initialHtml = defaultHtml,
  initialCss = defaultCss,
  availableFields = [],
  onSave,
  onPreview,
}: TemplateEditorProps) {
  const [html, setHtml] = useState(initialHtml);
  const [css, setCss] = useState(initialCss);
  const [activeTab, setActiveTab] = useState('html');

  const handleSave = () => {
    onSave?.(html, css);
  };

  const handlePreview = () => {
    onPreview?.(html, css);
  };

  const insertField = (field: string) => {
    const insertion = `{{ ${field} }}`;
    setHtml((prev) => prev + insertion);
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
    <div className="flex h-full flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handlePreview}>
            <Play className="mr-2 h-4 w-4" />
            Preview
          </Button>
          <Button size="sm" onClick={handleSave}>
            <Save className="mr-2 h-4 w-4" />
            Save
          </Button>
        </div>
      </div>

      <div className="grid flex-1 gap-4 lg:grid-cols-3">
        {/* Editor Panel */}
        <div className="lg:col-span-2">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="html">
                <Code className="mr-2 h-4 w-4" />
                HTML
              </TabsTrigger>
              <TabsTrigger value="css">
                <Settings className="mr-2 h-4 w-4" />
                CSS
              </TabsTrigger>
              <TabsTrigger value="preview">
                <Eye className="mr-2 h-4 w-4" />
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
        </div>

        {/* Fields Panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Available Fields</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-4 text-sm text-muted-foreground">
              Click a field to insert it into your template. Use Jinja2 syntax:
              {' '}
              <code className="rounded bg-muted px-1">{'{{ field_name }}'}</code>
            </p>

            {availableFields.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {availableFields.map((field) => (
                  <Button
                    key={field}
                    variant="outline"
                    size="sm"
                    onClick={() => insertField(field)}
                  >
                    {field}
                  </Button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Upload a data source to see available fields.
              </p>
            )}

            <div className="mt-6 space-y-4">
              <div>
                <Label>Custom Field</Label>
                <div className="mt-2 flex gap-2">
                  <Input
                    id="customField"
                    placeholder="field_name"
                  />
                  <Button
                    variant="outline"
                    onClick={() => {
                      const input = document.getElementById('customField') as HTMLInputElement;
                      if (input.value) {
                        insertField(input.value);
                        input.value = '';
                      }
                    }}
                  >
                    Insert
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
