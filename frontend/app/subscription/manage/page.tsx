'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '../../../lib/auth-context';
import axios from 'axios';

export default function ManageSubscriptionPage() {
  const { user, isAuthenticated, isLoading, getAccessToken, refreshUserData } = useAuth();
  const router = useRouter();
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/auth/login');
    } else if (isAuthenticated) {
      // Refresh user data to ensure we have the latest subscription info
      refreshUserData();
    }
  }, [isLoading, isAuthenticated, router, refreshUserData]);
  
  const handleCancelSubscription = async () => {
    if (!confirm('Are you sure you want to cancel your subscription? You will lose access to premium features at the end of your current billing period.')) {
      return;
    }
    
    setIsProcessing(true);
    setError('');
    setSuccess('');
    
    try {
      const token = await getAccessToken();
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/subscriptions/cancel`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      
      setSuccess('Your subscription has been canceled. You will have access until the end of your current billing period.');
    } catch (err) {
      console.error('Error canceling subscription:', err);
      setError('Failed to cancel subscription. Please try again or contact support.');
    } finally {
      setIsProcessing(false);
    }
  };
  
  const handleResumeSubscription = async () => {
    setIsProcessing(true);
    setError('');
    setSuccess('');
    
    try {
      const token = await getAccessToken();
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/subscriptions/resume`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      
      setSuccess('Your subscription has been resumed successfully.');
    } catch (err) {
      console.error('Error resuming subscription:', err);
      setError('Failed to resume subscription. Please try again or contact support.');
    } finally {
      setIsProcessing(false);
    }
  };
  
  const handleUpdatePaymentMethod = async () => {
    setIsProcessing(true);
    setError('');
    
    try {
      const token = await getAccessToken();
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/subscriptions/update-payment-session`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      
      // Redirect to Stripe portal
      if (response.data && response.data.url) {
        window.location.href = response.data.url;
      } else {
        throw new Error('No portal URL returned');
      }
    } catch (err) {
      console.error('Error creating portal session:', err);
      setError('Failed to access payment settings. Please try again or contact support.');
      setIsProcessing(false);
    }
  };
  
  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }
  
  if (!user) {
    return null;
  }
  
  const subscription = user.subscription;
  const hasActiveSubscription = !!subscription;
  const isCanceled = subscription?.status === 'canceled' || subscription?.cancel_at_period_end;
  const planName = subscription?.plan?.name || 'Free Plan';
  
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="px-4 py-5 sm:px-6">
          <h1 className="text-2xl font-bold text-gray-900">Manage Subscription</h1>
          <p className="mt-1 max-w-2xl text-sm text-gray-500">
            View and manage your subscription details
          </p>
        </div>
        
        {error && (
          <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-4 mx-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}
        
        {success && (
          <div className="bg-green-50 border-l-4 border-green-400 p-4 mb-4 mx-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-green-700">{success}</p>
              </div>
            </div>
          </div>
        )}
        
        <div className="px-4 py-5 sm:p-6">
          <div className="bg-gray-50 p-6 rounded-lg border border-gray-200">
            <div className="flex flex-col md:flex-row md:justify-between md:items-center">
              <div>
                <h2 className="text-lg font-medium text-gray-900">Current Plan</h2>
                <div className="mt-2 flex items-center">
                  <span className="text-2xl font-bold text-indigo-600">{planName}</span>
                  {hasActiveSubscription && (
                    <span className={`ml-3 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      isCanceled ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'
                    }`}>
                      {isCanceled ? 'Canceling' : 'Active'}
                    </span>
                  )}
                </div>
                
                {hasActiveSubscription && (
                  <div className="mt-2 text-sm text-gray-500">
                    {isCanceled ? (
                      <p>Your subscription will end on {new Date(subscription.current_period_end).toLocaleDateString()}</p>
                    ) : (
                      <p>Next billing date: {new Date(subscription.current_period_end).toLocaleDateString()}</p>
                    )}
                  </div>
                )}
              </div>
              
              <div className="mt-4 md:mt-0">
                {!hasActiveSubscription && (
                  <Link
                    href="/subscription/plans"
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Upgrade to Premium
                  </Link>
                )}
                {hasActiveSubscription && planName !== 'Enterprise' && !isCanceled && (
                  <Link
                    href="/subscription/plans"
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Upgrade Plan
                  </Link>
                )}
              </div>
            </div>
            
            {hasActiveSubscription && (
              <div className="mt-6 border-t border-gray-200 pt-6">
                <h3 className="text-sm font-medium text-gray-900">Subscription Management</h3>
                <div className="mt-4 flex flex-col space-y-3 sm:flex-row sm:space-y-0 sm:space-x-3">
                  <button
                    onClick={handleUpdatePaymentMethod}
                    disabled={isProcessing}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                  >
                    Update Payment Method
                  </button>
                  
                  {isCanceled ? (
                    <button
                      onClick={handleResumeSubscription}
                      disabled={isProcessing}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    >
                      {isProcessing ? 'Processing...' : 'Resume Subscription'}
                    </button>
                  ) : (
                    <button
                      onClick={handleCancelSubscription}
                      disabled={isProcessing}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                    >
                      {isProcessing ? 'Processing...' : 'Cancel Subscription'}
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
          
          <div className="mt-8">
            <h3 className="text-lg font-medium text-gray-900">Billing History</h3>
            {hasActiveSubscription ? (
              <div className="mt-4 bg-white shadow overflow-hidden sm:rounded-md">
                <ul className="divide-y divide-gray-200">
                  {user.invoices && user.invoices.length > 0 ? (
                    user.invoices.map((invoice) => (
                      <li key={invoice.id}>
                        <div className="px-4 py-4 sm:px-6">
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium text-indigo-600 truncate">
                              {invoice.description || 'Subscription Payment'}
                            </p>
                            <div className="ml-2 flex-shrink-0 flex">
                              <p className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                invoice.paid ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                              }`}>
                                {invoice.paid ? 'Paid' : 'Pending'}
                              </p>
                            </div>
                          </div>
                          <div className="mt-2 sm:flex sm:justify-between">
                            <div className="sm:flex">
                              <p className="flex items-center text-sm text-gray-500">
                                ${typeof invoice.amount_paid === 'number' ? (invoice.amount_paid / 100).toFixed(2) : '0.00'} USD
                              </p>
                            </div>
                            <div className="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                              <p>
                                {new Date(typeof invoice.created === 'number' ? invoice.created * 1000 : Date.now()).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                        </div>
                      </li>
                    ))
                  ) : (
                    <li>
                      <div className="px-4 py-4 sm:px-6 text-center text-gray-500">
                        No billing history available
                      </div>
                    </li>
                  )}
                </ul>
              </div>
            ) : (
              <p className="mt-4 text-gray-500">
                Billing history will be available once you subscribe to a plan.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
} 