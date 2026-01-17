'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Loader2 } from 'lucide-react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, isLoading, loginAsGuest } = useAuth();
  const [isSettingUpGuest, setIsSettingUpGuest] = useState(false);

  useEffect(() => {
    // Only auto-login as guest if:
    // 1. Auth check is done (not loading)
    // 2. User is not authenticated
    // 3. We're not already setting up guest
    if (!isLoading && !isAuthenticated && !isSettingUpGuest) {
      setIsSettingUpGuest(true);
      loginAsGuest()
        .catch((err) => {
          console.error('Failed to setup guest:', err);
        })
        .finally(() => {
          setIsSettingUpGuest(false);
        });
    }
  }, [isLoading, isAuthenticated, loginAsGuest, isSettingUpGuest]);

  // Show loading spinner while:
  // 1. Initial auth check is happening
  // 2. Setting up guest session
  // 3. Not yet authenticated (waiting for guest setup to complete)
  if (isLoading || isSettingUpGuest || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
