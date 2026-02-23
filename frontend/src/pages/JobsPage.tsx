/**
 * Jobs page component
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobsAPI } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface Job {
  _id: string;
  ulid: string;
  job_title: string;
  job_description: string;
  hr_email: string;
  createdAt: string;
}

interface JobsResponse {
  total: number;
  jobs: Job[];
}

export function JobsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formTitle, setFormTitle] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formHrName, setFormHrName] = useState('');
  const [formHrEmail, setFormHrEmail] = useState('');

  const isHR = user?.role === 'hr_manager' || user?.role === 'admin';

  const { data, isLoading, error, refetch } = useQuery<JobsResponse>({
    queryKey: ['jobs'],
    queryFn: async () => {
      const response = await jobsAPI.list();
      return response.data;
    },
  });

  const createMutation = useMutation({
    mutationFn: (payload: { title: string; description: string; hr_name: string; hr_email: string }) =>
      jobsAPI.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      setShowCreateForm(false);
      setFormTitle('');
      setFormDescription('');
      setFormHrName('');
      setFormHrEmail('');
    },
  });

  const jobs = data?.jobs || [];
  const total = data?.total || 0;

  const handleSubmitCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim()) return;
    createMutation.mutate({
      title: formTitle.trim(),
      description: formDescription.trim(),
      hr_name: (formHrName.trim() || user?.name || 'HR').toString(),
      hr_email: (formHrEmail.trim() || user?.email || '').toString(),
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-lg">Loading jobs...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Failed to load jobs. Please try again later.
        </div>
        <Button onClick={() => refetch()} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Available Jobs</h1>
          <p className="text-gray-600 mt-1">{total} {total === 1 ? 'position' : 'positions'} available</p>
        </div>
        {isHR && (
          <Button onClick={() => setShowCreateForm(!showCreateForm)}>
            {showCreateForm ? 'Cancel' : 'Create Job'}
          </Button>
        )}
      </div>

      {isHR && showCreateForm && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Create job posting</CardTitle>
            <CardDescription>Add a new position. HR contact info is used for candidate inquiries.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmitCreate} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="job-title">Job title</Label>
                <Input
                  id="job-title"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="e.g. Senior Backend Engineer"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="job-description">Description</Label>
                <textarea
                  id="job-description"
                  className="flex min-h-[120px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm"
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  placeholder="Job requirements, responsibilities, etc."
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="hr-name">HR contact name</Label>
                  <Input
                    id="hr-name"
                    value={formHrName}
                    onChange={(e) => setFormHrName(e.target.value)}
                    placeholder={user?.name || 'Name'}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="hr-email">HR contact email</Label>
                  <Input
                    id="hr-email"
                    type="email"
                    value={formHrEmail}
                    onChange={(e) => setFormHrEmail(e.target.value)}
                    placeholder={user?.email || 'hr@company.com'}
                  />
                </div>
              </div>
              {createMutation.isError && (
                <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm text-red-700">
                  <p className="font-medium">Create job failed</p>
                  <p className="mt-1">
                    {Array.isArray((createMutation.error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail)
                      ? (createMutation.error as { response?: { data?: { detail?: unknown[] } } }).response?.data?.detail?.map((e: { msg?: string; loc?: string[] }) => e.msg || JSON.stringify(e)).join('; ')
                      : (createMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? (createMutation.error as Error).message ?? 'Unknown error'}
                  </p>
                  <p className="mt-1 text-xs">
                    Status: {(createMutation.error as { response?: { status?: number } })?.response?.status ?? '—'}
                  </p>
                </div>
              )}
              <div className="flex gap-2">
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Creating...' : 'Create'}
                </Button>
                <Button type="button" variant="outline" onClick={() => setShowCreateForm(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {jobs.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <p className="text-center text-gray-500">No jobs available at the moment.</p>
            {isHR && !showCreateForm && (
              <p className="text-center mt-2">
                <Button variant="link" onClick={() => setShowCreateForm(true)}>
                  Create the first job
                </Button>
              </p>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {jobs.map((job) => (
            <Card key={job._id || job.ulid}>
              <CardHeader>
                <CardTitle>{job.job_title}</CardTitle>
                <CardDescription>
                  Posted on {job.createdAt ? new Date(job.createdAt).toLocaleDateString() : 'Recently'}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-gray-700 whitespace-pre-wrap line-clamp-3">
                  {job.job_description || 'No description.'}
                </p>
                <p className="text-sm text-gray-500 mt-4">
                  Contact: {job.hr_email}
                </p>
              </CardContent>
              <CardFooter>
                <Button variant="outline" asChild>
                  <Link to={`/jobs/${job._id}`}>View Details</Link>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
