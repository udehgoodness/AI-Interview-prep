'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../../lib/auth-context';
import axios from 'axios';
import PlanFeaturesList from '../../../components/PlanFeatures';

// Add API base URL configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface PlanFeatures {
  code_challenges?: boolean;
  feedback_detail?: string;
  video_interviews?: boolean;
  voice_interviews?: boolean;
  text_interviews?: boolean;
  interviews_per_month?: number;
  interview_duration_max?: number;
  [key: string]: any;
}

interface Plan {
  id: string;
  name: string;
  description: string;
  price: number;
  interval: string;
  features: string[] | PlanFeatures;
  isPopular?: boolean;
}

// Default plans that match exactly what's in the database
const defaultPlans: Plan[] = [
  {
    id: '12',
    name: 'Free',
    description: 'Get started with basic interview preparation',
    price: 0,
    interval: 'month',
    features: {
      support: "community",
      code_challenges: false,
      feedback_detail: "basic",
      text_interviews: true,
      video_interviews: false,
      voice_interviews: false,
      interviews_per_month: 3,
      interview_duration_max: 15,
      question_library_access: "limited"
    }
  },
  {
    id: '13',
    name: 'Basic',
    description: 'Perfect for individuals preparing for job interviews',
    price: 9.99,
    interval: 'month',
    features: {
      support: "email",
      code_challenges: true,
      feedback_detail: "detailed",
      text_interviews: true,
      video_interviews: false,
      voice_interviews: true,
      interviews_per_month: 10,
      interview_duration_max: 30,
      question_library_access: "full"
    }
  },
  {
    id: '14',
    name: 'Professional',
    description: 'For serious job seekers who want comprehensive preparation',
    price: 19.99,
    interval: 'month',
    features: {
      support: "priority_email",
      cv_review: true,
      code_challenges: true,
      feedback_detail: "comprehensive",
      text_interviews: true,
      video_interviews: true,
      voice_interviews: true,
      interviews_per_month: -1,
      performance_analytics: true,
      interview_duration_max: 60,
      question_library_access: "full",
      personalized_suggestions: true
    },
    isPopular: true
  },
  {
    id: '15',
    name: 'Enterprise',
    description: 'For teams and organizations preparing multiple candidates',
    price: 49.99,
    interval: 'month',
    features: {
      support: "24/7",
      cv_review: true,
      code_challenges: true,
      feedback_detail: "comprehensive",
      team_management: true,
      text_interviews: true,
      custom_templates: true,
      video_interviews: true,
      voice_interviews: true,
      bulk_user_management: true,
      interviews_per_month: -1,
      performance_analytics: true,
      interview_duration_max: 120,
      question_library_access: "full",
      personalized_suggestions: true,
      dedicated_account_manager: true
    }
  }
];

