/**
 * Authentication hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authAPI } from '@/lib/api';
import { User, TokenResponse } from '@/lib/types';

export function useAuth() {
  const queryClient = useQueryClient();

  const { data: user, isLoading, error } = useQuery<User>({
    queryKey: ['auth', 'user'],
    queryFn: async () => {
      const response = await authAPI.getCurrentUser();
      return response.data;
    },
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const loginMutation = useMutation<TokenResponse, Error, { email: string; password: string }>({
    mutationFn: async ({ email, password }) => {
      const response = await authAPI.login(email, password);
      return response.data;
    },
    onSuccess: (data) => {
      localStorage.setItem('access_token', data.access_token);
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
    queryClient.clear();
    window.location.href = '/login';
  };

  return {
    user,
    isLoading,
    error,
    isAuthenticated: !!user,
    login: loginMutation.mutate,
    loginAsync: loginMutation.mutateAsync,
    register: registerMutation.mutate,
    registerAsync: registerMutation.mutateAsync,
    logout,
    isLoggingIn: loginMutation.isPending,
    isRegistering: registerMutation.isPending,
  };
}
