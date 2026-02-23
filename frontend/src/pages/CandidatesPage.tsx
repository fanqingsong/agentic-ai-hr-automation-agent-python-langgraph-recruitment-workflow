/**
 * Candidates list page (HR): filter, sort, paginate, export
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { candidatesAPI, jobsAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';

const PAGE_SIZE = 20;

interface Candidate {
  _id: string;
  candidate_name?: string;
  candidate_email?: string;
  evaluation_score?: number;
  job_id?: string;
  job_title?: string;
  timestamp?: string;
}

interface CandidatesResponse {
  total: number;
  limit: number;
  offset: number;
  candidates: Candidate[];
}

export function CandidatesPage() {
  const [jobId, setJobId] = useState<string>('');
  const [minScore, setMinScore] = useState<string>('');
  const [maxScore, setMaxScore] = useState<string>('');
  const [sortBy, setSortBy] = useState<'timestamp' | 'score' | 'name'>('timestamp');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState<'csv' | 'xlsx'>('csv');

  const { data, isLoading, error, refetch } = useQuery<CandidatesResponse>({
    queryKey: ['candidates', jobId, minScore, maxScore, sortBy, sortOrder, page],
    queryFn: async () => {
      const params: Record<string, string | number> = {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        sort_by: sortBy,
        sort_order: sortOrder,
      };
      if (jobId) params.job_id = jobId;
      const min = minScore.trim() ? parseInt(minScore, 10) : undefined;
      const max = maxScore.trim() ? parseInt(maxScore, 10) : undefined;
      if (min !== undefined && !Number.isNaN(min)) params.min_score = min;
      if (max !== undefined && !Number.isNaN(max)) params.max_score = max;
      const res = await candidatesAPI.list(params);
      return res.data;
    },
  });

  const { data: jobsData } = useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      const res = await jobsAPI.list();
      return res.data;
    },
  });

  const jobs = jobsData?.jobs ?? [];
  const candidates = data?.candidates ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const handleExport = async () => {
    setExporting(true);
    try {
      const form = new FormData();
      if (jobId) form.append('job_id', jobId);
      form.append('format', exportFormat);
      const min = minScore.trim() ? parseInt(minScore, 10) : null;
      const max = maxScore.trim() ? parseInt(maxScore, 10) : null;
      if (min !== null && !Number.isNaN(min)) form.append('min_score', String(min));
      if (max !== null && !Number.isNaN(max)) form.append('max_score', String(max));
      const res = await candidatesAPI.export(form);
      const blob = res.data as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `candidates_export_${Date.now()}.${exportFormat === 'csv' ? 'csv' : 'xlsx'}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
    } finally {
      setExporting(false);
    }
  };

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Failed to load candidates. You may not have permission (HR/Admin only).
        </div>
        <Button onClick={() => refetch()} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Candidates</h1>
          <p className="text-gray-600 mt-1">{total} candidate{total !== 1 ? 's' : ''} found</p>
        </div>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Filter and sort candidates. Export to CSV or Excel.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-2">
              <Label>Job</Label>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                value={jobId || 'all'}
                onChange={(e) => setJobId(e.target.value === 'all' ? '' : e.target.value)}
              >
                <option value="all">All jobs</option>
                {jobs.map((j: { _id: string; job_title?: string }) => (
                  <option key={j._id} value={j._id}>
                    {j.job_title || j._id}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Min score</Label>
              <Input
                type="number"
                min={0}
                max={100}
                placeholder="0"
                value={minScore}
                onChange={(e) => setMinScore(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Max score</Label>
              <Input
                type="number"
                min={0}
                max={100}
                placeholder="100"
                value={maxScore}
                onChange={(e) => setMaxScore(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Sort by</Label>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'timestamp' | 'score' | 'name')}
              >
                <option value="timestamp">Date</option>
                <option value="score">Score</option>
                <option value="name">Name</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>Order</Label>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
              >
                <option value="desc">Descending</option>
                <option value="asc">Ascending</option>
              </select>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select
              className="flex h-9 w-28 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value as 'csv' | 'xlsx')}
            >
              <option value="csv">CSV</option>
              <option value="xlsx">Excel</option>
            </select>
            <Button variant="outline" onClick={handleExport} disabled={exporting || total === 0}>
              {exporting ? 'Exporting...' : 'Export'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="flex justify-center min-h-[200px] items-center">
          <p className="text-gray-500">Loading candidates...</p>
        </div>
      ) : candidates.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <p className="text-center text-gray-500">No candidates match the current filters.</p>
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-gray-50">
                      <th className="text-left py-3 px-4 font-medium text-gray-700">Name</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-700">Email</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-700">Score</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-700">Job</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-700">Date</th>
                      <th className="text-left py-3 px-4 font-medium text-gray-700">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((c) => (
                      <tr key={c._id} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="py-3 px-4">{c.candidate_name ?? '—'}</td>
                        <td className="py-3 px-4 text-sm text-gray-600">{c.candidate_email ?? '—'}</td>
                        <td className="py-3 px-4">{c.evaluation_score ?? '—'}</td>
                        <td className="py-3 px-4 text-sm text-gray-600">{c.job_title ?? c.job_id ?? '—'}</td>
                        <td className="py-3 px-4 text-sm text-gray-600">
                          {c.timestamp ? new Date(c.timestamp).toLocaleDateString() : '—'}
                        </td>
                        <td className="py-3 px-4">
                          <Button variant="outline" size="sm" asChild>
                            <Link to={`/candidates/${c._id}`}>View</Link>
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-gray-600">
                Page {page + 1} of {totalPages}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                  disabled={page >= totalPages - 1}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
