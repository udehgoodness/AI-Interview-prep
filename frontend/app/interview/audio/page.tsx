'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AudioInterviewRedirect() {
  const router = useRouter();
  
  useEffect(() => {
    // Redirect to the interview setup page
    router.push('/interview/setup');
  }, [router]);
  
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="bg-white rounded-lg shadow-lg p-6 md:p-8 text-center">
        <h1 className="text-3xl font-bold mb-6">Redirecting...</h1>
        <p className="mb-6">The audio interview feature has been integrated into the main interview experience.</p>
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
      </div>
    </div>
  );
} 