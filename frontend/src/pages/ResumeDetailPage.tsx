/**
 * Resume detail page: view one uploaded resume, preview and download CV
 * Preview and download use the backend download endpoint (auth) so they work whenever the file is stored.
 */

import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { myResumesAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function ResumeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [fileAvailable, setFileAvailable] = useState<boolean | null>(null);
  const [refreshingRec, setRefreshingRec] = useState(false);
  const blobUrlRef = useRef<string | null>(null);

  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ['my-resume', id],
    queryFn: async () => {
      const res = await myResumesAPI.get(id!);
      return res.data;
    },
    enabled: !!id,
  });

  const {
    data: recData,
    isLoading: recLoading,
    isFetching: recFetching,
    refetch: refetchRec,
  } = useQuery({
    queryKey: ['my-resume-job-recommendations', id],
    queryFn: async () => {
      const res = await myResumesAPI.getJobRecommendations(id!, false);
      return res.data;
    },
    enabled: !!id,
  });

  // Fetch CV file when we have resume data; blob URL used for preview iframe and preview-in-new-tab
  useEffect(() => {
    if (!id || !data) return;
    let cancelled = false;
    setFileAvailable(null);
    myResumesAPI.downloadBlob(id)
      .then((res) => {
        if (cancelled) return;
        const url = URL.createObjectURL(res.data as Blob);
        if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = url;
        setBlobUrl(url);
        setFileAvailable(true);
      })
      .catch(() => {
        if (!cancelled) setFileAvailable(false);
      });
    return () => {
      cancelled = true;
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current);
        blobUrlRef.current = null;
      }
      setBlobUrl(null);
    };
  }, [id, data]);

  if (!id) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8">
        <p className="text-gray-500">Invalid resume id.</p>
        <Button asChild variant="link" className="mt-2">
          <Link to="/resumes">Back to My Resumes</Link>
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8">
        <p className="text-gray-500">Loading resume...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Failed to load resume or you do not have permission to view it.
        </div>
        <Button asChild variant="link" className="mt-4">
          <Link to="/resumes">Back to My Resumes</Link>
        </Button>
      </div>
    );
  }

  const resume = data as any;

  const handleDownload = async () => {
    if (!id) return;
    setDownloadError(null);
    try {
      const res = await myResumesAPI.downloadBlob(id);
      const blob = res.data as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resume-${resume.candidate_name?.replace(/\s+/g, '_') || id}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string }; status?: number } };
      setDownloadError(err.response?.data?.detail ?? 'Download failed.');
    }
  };

  const handlePreview = () => {
    if (blobUrl) window.open(blobUrl, '_blank', 'noopener,noreferrer');
    else setPreviewError('Preview not loaded. Try again.');
  };

  const handleRefreshRecommendations = async () => {
    if (!id) return;
    setRefreshingRec(true);
    try {
      await myResumesAPI.getJobRecommendations(id, true);
      await queryClient.invalidateQueries({ queryKey: ['my-resume-job-recommendations', id] });
    } catch {
      await refetchRec();
    } finally {
      setRefreshingRec(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6 flex items-center gap-4">
        <Button variant="outline" size="sm" asChild>
          <Link to="/resumes">← My Resumes</Link>
        </Button>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>{resume.candidate_name || 'Resume'}</CardTitle>
          <CardDescription>
            {resume.candidate_email} · Uploaded {resume.timestamp ? new Date(resume.timestamp).toLocaleString() : '—'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {resume.summary && (
            <div>
              <h3 className="font-medium text-gray-900 mb-1">Summary</h3>
              <p className="text-gray-600 text-sm">{resume.summary}</p>
            </div>
          )}
          <div className="pt-2 space-y-3">
            {fileAvailable === null && (
              <p className="text-sm text-gray-500">Checking if CV file is available...</p>
            )}
            {fileAvailable === true && (
              <>
                <div className="flex flex-wrap gap-2">
                  <Button variant="default" onClick={handlePreview} title="在新标签页中预览">
                    Preview CV
                  </Button>
                  <Button variant="outline" onClick={handleDownload} title="下载简历文件">
                    Download CV
                  </Button>
                </div>
                {previewError && <p className="text-sm text-red-600">{previewError}</p>}
                {downloadError && <p className="text-sm text-red-600">{downloadError}</p>}
                <p className="text-xs text-gray-500">Preview opens the file in a new tab; Download saves it to your device.</p>
              </>
            )}
            {fileAvailable === false && (
              <p className="text-sm text-gray-500">
                CV file is not available for preview or download. This may be an older upload before file storage was enabled. Please upload a new resume to use preview and download.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Job recommendations: ranked by job evaluation workflow (Graph2) */}
      <Card className="mt-6">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle className="text-lg">Recommended jobs (职位推荐排名)</CardTitle>
              <CardDescription>
                Jobs ranked by AI evaluation of this resume against each job (job evaluation workflow).
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={recLoading || recFetching || refreshingRec}
              onClick={handleRefreshRecommendations}
            >
              {refreshingRec || recFetching ? 'Evaluating…' : 'Refresh rankings'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {recLoading ? (
            <p className="text-sm text-gray-500">Loading job recommendations…</p>
          ) : (recData?.rankings?.length ?? 0) === 0 ? (
            <p className="text-sm text-gray-500">
              No rankings yet. Click &quot;Refresh rankings&quot; to run the job evaluation for all jobs (this may take a minute).
            </p>
          ) : (
            <ul className="divide-y divide-gray-200">
              {recData!.rankings.map((item: { rank: number; job: { _id: string; job_title?: string }; score: number | null; reasoning?: string; tag?: string }) => (
                <li key={item.rank} className="py-3 first:pt-0">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <span className="font-medium text-gray-500 mr-2">#{item.rank}</span>
                      <Link
                        to={`/jobs/${item.job?._id ?? ''}`}
                        className="font-medium text-gray-900 hover:underline"
                      >
                        {item.job?.job_title ?? 'Unknown job'}
                      </Link>
                      {item.score != null && (
                        <span className="ml-2 text-sm text-gray-600">Score: {item.score}/100</span>
                      )}
                      {item.tag && (
                        <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-600">{item.tag}</span>
                      )}
                    </div>
                  </div>
                  {item.reasoning && (
                    <p className="mt-1 text-sm text-gray-600 whitespace-pre-wrap line-clamp-2">{item.reasoning}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {fileAvailable === true && blobUrl && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-lg">Resume preview</CardTitle>
            <CardDescription>Inline preview of your uploaded CV (PDF)</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border bg-gray-100 overflow-hidden">
              <iframe
                src={blobUrl}
                title="CV Preview"
                className="w-full h-[min(80vh,720px)] min-h-[480px]"
              />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
