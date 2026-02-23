/**
 * Main application layout
 */

import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

export function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link to="/" className="text-xl font-bold text-primary">
                AI HR Automation
              </Link>
            </div>

            <nav className="flex items-center gap-6">
              {user?.role === 'job_seeker' && (
                <>
                  <Link to="/jobs" className="text-gray-700 hover:text-primary">
                    Jobs
                  </Link>
                  <Link to="/resumes" className="text-gray-700 hover:text-primary">
                    My Resumes
                  </Link>
                </>
              )}

              {user?.role === 'hr_manager' && (
                <>
                  <Link to="/" className="text-gray-700 hover:text-primary">
                    Home
                  </Link>
                  <Link to="/jobs" className="text-gray-700 hover:text-primary">
                    Jobs
                  </Link>
                  <Link to="/candidates" className="text-gray-700 hover:text-primary">
                    Candidates
                  </Link>
                  <Link to="/batch" className="text-gray-700 hover:text-primary">
                    Batch
                  </Link>
                </>
              )}

              {user?.role === 'admin' && (
                <>
                  <Link to="/dashboard" className="text-gray-700 hover:text-primary">
                    Dashboard
                  </Link>
                  <Link to="/users" className="text-gray-700 hover:text-primary">
                    Users
                  </Link>
                  <Link to="/jobs" className="text-gray-700 hover:text-primary">
                    Jobs
                  </Link>
                  <Link to="/candidates" className="text-gray-700 hover:text-primary">
                    Candidates
                  </Link>
                  <Link to="/batch" className="text-gray-700 hover:text-primary">
                    Batch
                  </Link>
                  <Link to="/resumes" className="text-gray-700 hover:text-primary">
                    My Resumes
                  </Link>
                </>
              )}

              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-600">
                  {user?.name} ({user?.role})
                </span>
                <Button variant="outline" size="sm" onClick={handleLogout}>
                  Logout
                </Button>
              </div>
            </nav>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-600">
            © 2026 AI HR Automation. Powered by LangGraph and OpenAI.
          </p>
        </div>
      </footer>
    </div>
  );
}
