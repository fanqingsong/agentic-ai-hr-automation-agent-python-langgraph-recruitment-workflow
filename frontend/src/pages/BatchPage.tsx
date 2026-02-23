/**
 * Batch processing page (HR): select job, process CVs from server directory, view result and export
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { jobsAPI, batchAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';

export function BatchPage() {
  const [selectedJobId, setSelectedJobId] = useState('');
  const [cvDirectory, setCvDirectory] = useState('');
  const [maxConcurrent, setMaxConcurrent] = useState(5);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<{
    batch_id: string;
    summary: { total: number; successful: number; failed: number; average_score?: number };
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const { data: jobsData } = useQuery({
    queryKey: ['jobs'],
    queryFn: async () => {
      const res = await jobsAPI.list();
      return res.data;
    },
  });

  const jobs = jobsData?.jobs ?? [];

  const handleProcessDirectory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedJobId.trim() || !cvDirectory.trim()) {
      setError('Please select a job and enter the server directory path.');
      return;
    }
    setError(null);
    setResult(null);
    setProcessing(true);
    try {
      const form = new FormData();
      form.append('job_id', selectedJobId);
      form.append('cv_directory', cvDirectory.trim());
      form.append('max_concurrent', String(maxConcurrent));
      const res = await batchAPI.processDirectory(form as any);
      const data = res.data as { success?: boolean; batch_id?: string; summary?: any };
      if (data.success && data.batch_id) {
        setResult({
          batch_id: data.batch_id,
          summary: data.summary ?? { total: 0, successful: 0, failed: 0 },
        });
      } else {
        setError('Unexpected response from server.');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail ?? err.message ?? 'Batch processing failed.');
    } finally {
      setProcessing(false);
    }
  };

  const handleExportBatch = async () => {
    if (!result?.batch_id) return;
    setExporting(true);
    try {
      const res = await batchAPI.export(result.batch_id);
      const blob = res.data as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `batch_${result.batch_id}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Batch Processing</h1>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Process from server directory</CardTitle>
          <CardDescription>
            Enter a path on the server where CV files (PDF, DOC, DOCX) are stored. All files in that directory will be processed for the selected job.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleProcessDirectory} className="space-y-4">
            <div className="space-y-2">
              <Label>Job</Label>
              <select
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                required
              >
                <option value="">Select a job</option>
                {jobs.map((j: { _id: string; job_title?: string }) => (
                  <option key={j._id} value={j._id}>
                    {j.job_title || j._id}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Server directory path</Label>
              <Input
                placeholder="e.g. /tmp/cvs or ./uploads/cvs"
                value={cvDirectory}
                onChange={(e) => setCvDirectory(e.target.value)}
                required
              />
              <p className="text-xs text-gray-500">
                Path relative to the backend server. The server must have read access to this directory.
              </p>
            </div>
            <div className="space-y-2">
              <Label>Max concurrent (1–20)</Label>
              <Input
                type="number"
                min={1}
                max={20}
                value={maxConcurrent}
                onChange={(e) => setMaxConcurrent(parseInt(e.target.value, 10) || 5)}
              />
            </div>
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
                {error}
              </div>
            )}
            <Button type="submit" disabled={processing}>
              {processing ? 'Processing...' : 'Process directory'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Result</CardTitle>
            <CardDescription>Batch ID: {result.batch_id}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p>Total: {result.summary.total}</p>
            <p>Successful: {result.summary.successful}</p>
            <p>Failed: {result.summary.failed}</p>
            {result.summary.average_score != null && (
              <p>Average score: {result.summary.average_score.toFixed(1)}</p>
            )}
            <Button variant="outline" onClick={handleExportBatch} disabled={exporting} className="mt-4">
              {exporting ? 'Exporting...' : 'Export batch (CSV)'}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
