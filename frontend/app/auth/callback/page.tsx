'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth0 } from '@auth0/auth0-react';

export default function Callback() {
  const router = useRouter();
  const { isAuthenticated, isLoading, error } = useAuth0();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        // Redirect to home page or the page they were trying to access
        router.push('/');
      } else if (error) {
        // Redirect to login page with error
        router.push(`/auth/login?error=${encodeURIComponent(error.message)}`);
      }
    }
  }, [isAuthenticated, isLoading, error, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-2xl font-semibold mb-4">Logging you in...</h1>
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
      </div>
    </div>
  );
} 