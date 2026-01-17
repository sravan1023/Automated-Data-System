'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FileText, Upload, Zap, FolderOpen, UserPlus, LogIn, Users } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';

export default function HomePage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const { login, register } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, password, name);
      }
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'An error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left Column - Content (60%) */}
      <div className="flex w-[60%] flex-col">
        {/* Header */}
        <header className="border-b">
          <div className="container flex h-16 items-center">
            <div className="flex items-center gap-2">
              <FileText className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">FlowDoc</span>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          {/* Hero Section */}
          <section className="container py-16">
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
              Transform Your Data Into
              <br />
              <span className="text-primary">Professional Documents</span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg text-muted-foreground">
              FlowDoc automates the creation of personalized documents at scale.
              Upload your data, design your templates, and generate thousands of
              documents in minutes.
            </p>
          </section>

          {/* Features Section */}
          <section className="border-t bg-muted/50 py-16">
            <div className="container">
              <h2 className="text-2xl font-bold">
                Everything You Need for Document Automation
              </h2>
              <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                <FeatureCard
                  icon={<Upload className="h-8 w-8" />}
                  title="Easy Data Import"
                  description="Upload CSV, Excel, or connect to your existing data sources. We handle the rest."
                />
                <FeatureCard
                  icon={<FileText className="h-8 w-8" />}
                  title="Template Designer"
                  description="Create beautiful templates with our visual editor. Use Jinja2 for dynamic content."
                />
                <FeatureCard
                  icon={<Zap className="h-8 w-8" />}
                  title="Bulk Generation"
                  description="Generate thousands of personalized PDFs in parallel. Download as a bundle or individually."
                />
              </div>
            </div>
          </section>
        </main>

        {/* Footer */}
        <footer className="border-t py-6">
          <div className="container flex flex-col items-center justify-between gap-4 sm:flex-row">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              <span className="font-semibold">FlowDoc</span>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2026 FlowDoc. All rights reserved.
            </p>
          </div>
        </footer>
      </div>

      {/* Right Column - Auth (40%) */}
      <div className="flex w-[35%] flex-col border-l bg-muted/30 p-8 overflow-y-auto">
        <div className="flex flex-1 flex-col justify-center">
          <div className="mx-auto w-full max-w-sm">
            {/* Account Section */}
            <div className="space-y-5">
              <div className="text-center">
                <h2 className="text-2xl font-bold">Welcome</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {isLogin ? 'Sign in to your account' : 'Create a new account'}
                </p>
              </div>

              {/* Login/Signup Tabs */}
              <div className="flex items-center gap-1 rounded-lg bg-muted p-1">
                <Button
                  variant={isLogin ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setIsLogin(true)}
                  className="flex-1"
                >
                  <LogIn className="mr-2 h-4 w-4" />
                  Login
                </Button>
                <Button
                  variant={!isLogin ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setIsLogin(false)}
                  className="flex-1"
                >
                  <UserPlus className="mr-2 h-4 w-4" />
                  Sign Up
                </Button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {!isLogin && (
                  <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input
                      id="name"
                      placeholder="Your name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required={!isLogin}
                    />
                  </div>
                )}
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
                {error && (
                  <p className="text-sm text-destructive">{error}</p>
                )}
                <Button type="submit" className="w-full" size="lg" disabled={isLoading}>
                  {isLoading ? 'Loading...' : isLogin ? 'Sign In' : 'Create Account'}
                </Button>
              </form>
            </div>

            {/* Visual Separator */}
            <div className="my-8 flex items-center gap-4">
              <div className="h-px flex-1 bg-border" />
              <span className="text-xs font-medium uppercase text-muted-foreground">
                Or skip for now
              </span>
              <div className="h-px flex-1 bg-border" />
            </div>

            {/* Guest Section */}
            <div className="rounded-lg border border-dashed bg-background/50 p-5 text-center">
              <Users className="mx-auto h-8 w-8 text-muted-foreground" />
              <h3 className="mt-3 font-semibold">Continue as Guest</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                No account needed. Jump right in.
              </p>
              <Link href="/dashboard">
                <Button className="mt-4 w-full" variant="outline" size="lg">
                  <FolderOpen className="mr-2 h-5 w-5" />
                  Open Workspace
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-6 text-card-foreground shadow-sm">
      <div className="text-primary">{icon}</div>
      <h3 className="mt-4 text-xl font-semibold">{title}</h3>
      <p className="mt-2 text-muted-foreground">{description}</p>
    </div>
  );
}
