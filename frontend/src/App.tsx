/**
 * App routing with React Router
 */

import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { lazy, Suspense } from 'react';

// Lazy load pages for code splitting
const LoginPage = lazy(() => import('@/components/auth/LoginForm').then(m => ({ default: () => <m.LoginForm /> })));
const RegisterPage = lazy(() => import('@/components/auth/RegisterForm').then(m => ({ default: () => <m.RegisterForm /> })));
const HomePage = lazy(() => import('@/pages/HomePage').then(m => ({ default: () => <m.HomePage() })));
const ProtectedRoute = lazy(() => import('@/components/auth/ProtectedRoute').then(m => ({ default: m.ProtectedRoute }));

// Loading component
function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-lg">Loading...</div>
    </div>
  );
}

// Router configuration
const router = createBrowserRouter([
  {
    path: '/login',
    element: (
      <Suspense fallback={<Loading />}>
        <LoginPage />
      </Suspense>
    ),
  },
  {
    path: '/register',
    element: (
      <Suspense fallback={<Loading />}>
        <RegisterPage />
      </Suspense>
    ),
  },
  {
    path: '/',
    element: (
      <Suspense fallback={<Loading />}>
        <ProtectedRoute />
      </Suspense>
    ),
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={<Loading />}>
            <HomePage />
          </Suspense>
        ),
      },
      // TODO: Add more routes here
      // {
      //   path: 'jobs',
      //   element: <JobListPage />,
      // },
      // {
      //   path: 'candidates',
      //   element: <CandidateListPage />,
      // },
      // {
      //   path: 'dashboard',
      //   element: <DashboardPage />,
      // },
    ],
  },
  {
    path: '*',
    element: <div>Page not found</div>,
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}
