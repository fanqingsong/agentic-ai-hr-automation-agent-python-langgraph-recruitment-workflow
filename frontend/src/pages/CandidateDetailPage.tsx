/**
 * Candidate detail page (HR): view one candidate's resume data and AI evaluation
 */

import { useState, useEffect, useRef } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { candidatesAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [fileAvailable, setFileAvailable] = useState<boolean | null>(null);
  const blobUrlRef = useRef<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['candidate', id],
    queryFn: async () => {
      const res = await candidatesAPI.get(id!);
      return res.data;
    },
    enabled: !!id,
  });

  useEffect(() => {
    if (!id || !data) return;
    let cancelled = false;
    setFileAvailable(null);
    candidatesAPI.downloadBlob(id)
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
      <div className="max-w-4xl mx-auto px-4 py-8">
        <p className="text-gray-500">Invalid candidate id.</p>
        <Button asChild variant="link" className="mt-2">
          <Link to="/candidates">Back to Candidates</Link>
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <p className="text-gray-500">Loading candidate...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Failed to load candidate or you do not have permission to view it.
        </div>
        <Button asChild variant="link" className="mt-4">
          <Link to="/candidates">Back to Candidates</Link>
        </Button>
      </div>
    );
  }

  const evaluation = data.evaluation as { score?: number; decision?: string; reasoning?: string; strengths?: string[]; gaps?: string[] } | undefined;
  const skillsMatch = data.skills_match as { strong?: string[]; partial?: string[]; missing?: string[] } | undefined;
  const score = data.evaluation_score ?? evaluation?.score;

  const handleDownload = async () => {
    if (!id) return;
    setDownloadError(null);
    try {
      const res = await candidatesAPI.downloadBlob(id);
      const blob = res.data as Blob;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resume-${data.candidate_name?.replace(/\s+/g, '_') || id}.pdf`;
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

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6 flex items-center justify-between">
        <Button variant="outline" size="sm" asChild>
          <Link to="/candidates">Back to Candidates</Link>
        </Button>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>{data.candidate_name ?? 'Unknown'}</CardTitle>
          <CardDescription>
            {data.candidate_email ?? '—'}
            {data.source_folder ? ` · 来源文件夹: ${data.source_folder}` : ''}
            {data.job_title || data.job_id ? ` · Job: ${data.job_title || data.job_id}` : ''}
            {data.timestamp && ` · ${new Date(data.timestamp).toLocaleDateString()}`}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {score != null && (
            <p className="text-lg font-medium">
              Evaluation score: <span className="text-primary">{score}</span> / 100
            </p>
          )}
          {evaluation?.decision && (
            <p className="text-sm text-gray-600">Decision: {evaluation.decision}</p>
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
              </>
            )}
            {fileAvailable === false && (
              <p className="text-sm text-gray-500">
                原始简历文件不可用。可能是较早导入的记录，当时尚未启用文件存储。
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {fileAvailable === true && blobUrl && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">原始简历</CardTitle>
            <CardDescription>候选人上传的 CV 文件（PDF 内嵌预览）</CardDescription>
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

      {data.summary && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700 whitespace-pre-wrap">{data.summary}</p>
          </CardContent>
        </Card>
      )}

      {evaluation?.reasoning && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Evaluation reasoning</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700 whitespace-pre-wrap">{evaluation.reasoning}</p>
          </CardContent>
        </Card>
      )}

      {(evaluation?.strengths?.length || evaluation?.gaps?.length) ? (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Strengths & gaps</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {evaluation?.strengths?.length ? (
              <div>
                <p className="font-medium text-gray-700 mb-1">Strengths</p>
                <ul className="list-disc list-inside text-gray-600 space-y-0.5">
                  {evaluation.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {evaluation?.gaps?.length ? (
              <div>
                <p className="font-medium text-gray-700 mb-1">Gaps</p>
                <ul className="list-disc list-inside text-gray-600 space-y-0.5">
                  {evaluation.gaps.map((g, i) => (
                    <li key={i}>{g}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      {skillsMatch && (skillsMatch.strong?.length || skillsMatch.partial?.length || skillsMatch.missing?.length) ? (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Skills match</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {skillsMatch.strong?.length ? (
              <div>
                <p className="font-medium text-green-700 mb-1">Strong match</p>
                <p className="text-gray-600">{skillsMatch.strong.join(', ')}</p>
              </div>
            ) : null}
            {skillsMatch.partial?.length ? (
              <div>
                <p className="font-medium text-gray-700 mb-1">Partial match</p>
                <p className="text-gray-600">{skillsMatch.partial.join(', ')}</p>
              </div>
            ) : null}
            {skillsMatch.missing?.length ? (
              <div>
                <p className="font-medium text-amber-700 mb-1">Missing</p>
                <p className="text-gray-600">{skillsMatch.missing.join(', ')}</p>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
