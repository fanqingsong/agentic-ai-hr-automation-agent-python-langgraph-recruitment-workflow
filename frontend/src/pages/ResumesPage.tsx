/**
 * My Resumes page: list and maintain job seeker's uploaded resumes
 */

import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { myResumesAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function ResumesPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['my-resumes'],
    queryFn: async () => {
      const res = await myResumesAPI.list({ limit: 50 });
      return res.data;
    },
  });

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <p className="text-gray-500">Loading your resumes...</p>
      </div>
    );
  }

  if (error) {
    const err = error as { response?: { data?: { detail?: string }; status?: number }; message?: string };
    const message = err.response?.data?.detail ?? err.message ?? 'Failed to load resumes. Please try again.';
    const status = err.response?.status;
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          <p className="font-medium">
            {status === 401 ? 'Please log in to view your resumes.' : status === 403 ? 'You do not have permission to view resumes.' : 'Failed to load resumes.'}
          </p>
          <p className="text-sm mt-1">{message}</p>
        </div>
      </div>
    );
  }

  const resumes = data?.resumes ?? [];
  const total = data?.total ?? 0;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <h1 className="text-3xl font-bold text-gray-900">My Resumes</h1>
        <Button asChild>
          <Link to="/resumes/upload">Upload New Resume</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Your uploaded resumes</CardTitle>
          <CardDescription>
            View and download your previously submitted resumes. Upload a new one to get AI analysis.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {total === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p className="mb-2">You have not uploaded any resumes yet, or none are linked to your account.</p>
              <p className="mb-4 text-sm">Resumes you upload while logged in will appear here. You can also re-upload to add one now.</p>
              <Button asChild>
                <Link to="/resumes/upload">Upload your first resume</Link>
              </Button>
            </div>
          ) : (
            <ul className="divide-y divide-gray-200">
              {resumes.map((r: any) => (
                <li key={r._id} className="py-4 first:pt-0 last:pb-0 flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900 truncate">{r.candidate_name || 'Untitled'}</p>
                    <p className="text-sm text-gray-500">
                      {r.timestamp ? new Date(r.timestamp).toLocaleDateString() : '—'}
                    </p>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <Button variant="outline" size="sm" asChild>
                      <Link to={`/resumes/${r._id}`}>View</Link>
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
