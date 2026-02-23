/**
 * Authentication hooks
 */

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authAPI } from '@/lib/api';
import { User, TokenResponse } from '@/lib/types';

export function useAuth() {
  const queryClient = useQueryClient();
  const [token, setToken] = useState<string | null>(
    localStorage.getItem('access_token')
  );

  // Listen for storage changes (e.g., from other tabs)
  useEffect(() => {
    const handleStorageChange = () => {
      setToken(localStorage.getItem('access_token'));
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const { data: user, isLoading, error } = useQuery<User>({
    queryKey: ['auth', 'user'],
    queryFn: async () => {
      const response = await authAPI.getCurrentUser();
      return response.data;
    },
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: !!token, // Only run query if token exists
  });

  const loginMutation = useMutation<TokenResponse, Error, { email: string; password: string }>({
    mutationFn: async ({ email, password }) => {
      const response = await authAPI.login(email, password);
      return response.data;
    },
    onSuccess: (data) => {
      localStorage.setItem('access_token', data.access_token);
      setToken(data.access_token); // Update local state
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
  });

  const registerMutation = useMutation<User, Error, {
    email: string;
    password: string;
    name: string;
    role: string;
  }>({
    mutationFn: async (data) => {
      const response = await authAPI.register(data);
      return response.data;
    },
    onSuccess: () => {
      // After successful registration, login automatically
      // Or redirect to login page
    },
  });

  const logout = () => {
    localStorage.removeItem('access_token');
    setToken(null); // Update local state
    queryClient.clear();
    window.location.href = '/login';
  };

  return {
    user,
    isLoading,
    error,
    isAuthenticated: !!user,
    login: async (credentials: { email: string; password: string }) => {
      // Wrapper that returns promise for backward compatibility
      return new Promise((resolve, reject) => {
        loginMutation.mutate(
          credentials,
          {
            onSuccess: (data) => resolve(data),
            onError: (error) => reject(error),
          }
        );
      });
    },
    loginAsync: loginMutation.mutateAsync,
    register: async (data: { email: string; password: string; name: string; role: string }) => {
      // Wrapper that returns promise for better error handling
      return new Promise((resolve, reject) => {
        registerMutation.mutate(
          data,
          {
            onSuccess: (responseData) => resolve(responseData),
            onError: (error) => reject(error),
          }
        );
      });
    },
    registerAsync: registerMutation.mutateAsync,
    logout,
    isLoggingIn: loginMutation.isPending,
    isRegistering: registerMutation.isPending,
  };
}