export default function SubscriptionPlansPage() {
  const { user, isAuthenticated, isLoading, getAccessToken } = useAuth();
  const router = useRouter();
  
  const [apiPlans, setApiPlans] = useState<Plan[]>([]);
  const [isLoadingPlans, setIsLoadingPlans] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  const [lastFetchTime, setLastFetchTime] = useState<number | null>(null);
  
  // Load plans and last fetch time from localStorage on initial render
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedPlans = localStorage.getItem('subscription_plans');
      const storedLastFetchTime = localStorage.getItem('plans_last_fetch_time');
      
      if (storedPlans) {
        try {
          const parsedPlans = JSON.parse(storedPlans);
          setApiPlans(parsedPlans);
        } catch (e) {
          console.error('Error parsing stored plans:', e);
        }
      }
      
      if (storedLastFetchTime) {
        try {
          const parsedTime = parseInt(storedLastFetchTime);
          setLastFetchTime(parsedTime);
        } catch (e) {
          console.error('Error parsing stored fetch time:', e);
        }
      }
    }
  }, []);
  
  useEffect(() => {
    // Check if we need to fetch plans from API
    const shouldFetchPlans = () => {
      // If we've never fetched plans, fetch them
      if (!lastFetchTime) return true;
      
      // If it's been more than 1 hour since we last fetched plans, fetch them again
      const oneHour = 60 * 60 * 1000; // 1 hour in milliseconds
      return Date.now() - lastFetchTime > oneHour;
    };
    
    if (shouldFetchPlans()) {
      fetchPlans();
    }
  }, [lastFetchTime]);
  
  const fetchPlans = async () => {
    try {
      setIsLoadingPlans(true);
      const response = await axios.get(
        `${API_BASE_URL}/api/subscriptions/plans`
      );
      if (response.data && response.data.length > 0) {
        // Transform API response to match our Plan interface
        const transformedPlans = response.data.map((plan: any) => ({
          id: plan.id.toString(),
          name: plan.name,
          description: plan.description,
          price: parseFloat(plan.price_monthly),
          interval: 'month',
          features: plan.features,
          isPopular: plan.name === 'Professional' // Mark Professional plan as popular
        }));
        
        setApiPlans(transformedPlans);
        
        // Store plans and fetch time in localStorage
        if (typeof window !== 'undefined') {
          localStorage.setItem('subscription_plans', JSON.stringify(transformedPlans));
          const now = Date.now();
          localStorage.setItem('plans_last_fetch_time', now.toString());
          setLastFetchTime(now);
        }
        
        console.log('Successfully loaded plans from API:', transformedPlans.length);
      } else {
        console.log('No plans returned from API, using default plans');
      }
    } catch (err) {
      console.error('Error fetching plans:', err);
      // Don't set error - we'll use default plans instead
    } finally {
      setIsLoadingPlans(false);
    }
  };
  
  const handleSelectPlan = (planId: string) => {
    setSelectedPlan(planId);
  };
  
  const handleSubscribe = async () => {
    if (!selectedPlan) return;
    
    if (!isAuthenticated) {
      // Redirect to login page with redirect back to plans page
      router.push(`/auth/login?redirect=/subscription/plans`);
      return;
    }
    
    setIsProcessing(true);
    setError('');
    
    try {
      const token = await getAccessToken();
      
      // Find the selected plan
      const plans = apiPlans.length > 0 ? apiPlans : defaultPlans;
      const selectedPlanObj = plans.find(p => p.id === selectedPlan);
      if (!selectedPlanObj) {
        throw new Error('Selected plan not found');
      }
      
      // For API plans, we need to use the numeric ID
      const planIdForApi = parseInt(selectedPlan);
      
      const response = await axios.post(
        `${API_BASE_URL}/api/subscriptions/checkout`,
        { 
          plan_id: planIdForApi,
          is_yearly: false // Default to monthly for now
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );
      
      // Redirect to Stripe checkout
      if (response.data && response.data.url) {
        window.location.href = response.data.url;
      } else {
        throw new Error('No checkout URL returned');
      }
    } catch (err) {
      console.error('Error creating checkout session:', err);
      setError('Failed to initiate checkout. Please try again or contact support.');
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Choose which plans to display based on whether we have API plans
  const displayPlans = apiPlans.length > 0 ? apiPlans : defaultPlans;
  
  // Get the user's current plan
  const currentPlanName = user?.subscription?.plan?.name || 'Free';
  
  // Function to determine if a plan is an upgrade from the current plan
  const isUpgrade = (planName: string) => {
    const planOrder = ['Free', 'Basic', 'Professional', 'Enterprise'];
    const currentPlanIndex = planOrder.indexOf(currentPlanName);
    const planIndex = planOrder.indexOf(planName);
    
    return planIndex > currentPlanIndex;
  };
  
  // Flag to show if we're loading plans
  const isLoadingDisplay = isLoadingPlans && apiPlans.length === 0 && !lastFetchTime;
  
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center">
        <h1 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
          Choose Your Plan
        </h1>
        <p className="mt-4 text-xl text-gray-500">
          Select the plan that best fits your interview preparation needs
        </p>
      </div>
      
      {error && (
        <div className="max-w-3xl mx-auto mt-8">
          <div className="bg-red-50 border-l-4 border-red-400 p-4">
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
        </div>
      )}
      
      {isLoadingDisplay ? (
        <div className="mt-12 text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-600"></div>
          <p className="mt-4 text-gray-600">Loading subscription plans...</p>
        </div>
      ) : (
        <div className="mt-12 space-y-12 lg:space-y-0 lg:grid lg:grid-cols-3 lg:gap-x-8">
          {displayPlans.map((plan) => (
            <div 
              key={plan.id}
              data-popular={plan.isPopular || false}
              className={`relative p-8 bg-white border-2 rounded-lg shadow-sm flex flex-col pricing-card ${
                selectedPlan === plan.id 
                  ? 'border-indigo-500 ring-2 ring-indigo-500' 
                  : plan.isPopular 
                    ? 'border-indigo-500' 
                    : 'border-gray-200'
              } ${plan.isPopular ? 'lg:scale-105 z-10' : ''}`}
            >
              <div className="flex-1">
                <h3 className="text-xl font-semibold text-gray-900 flex items-center">
                  {plan.name}
                  {plan.isPopular && (
                    <span className="ml-3 inline-flex items-center px-3 py-1 rounded-full text-sm font-bold bg-indigo-600 text-white">
                      MOST POPULAR
                    </span>
                  )}
                </h3>
                
                <p className="mt-4 flex items-baseline text-gray-900">
                  <span className="text-4xl font-extrabold tracking-tight">${plan.price}</span>
                  <span className="ml-1 text-xl font-semibold">/{plan.interval}</span>
                </p>
                
                <p className="mt-6 text-gray-500">{plan.description}</p>
                
                <PlanFeaturesList planName={plan.name} features={plan.features} />
              </div>
              
              {plan.name === currentPlanName ? (
                <div className="mt-8 block w-full py-3 px-6 border border-transparent rounded-md text-center font-medium bg-green-100 text-green-800">
                  Current Plan
                </div>
              ) : isUpgrade(plan.name) ? (
                <button
                  onClick={() => handleSelectPlan(plan.id)}
                  className={`mt-8 block w-full py-3 px-6 border border-transparent rounded-md text-center font-medium ${
                    selectedPlan === plan.id
                      ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                      : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
                  }`}
                >
                  {selectedPlan === plan.id ? 'Selected' : 'Upgrade'}
                </button>
              ) : (
                <button
                  onClick={() => handleSelectPlan(plan.id)}
                  className={`mt-8 block w-full py-3 px-6 border border-transparent rounded-md text-center font-medium ${
                    selectedPlan === plan.id
                      ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                      : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
                  }`}
                >
                  {selectedPlan === plan.id ? 'Selected' : 'Select Plan'}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
      
      <div className="mt-10 text-center">
        <button
          onClick={handleSubscribe}
          disabled={!selectedPlan || isProcessing}
          className={`inline-flex items-center px-6 py-3 border border-transparent rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
            !selectedPlan || isProcessing ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {isProcessing ? 'Processing...' : isAuthenticated ? 'Subscribe Now' : 'Sign In to Subscribe'}
        </button>
        <p className="mt-4 text-sm text-gray-500">
          You can cancel or change your subscription at any time.
        </p>
      </div>
    </div>
  );
} 