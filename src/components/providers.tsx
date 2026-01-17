'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { useState, createContext, useContext } from 'react';
import { AuthProvider } from '@/lib/auth-context';

// Create a context to share the queryClient
const QueryClientContext = createContext<QueryClient | null>(null);

export function useQueryClientContext() {
  return useContext(QueryClientContext);
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <QueryClientContext.Provider value={queryClient}>
        <AuthProvider>{children}</AuthProvider>
      </QueryClientContext.Provider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
