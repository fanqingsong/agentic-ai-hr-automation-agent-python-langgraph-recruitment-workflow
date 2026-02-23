/**
 * Home page component - role-based content
 */

import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/hooks/useAuth';
import { dashboardAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export function HomePage() {
  const { user } = useAuth();
  const isHR = user?.role === 'hr_manager' || user?.role === 'admin';

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const res = await dashboardAPI.getStats({ days: 30 });
      return res.data;
    },
    enabled: isHR,
  });

  if (isHR) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">
          Recruitment Dashboard
        </h1>

        {statsLoading ? (
          <p className="text-gray-500 mb-6">Loading stats...</p>
        ) : stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <Card>
              <CardHeader className="pb-1">
                <CardDescription>Total candidates</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold">{stats.total_candidates ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardDescription>Average score</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold">
                  {typeof stats.average_score === 'number' ? stats.average_score.toFixed(1) : '—'}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardDescription>High scorers (≥70)</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold">{stats.high_scorers_count ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardDescription>Successful evaluations</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold">{stats.successful_evaluations ?? 0}</p>
              </CardContent>
            </Card>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Link to="/jobs" className="block group">
            <Card className="h-full transition-shadow hover:shadow-lg">
              <CardHeader>
                <CardTitle className="group-hover:text-primary transition-colors">
                  Jobs
                </CardTitle>
                <CardDescription>
                  View and manage job postings
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 mb-4">
                  Browse current job openings. Use jobs when filtering candidates or running batch processing.
                </p>
                <Button variant="outline" className="w-full">
                  View Jobs
                </Button>
              </CardContent>
            </Card>
          </Link>

          <Link to="/candidates" className="block group">
            <Card className="h-full transition-shadow hover:shadow-lg">
              <CardHeader>
                <CardTitle className="group-hover:text-primary transition-colors">
                  Candidates
                </CardTitle>
                <CardDescription>
                  View and filter all candidates
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 mb-4">
                  See all evaluated candidates, filter by job or score, and export data to CSV or Excel.
                </p>
                <Button variant="outline" className="w-full">
                  View Candidates
                </Button>
              </CardContent>
            </Card>
          </Link>

          <Link to="/batch" className="block group">
            <Card className="h-full transition-shadow hover:shadow-lg">
              <CardHeader>
                <CardTitle className="group-hover:text-primary transition-colors">
                  Batch Processing
                </CardTitle>
                <CardDescription>
                  Process multiple CVs at once
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 mb-4">
                  Select a job and process multiple resumes in batch. Get evaluation results and export.
                </p>
                <Button variant="outline" className="w-full">
                  Batch Process
                </Button>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>
    );
  }

  // Job seeker (and default) view
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">
        AI HR Automation Dashboard
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Link to="/resumes" className="block group">
          <Card className="h-full transition-shadow hover:shadow-lg">
            <CardHeader>
              <CardTitle className="group-hover:text-primary transition-colors">
                My Resumes
              </CardTitle>
              <CardDescription>
                View your uploaded resumes or submit a new one for AI analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">
                Manage your resumes: view past uploads and download your CV, or upload a new one for AI-powered analysis.
              </p>
              <Button variant="outline" className="w-full">
                My Resumes
              </Button>
            </CardContent>
          </Card>
        </Link>

        <Link to="/jobs" className="block group">
          <Card className="h-full transition-shadow hover:shadow-lg">
            <CardHeader>
              <CardTitle className="group-hover:text-primary transition-colors">
                Browse Jobs
              </CardTitle>
              <CardDescription>
                View available job openings
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 mb-4">
                Explore current job openings and find positions that match your skills and experience.
              </p>
              <Button variant="outline" className="w-full">
                View Jobs
              </Button>
            </CardContent>
          </Card>
        </Link>

        <Card className="h-full">
          <CardHeader>
            <CardTitle>AI-Powered Matching</CardTitle>
            <CardDescription>
              Intelligent skill analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">
              Our AI analyzes your CV and matches your skills with job requirements automatically.
            </p>
          </CardContent>
        </Card>

        <Card className="h-full">
          <CardHeader>
            <CardTitle>Recruitment Analytics</CardTitle>
            <CardDescription>
              Data-driven insights
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">
              Get detailed analytics on recruitment metrics and candidate evaluations.
            </p>
          </CardContent>
        </Card>

        <Card className="h-full">
          <CardHeader>
            <CardTitle>Smart CV Processing</CardTitle>
            <CardDescription>
              Automated extraction
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">
              Extract key information from CVs including education, experience, and technical skills.
            </p>
          </CardContent>
        </Card>

        <Card className="h-full">
          <CardHeader>
            <CardTitle>Candidate Evaluation</CardTitle>
            <CardDescription>
              Comprehensive scoring
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-gray-600">
              Get AI-powered candidate evaluations with detailed scoring and recommendations.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
