/**
 * App routing with React Router
 */

import { createBrowserRouter, RouterProvider, Outlet } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

// Lazy load pages for code splitting
const LoginPage = lazy(() => import('@/components/auth/LoginForm').then(m => ({ default: () => <m.LoginForm /> })));
const RegisterPage = lazy(() => import('@/components/auth/RegisterForm').then(m => ({ default: () => <m.RegisterForm /> })));
const HomePage = lazy(() => import('@/pages/HomePage').then(m => ({ default: () => <m.HomePage /> })));
const JobsPage = lazy(() => import('@/pages/JobsPage').then(m => ({ default: () => <m.JobsPage /> })));
const CVUploadPage = lazy(() => import('@/pages/CVUploadPage').then(m => ({ default: () => <m.CVUploadPage /> })));
const ResumesPage = lazy(() => import('@/pages/ResumesPage').then(m => ({ default: () => <m.ResumesPage /> })));
const ResumeDetailPage = lazy(() => import('@/pages/ResumeDetailPage').then(m => ({ default: () => <m.ResumeDetailPage /> })));
const CandidatesPage = lazy(() => import('@/pages/CandidatesPage').then(m => ({ default: () => <m.CandidatesPage /> })));
const CandidateDetailPage = lazy(() => import('@/pages/CandidateDetailPage').then(m => ({ default: () => <m.CandidateDetailPage /> })));
const BatchPage = lazy(() => import('@/pages/BatchPage').then(m => ({ default: () => <m.BatchPage /> })));
const JobDetailPage = lazy(() => import('@/pages/JobDetailPage').then(m => ({ default: () => <m.JobDetailPage /> })));

// Loading component
function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-lg">Loading...</div>
    </div>
  );
}

// Wrapper component for protected routes with Outlet
function ProtectedRouteWrapper() {
  return (
    <ProtectedRoute>
      <Outlet />
    </ProtectedRoute>
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
    element: <ProtectedRouteWrapper />,
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={<Loading />}>
            <HomePage />
          </Suspense>
        ),
      },
      {
        path: 'jobs',
        element: (
          <Suspense fallback={<Loading />}>
            <JobsPage />
          </Suspense>
        ),
      },
      {
        path: 'jobs/:id',
        element: (
          <Suspense fallback={<Loading />}>
            <JobDetailPage />
          </Suspense>
        ),
      },
      {
        path: 'upload-cv',
        element: (
          <Suspense fallback={<Loading />}>
            <CVUploadPage />
          </Suspense>
        ),
      },
      {
        path: 'resumes',
        element: (
          <Suspense fallback={<Loading />}>
            <ResumesPage />
          </Suspense>
        ),
      },
      {
        path: 'resumes/upload',
        element: (
          <Suspense fallback={<Loading />}>
            <CVUploadPage />
          </Suspense>
        ),
      },
      {
        path: 'resumes/:id',
        element: (
          <Suspense fallback={<Loading />}>
            <ResumeDetailPage />
          </Suspense>
        ),
      },
      {
        path: 'candidates',
        element: (
          <Suspense fallback={<Loading />}>
            <CandidatesPage />
          </Suspense>
        ),
      },
      {
        path: 'candidates/:id',
        element: (
          <Suspense fallback={<Loading />}>
            <CandidateDetailPage />
          </Suspense>
        ),
      },
      {
        path: 'batch',
        element: (
          <Suspense fallback={<Loading />}>
            <BatchPage />
          </Suspense>
        ),
      },
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
