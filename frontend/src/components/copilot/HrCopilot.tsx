/**
 * CopilotKit shell: wraps authenticated HR/admin pages with the provider
 * and mounts the right-hand CopilotSidebar.
 */

import { CopilotKit, useCopilotReadable, useDefaultTool } from '@copilotkit/react-core';
import { CopilotSidebar } from '@copilotkit/react-ui';
import '@copilotkit/react-ui/styles.css';
import { useAuth } from '@/hooks/useAuth';

function ToolCallCard({
  name,
  status,
  args,
  result,
}: {
  name?: string;
  status?: string;
  args?: unknown;
  result?: unknown;
}) {
  return (
    <details className="my-2 rounded border border-gray-200 bg-gray-50 p-2 text-xs">
      <summary className="cursor-pointer font-medium text-gray-800">
        {status === 'complete' ? `Tool: ${name}` : `Calling ${name}…`}
      </summary>
      <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-[11px] text-gray-600">
        {JSON.stringify({ args, result }, null, 2)}
      </pre>
    </details>
  );
}

function ExplorerToolRenderer() {
  useDefaultTool({
    render: ({ name, status, args, result }) => (
      <ToolCallCard name={name} status={status} args={args} result={result} />
    ),
  });
  return null;
}

function GlobalReadableContext() {
  const { user } = useAuth();
  useCopilotReadable({
    description: 'Current authenticated HR user',
    value: {
      name: user?.name,
      email: user?.email,
      role: user?.role,
    },
  });
  return null;
}

function HrCopilotSidebar() {
  return (
    <>
      <GlobalReadableContext />
      <ExplorerToolRenderer />
      <CopilotSidebar
        defaultOpen={false}
        clickOutsideToClose
        labels={{
          title: 'HR Explorer',
          initial:
            'Ask me to explore candidates and jobs across MongoDB, vector search, and the knowledge graph. I am read-only.',
        }}
      />
    </>
  );
}

function isHrRole(role?: string) {
  return role === 'hr_manager' || role === 'admin';
}

export function HrCopilotProvider({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated || !isHrRole(user?.role)) {
    return <>{children}</>;
  }

  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      agent="hr_explorer"
      // Multi-route FastAPI runtime (/info + /agent/:id/run). v1 defaults to
      // single-endpoint, which POSTs {method:"info"} to the AG-UI run path → 422.
      useSingleEndpoint={false}
      headers={() => {
        const token = localStorage.getItem('access_token');
        const h: Record<string, string> = {};
        if (token) h.Authorization = `Bearer ${token}`;
        return h;
      }}
    >
      {children}
      <HrCopilotSidebar />
    </CopilotKit>
  );
}

/** Inject page-level context the agent can read without the user pasting IDs. */
export function CopilotPageContext({
  description,
  value,
}: {
  description: string;
  value: unknown;
}) {
  const { user } = useAuth();
  if (!isHrRole(user?.role)) {
    return null;
  }
  return <CopilotPageContextInner description={description} value={value} />;
}

function CopilotPageContextInner({
  description,
  value,
}: {
  description: string;
  value: unknown;
}) {
  useCopilotReadable({ description, value });
  return null;
}
