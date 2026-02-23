/**
 * CV Upload page component
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function CVUploadPage() {
  const navigate = useNavigate();
  const [candidateName, setCandidateName] = useState('');
  const [candidateEmail, setCandidateEmail] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await api.post('/api/cv/process', formData);
      return response.data;
    },
    onSuccess: (data) => {
      setUploadSuccess(true);
      setError('');
      // Redirect to My Resumes after 2 seconds
      setTimeout(() => {
        navigate('/resumes');
      }, 2000);
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to upload CV. Please try again.');
      setUploadSuccess(false);
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setUploadSuccess(false);

    if (!file) {
      setError('Please select a CV file to upload.');
      return;
    }

    if (!candidateName || !candidateEmail) {
      setError('Please fill in all fields.');
      return;
    }

    const formData = new FormData();
    formData.append('candidate_name', candidateName);
    formData.append('candidate_email', candidateEmail);
    formData.append('cv_file', file);

    uploadMutation.mutate(formData);
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Upload Your CV</h1>

      <Card>
        <CardHeader>
          <CardTitle>Submit Your Resume</CardTitle>
          <CardDescription>
            Upload your CV and our AI will analyze it for matching job opportunities
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                {error}
              </div>
            )}

            {uploadSuccess && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
                CV uploaded successfully! Redirecting...
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="candidateName">Full Name</Label>
              <Input
                id="candidateName"
                type="text"
                placeholder="John Doe"
                value={candidateName}
                onChange={(e) => setCandidateName(e.target.value)}
                required
                disabled={uploadMutation.isPending}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="candidateEmail">Email</Label>
              <Input
                id="candidateEmail"
                type="email"
                placeholder="john@example.com"
                value={candidateEmail}
                onChange={(e) => setCandidateEmail(e.target.value)}
                required
                disabled={uploadMutation.isPending}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="cvFile">CV/Resume (PDF)</Label>
              <Input
                id="cvFile"
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                required
                disabled={uploadMutation.isPending}
              />
              <p className="text-sm text-gray-500">
                Accepted formats: PDF, DOC, DOCX (Max 10MB)
              </p>
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={uploadMutation.isPending || uploadSuccess}
            >
              {uploadMutation.isPending ? 'Uploading...' : 'Upload CV'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
