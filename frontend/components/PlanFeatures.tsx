'use client';

import React from 'react';

interface PlanFeatures {
  code_challenges?: boolean;
  feedback_detail?: string;
  video_interviews?: boolean;
  voice_interviews?: boolean;
  text_interviews?: boolean;
  interviews_per_month?: number;
  interview_duration_max?: number;
  cv_review?: boolean;
  performance_analytics?: boolean;
  personalized_suggestions?: boolean;
  team_management?: boolean;
  bulk_user_management?: boolean;
  custom_templates?: boolean;
  dedicated_account_manager?: boolean;
  support?: string;
  question_library_access?: string;
  [key: string]: any;
}

interface PlanFeaturesProps {
  planName: string;
  features: PlanFeatures | string[];
}

const PlanFeaturesList: React.FC<PlanFeaturesProps> = ({ planName, features }) => {
  // If features is an array of strings, render them directly
  if (Array.isArray(features)) {
    return (
      <ul className="mt-6 space-y-4">
        {features.map((feature, index) => (
          <li key={index} className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="ml-3 text-base text-gray-700">{feature}</p>
          </li>
        ))}
      </ul>
    );
  }

  // For object-based features, render them based on the plan
  return (
    <ul className="mt-6 space-y-4">
      {/* For Professional plan, show it inherits from Basic */}
      {planName === 'Professional' && (
        <li className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700 font-medium">Everything in Basic plan, plus:</p>
        </li>
      )}
      
      {/* For Enterprise plan, show it inherits from Professional */}
      {planName === 'Enterprise' && (
        <li className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700 font-medium">Everything in Professional plan, plus:</p>
        </li>
      )}
      
      {/* Render specific features based on plan */}
      {renderPlanSpecificFeatures(planName, features)}
    </ul>
  );
};

const renderPlanSpecificFeatures = (planName: string, features: PlanFeatures) => {
  const featureItems = [];
  
  // Free and Basic plans show all their features
  if (planName === 'Free' || planName === 'Basic') {
    // Interviews per month
    if (features.interviews_per_month !== undefined) {
      featureItems.push(
        <li key="interviews" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">
            {features.interviews_per_month === -1 
              ? 'Unlimited AI-powered mock interviews' 
              : `${features.interviews_per_month} AI-powered mock interviews per month`}
          </p>
        </li>
      );
    }
    
    // Interview duration
    if (features.interview_duration_max !== undefined) {
      featureItems.push(
        <li key="duration" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">
            Up to {features.interview_duration_max} minute interviews
          </p>
        </li>
      );
    }
    
    // Feedback detail
    if (features.feedback_detail) {
      let feedbackText = '';
      if (features.feedback_detail === 'basic') {
        feedbackText = 'Basic feedback';
      } else if (features.feedback_detail === 'detailed') {
        feedbackText = 'Detailed feedback and analysis';
      } else if (features.feedback_detail === 'comprehensive') {
        feedbackText = 'Comprehensive feedback and analysis';
      }
      
      featureItems.push(
        <li key="feedback" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">{feedbackText}</p>
        </li>
      );
    }
    
    // Interview modes
    if (features.text_interviews) {
      featureItems.push(
        <li key="text" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Text interview mode</p>
        </li>
      );
    }
    
    if (features.voice_interviews) {
      featureItems.push(
        <li key="voice" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Voice interview mode</p>
        </li>
      );
    }
    
    // Code challenges
    if (features.code_challenges) {
      featureItems.push(
        <li key="code" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Code challenges included</p>
        </li>
      );
    }
    
    // Support level
    if (features.support) {
      let supportText = '';
      if (features.support === 'community') {
        supportText = 'Community support';
      } else if (features.support === 'email') {
        supportText = 'Email support';
      } else if (features.support === 'priority_email') {
        supportText = 'Priority email support';
      } else if (features.support === '24/7') {
        supportText = '24/7 priority support';
      }
      
      featureItems.push(
        <li key="support" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">{supportText}</p>
        </li>
      );
    }
    
    // Question library access
    if (features.question_library_access) {
      featureItems.push(
        <li key="library" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">
            {features.question_library_access === 'limited' ? 'Limited question library access' : 'Full question library access'}
          </p>
        </li>
      );
    }
  }
  
  // Professional plan shows only what's different from Basic
  if (planName === 'Professional') {
    // Unlimited interviews
    if (features.interviews_per_month === -1) {
      featureItems.push(
        <li key="unlimited" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Unlimited AI-powered mock interviews</p>
        </li>
      );
    }
    
    // Longer interviews
    if (features.interview_duration_max) {
      featureItems.push(
        <li key="longer" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">
            Longer interviews (up to {features.interview_duration_max} minutes)
          </p>
        </li>
      );
    }
    
    // Video interviews
    if (features.video_interviews) {
      featureItems.push(
        <li key="video" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Video interview mode</p>
        </li>
      );
    }
    
    // CV review
    if (features.cv_review) {
      featureItems.push(
        <li key="cv" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">CV/Resume review</p>
        </li>
      );
    }
    
    // Performance analytics
    if (features.performance_analytics) {
      featureItems.push(
        <li key="analytics" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Detailed performance analytics</p>
        </li>
      );
    }
    
    // Personalized suggestions
    if (features.personalized_suggestions) {
      featureItems.push(
        <li key="suggestions" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Personalized improvement suggestions</p>
        </li>
      );
    }
    
    // Priority support
    if (features.support === 'priority_email') {
      featureItems.push(
        <li key="priority" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Priority email support</p>
        </li>
      );
    }
  }
  
  // Enterprise plan shows only what's different from Professional
  if (planName === 'Enterprise') {
    // Extended interviews
    if (features.interview_duration_max) {
      featureItems.push(
        <li key="extended" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">
            Extended interviews (up to {features.interview_duration_max} minutes)
          </p>
        </li>
      );
    }
    
    // Team management
    if (features.team_management) {
      featureItems.push(
        <li key="team" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Team management dashboard</p>
        </li>
      );
    }
    
    // Bulk user management
    if (features.bulk_user_management) {
      featureItems.push(
        <li key="bulk" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Bulk user management</p>
        </li>
      );
    }
    
    // Custom templates
    if (features.custom_templates) {
      featureItems.push(
        <li key="templates" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Custom interview templates</p>
        </li>
      );
    }
    
    // Dedicated account manager
    if (features.dedicated_account_manager) {
      featureItems.push(
        <li key="manager" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">Dedicated account manager</p>
        </li>
      );
    }
    
    // 24/7 support
    if (features.support === '24/7') {
      featureItems.push(
        <li key="24-7" className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-6 w-6 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p className="ml-3 text-base text-gray-700">24/7 priority support</p>
        </li>
      );
    }
  }
  
  return featureItems;
};

export default PlanFeaturesList; 