/**
 * Job detail page: full description, contact, and candidate ranking recommendations
 */

import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { jobsAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [refreshingRec, setRefreshingRec] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['job', id],
    queryFn: async () => {
      const res = await jobsAPI.get(id!);
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
    queryKey: ['job-candidate-recommendations', id],
    queryFn: async () => {
      const res = await jobsAPI.getCandidateRecommendations(id!, false);
      return res.data;
    },
    enabled: !!id,
  });

  const handleRefreshRecommendations = async () => {
    if (!id) return;
    setRefreshingRec(true);
    try {
      await jobsAPI.getCandidateRecommendations(id, true);
      await queryClient.invalidateQueries({ queryKey: ['job-candidate-recommendations', id] });
    } catch {
      await refetchRec();
    } finally {
      setRefreshingRec(false);
    }
  };

  if (!id) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <p className="text-gray-500">Invalid job id.</p>
        <Button asChild variant="link" className="mt-2">
          <Link to="/jobs">Back to Jobs</Link>
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <p className="text-gray-500">Loading job...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Failed to load job or job not found.
        </div>
        <Button asChild variant="link" className="mt-4">
          <Link to="/jobs">Back to Jobs</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <Button variant="outline" size="sm" asChild>
          <Link to="/jobs">Back to Jobs</Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{data.job_title}</CardTitle>
          <CardDescription>
            Posted on {data.createdAt ? new Date(data.createdAt).toLocaleDateString() : 'Recently'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-1">Description</h3>
            <p className="text-gray-700 whitespace-pre-wrap">
              {data.job_description || 'No description.'}
            </p>
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-1">Contact</h3>
            <p className="text-gray-600">{data.hr_email}</p>
          </div>
        </CardContent>
      </Card>

      {/* Candidate ranking recommendations (候选人排名推荐) */}
      <Card className="mt-6">
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle className="text-lg">Candidate ranking (候选人排名推荐)</CardTitle>
              <CardDescription>
                Candidates ranked by AI evaluation against this job (job evaluation workflow).
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
            <p className="text-sm text-gray-500">Loading candidate rankings…</p>
          ) : (recData?.rankings?.length ?? 0) === 0 ? (
            <p className="text-sm text-gray-500">
              No rankings yet. Click &quot;Refresh rankings&quot; to run the job evaluation for all candidates (this may take a minute).
            </p>
          ) : (
            <ul className="divide-y divide-gray-200">
              {recData!.rankings.map((item: { rank: number; candidate: { _id: string; candidate_name?: string; candidate_email?: string }; score: number | null; reasoning?: string; tag?: string }) => (
                <li key={item.rank} className="py-3 first:pt-0">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <span className="font-medium text-gray-500 mr-2">#{item.rank}</span>
                      <Link
                        to={`/candidates/${item.candidate?._id ?? ''}`}
                        className="font-medium text-gray-900 hover:underline"
                      >
                        {item.candidate?.candidate_name ?? 'Unknown'}
                      </Link>
                      {item.candidate?.candidate_email && (
                        <span className="ml-2 text-sm text-gray-500">{item.candidate.candidate_email}</span>
                      )}
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
    </div>
  );
}
