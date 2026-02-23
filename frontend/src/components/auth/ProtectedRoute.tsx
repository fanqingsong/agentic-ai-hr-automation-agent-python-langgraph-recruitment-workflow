/**
 * Protected route component
 */

import { Navigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Layout } from '@/components/layout/Layout';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading, isAuthenticated } = useAuth();

  // Show loading only while actively fetching
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Layout>{children}</Layout>;
}
