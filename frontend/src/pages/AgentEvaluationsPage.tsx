/**
 * Agent Evals page — Langfuse observability + agent evaluation control panel.
 *
 * Shows integration status, recent traces with their evaluation scores, and a
 * button to replay evaluators (heuristics always; LLM-as-judge opt-in) over
 * recent traces. HR manager / admin only (enforced by the backend routes).
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { agentEvaluationsAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const TRACE_NAME_OPTIONS = ['', 'cv-extraction', 'job-evaluation', 'hr_explorer'];

function formatLatency(ms: number | null): string {
  if (ms == null) return '—';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

function scoreColor(value: number): string {
  if (value >= 0.8) return 'bg-green-100 text-green-800';
  if (value >= 0.5) return 'bg-yellow-100 text-yellow-800';
  return 'bg-red-100 text-red-800';
}

export function AgentEvaluationsPage() {
  const queryClient = useQueryClient();
  const [limit, setLimit] = useState(50);
  const [traceName, setTraceName] = useState('');
  const [useLlmJudge, setUseLlmJudge] = useState(false);

  const { data: status } = useQuery({
    queryKey: ['agent-evaluations-status'],
    queryFn: async () => (await agentEvaluationsAPI.getStatus()).data,
  });

  const tracesQuery = useQuery({
    queryKey: ['agent-evaluations-traces', limit, traceName],
    queryFn: async () =>
      (
        await agentEvaluationsAPI.getTraces({
          limit,
          name: traceName || undefined,
        })
      ).data,
    enabled: !!status?.langfuse_enabled,
    refetchInterval: 30_000,
  });

  const runMutation = useMutation({
    mutationFn: async () =>
      (
        await agentEvaluationsAPI.run({
          limit,
          trace_name: traceName || null,
          use_llm_judge: useLlmJudge,
        })
      ).data,
    onSuccess: () => {
      // Scores were written back to the traces — refresh the table.
      queryClient.invalidateQueries({ queryKey: ['agent-evaluations-traces'] });
    },
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Agent Evals</h1>
      <p className="text-gray-600 mb-6">
        Langfuse observability: LLM/workflow traces and automatic evaluation scores for the CV,
        job-evaluation and explorer-agent runs.
      </p>

      {/* Status */}
      <Card className="mb-6">
        <CardHeader className="pb-2">
          <CardTitle>Langfuse integration</CardTitle>
          <CardDescription>Self-hosted observability backend status</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3 text-sm">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-medium ${
              status?.langfuse_enabled
                ? status.langfuse_reachable
                  ? 'bg-green-100 text-green-800'
                  : 'bg-yellow-100 text-yellow-800'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            {status?.langfuse_enabled
              ? status.langfuse_reachable
                ? 'enabled · reachable'
                : 'enabled · unreachable'
              : 'disabled'}
          </span>
          {status?.langfuse_host && (
            <a
              href={status.langfuse_host}
              target="_blank"
              rel="noreferrer"
              className="text-primary underline-offset-2 hover:underline"
            >
              Open Langfuse UI ({status.langfuse_host})
            </a>
          )}
          <span className="text-gray-500">
            LLM-as-judge default: {status?.llm_judge_default ? 'on' : 'off'}
          </span>
          {status?.trace_evaluators && (
            <span className="text-gray-500">
              Evaluators:{' '}
              {Object.entries(status.trace_evaluators)
                .map(([name, evals]) => `${name} (${evals.length})`)
                .join(' · ')}
            </span>
          )}
        </CardContent>
      </Card>

      {/* Run controls */}
      <Card className="mb-6">
        <CardHeader className="pb-2">
          <CardTitle>Run batch evaluation</CardTitle>
          <CardDescription>
            Replays heuristic evaluators over the most recent traces and writes scores back to
            Langfuse. Enable the LLM judge for quality scoring of candidate evaluations and agent
            answers (extra LLM cost).
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-sm text-gray-700">
            Trace limit
            <input
              type="number"
              min={1}
              max={100}
              value={limit}
              onChange={(e) => setLimit(Math.max(1, Math.min(100, Number(e.target.value) || 1)))}
              className="w-24 rounded-md border border-gray-300 px-2 py-1.5"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm text-gray-700">
            Trace name
            <select
              value={traceName}
              onChange={(e) => setTraceName(e.target.value)}
              className="rounded-md border border-gray-300 px-2 py-1.5"
            >
              {TRACE_NAME_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt || 'all traces'}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700 pb-2">
            <input
              type="checkbox"
              checked={useLlmJudge}
              onChange={(e) => setUseLlmJudge(e.target.checked)}
              className="h-4 w-4"
            />
            Use LLM-as-judge
          </label>
          <Button onClick={() => runMutation.mutate()} disabled={runMutation.isPending}>
            {runMutation.isPending ? 'Evaluating…' : 'Run evaluation'}
          </Button>
          {runMutation.data && (
            <span className="text-sm text-gray-600">
              fetched {runMutation.data.fetched} · evaluated {runMutation.data.evaluated} · skipped{' '}
              {runMutation.data.skipped} · scores written {runMutation.data.scores_written}
              {runMutation.data.llm_judged > 0 && ` · LLM-judged ${runMutation.data.llm_judged}`}
            </span>
          )}
          {runMutation.isError && (
            <span className="text-sm text-red-600">
              {(runMutation.error as any)?.response?.data?.detail ?? 'Evaluation run failed'}
            </span>
          )}
        </CardContent>
      </Card>

      {/* Traces table */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Recent traces</CardTitle>
          <CardDescription>
            {tracesQuery.isLoading
              ? 'Loading…'
              : `${tracesQuery.data?.count ?? 0} traces (auto-refreshes every 30s)`}
          </CardDescription>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {tracesQuery.isError && (
            <p className="text-sm text-red-600">
              {(tracesQuery.error as any)?.response?.data?.detail ??
                'Failed to load traces. Is the Langfuse stack running?'}
            </p>
          )}
          {tracesQuery.data && tracesQuery.data.traces.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-2 pr-4 font-medium">Trace</th>
                  <th className="py-2 pr-4 font-medium">Time</th>
                  <th className="py-2 pr-4 font-medium">Latency</th>
                  <th className="py-2 pr-4 font-medium">User / Session</th>
                  <th className="py-2 pr-4 font-medium">Scores</th>
                </tr>
              </thead>
              <tbody>
                {tracesQuery.data.traces.map((t) => (
                  <tr key={t.id} className="border-b last:border-0 align-top">
                    <td className="py-2 pr-4">
                      <div className="font-medium text-gray-900">{t.name ?? '—'}</div>
                      {t.tags.length > 0 && (
                        <div className="mt-0.5 flex flex-wrap gap-1">
                          {t.tags.map((tag) => (
                            <span
                              key={tag}
                              className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-gray-600">
                      {t.timestamp ? new Date(t.timestamp).toLocaleString() : '—'}
                    </td>
                    <td className="py-2 pr-4 text-gray-600">{formatLatency(t.latency)}</td>
                    <td className="py-2 pr-4 text-gray-600">
                      <div>{t.user_id ?? '—'}</div>
                      <div className="text-xs text-gray-400">{t.session_id ?? ''}</div>
                    </td>
                    <td className="py-2 pr-4">
                      {t.scores.length === 0 ? (
                        <span className="text-gray-400">no scores yet</span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {t.scores.map((s, i) => (
                            <span
                              key={`${s.name}-${i}`}
                              title={s.comment ?? undefined}
                              className={`rounded px-1.5 py-0.5 text-xs font-medium ${scoreColor(
                                s.value ?? 0
                              )}`}
                            >
                              {s.name}: {s.value}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {tracesQuery.data && tracesQuery.data.traces.length === 0 && (
            <p className="text-sm text-gray-500">
              No traces yet. Upload a CV, run a job evaluation, or chat with the HR explorer agent —
              each run creates a trace.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default AgentEvaluationsPage;
