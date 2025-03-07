'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '../../../lib/auth-context';
import axios from 'axios';

// Add API base URL configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Define plan feature restrictions
const planFeatures = {
  Free: {
    interview_duration_max: 15,
    voiceMode: false,
    videoMode: false,
    codeChallenge: false,
    maxInterviews: 3,
    feedbackDetail: 'basic'
  },
  Basic: {
    interview_duration_max: 30,
    voiceMode: true,
    videoMode: false,
    codeChallenge: true,
    maxInterviews: 10,
    feedbackDetail: 'detailed'
  },
  Professional: {
    interview_duration_max: 60,
    voiceMode: true,
    videoMode: true,
    codeChallenge: true,
    maxInterviews: -1, // unlimited
    feedbackDetail: 'comprehensive'
  },
  Enterprise: {
    interview_duration_max: 120,
    voiceMode: true,
    videoMode: true,
    codeChallenge: true,
    maxInterviews: -1, // unlimited
    feedbackDetail: 'comprehensive'
  }
};

export default function InterviewSetup() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, getAccessToken } = useAuth();
  const [jobTitle, setJobTitle] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [interviewType, setInterviewType] = useState('general');
  const [duration, setDuration] = useState(15);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [useVoiceMode, setUseVoiceMode] = useState(false);
  const [useVideoMode, setUseVideoMode] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Add states for progressive loading
  const [progressiveQuestions, setProgressiveQuestions] = useState<any[]>([]);
  const [progressiveLoading, setProgressiveLoading] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  
  // Get user's plan
  const [userPlan, setUserPlan] = useState('Free');
  const [availableDurations, setAvailableDurations] = useState<number[]>([5, 15]);
  const [planFeatureSettings, setPlanFeatureSettings] = useState(planFeatures.Free);
  const [selectedDuration, setSelectedDuration] = useState<string>("15");

  // Clear previous interview evaluation data when setting up a new interview
  useEffect(() => {
    // Clear the latest interview evaluation ID
    const latestEvaluationId = localStorage.getItem('latestInterviewEvaluation');
    
    if (latestEvaluationId) {
      // Remove the evaluation data for the latest interview
      localStorage.removeItem(`interviewEvaluation_${latestEvaluationId}`);
      localStorage.removeItem('latestInterviewEvaluation');
    }
    
    // For backward compatibility, also remove the old format
    localStorage.removeItem('interviewEvaluation');
    
    console.log('Cleared previous interview evaluation data');
  }, []);

  // Check authentication status and get user's plan
  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.push('/auth/login?redirect=/interview/setup');
      } else if (user) {
        // Set user's plan
        const planName = user.subscription?.plan?.name || 'Free';
        setUserPlan(planName);
        
        // Set plan feature settings
        const features = planFeatures[planName as keyof typeof planFeatures] || planFeatures.Free;
        setPlanFeatureSettings(features);
        
        // Set available durations based on plan
        const maxDuration = features.interview_duration_max || 15;
        const durations = [5, 15];
        if (maxDuration >= 30) durations.push(30);
        if (maxDuration >= 60) durations.push(60);
        if (maxDuration >= 120) durations.push(120);
        setAvailableDurations(durations);
        
        // Set default duration to 15 minutes or the lowest available
        const initialDuration = durations.includes(15) ? 15 : durations[0];
        setDuration(initialDuration);
        setSelectedDuration(initialDuration.toString());
        console.log('Setting initial duration to:', initialDuration);
        console.log('Available durations:', durations);
      }
    }
  }, [isLoading, isAuthenticated, router, user]);

  // Handle voice mode toggle
  const handleVoiceModeToggle = () => {
    setUseVoiceMode(!useVoiceMode);
  };

  // Handle video mode toggle
  const handleVideoModeToggle = () => {
    setUseVideoMode(!useVideoMode);
  };

  // Handle duration change
  const handleDurationChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    console.log('Duration dropdown changed to:', value);
    setSelectedDuration(value);
    const newDuration = parseInt(value, 10);
    console.log('Setting duration to:', newDuration);
    setDuration(newDuration);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setCvFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');
    setProgressiveQuestions([]);
    setProgressiveLoading(true);
    setProgressPercent(0);

    // Add a timeout to prevent getting stuck - longer for longer interviews
    const timeoutDuration = duration >= 60 ? 90000 : 45000; // 90 seconds for 60-min interviews, 45 seconds for others
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Request timed out. Please try again.')), timeoutDuration);
    });

    try {
      // Clear any previous interview data
      localStorage.removeItem('interviewEvaluation');
      localStorage.removeItem('currentInterview');
      
      // Clear any other interview-related data that might be stored
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (key.includes('interview') || key.includes('answer'))) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach(key => localStorage.removeItem(key));
      
      // Validate inputs
      if (!jobTitle.trim()) {
        throw new Error('Job title is required');
      }
      if (!jobDescription.trim()) {
        throw new Error('Job description is required');
      }

      // Upload CV if provided
      let cvText = null;
      if (cvFile) {
        const formData = new FormData();
        formData.append('file', cvFile);
        
        const token = await getAccessToken();
        const uploadResponse = await Promise.race([
          fetch(`${API_BASE_URL}/api/upload-cv`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`
            },
            body: formData,
          }),
          timeoutPromise
        ]) as Response;
        
        if (!uploadResponse.ok) {
          const errorData = await uploadResponse.json().catch(() => ({ detail: 'Failed to upload CV' }));
          throw new Error(errorData.detail || 'Failed to upload CV');
        }
        
        const cvUploadResponse = await uploadResponse.json();
        cvText = cvUploadResponse.cv_text;
      }

      // Generate interview with progressive loading
      setProgressiveQuestions([]);
      setProgressiveLoading(true);
      setProgressPercent(0);

      // Make the actual request to generate all questions
      const token = await getAccessToken();
      console.log('Sending interview request with duration:', duration);
      console.log('Voice mode:', useVoiceMode, 'Video mode:', useVideoMode);
      
      const interviewResponse = await Promise.race([
        fetch(`${API_BASE_URL}/api/interview/questions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            job_title: jobTitle,
            job_description: jobDescription,
            cv_text: cvText,
            interview_type: interviewType,
            duration: parseInt(selectedDuration, 10), // Use selectedDuration to ensure correct value
            use_voice_mode: useVoiceMode,
            use_video_mode: useVideoMode
          }),
        }),
        timeoutPromise
      ]) as Response;

      if (!interviewResponse.ok) {
        const errorData = await interviewResponse.json().catch(() => ({ detail: 'Failed to generate interview' }));
        throw new Error(errorData.detail || 'Failed to generate interview');
      }

      const interviewData = await interviewResponse.json();
      console.log('Interview data received:', interviewData.interview_id);
      
      // Update progress to 100%
      setProgressPercent(100);
      setProgressiveQuestions(interviewData.questions);
      
      // Store interview data in localStorage for now (in a real app, this would be in a database)
      localStorage.setItem('currentInterview', JSON.stringify({
        id: interviewData.interview_id,
        jobTitle,
        jobDescription,
        interviewType,
        duration,
        questions: interviewData.questions,
        cvFilename: cvFile ? cvFile.name : null,
        useVoiceMode: useVoiceMode,
        useVideoMode: useVideoMode,
        seniority_level: interviewData.seniority_level || 'mid'
      }));

      // Navigate to the interview page
      router.push(`/interview/session/${interviewData.interview_id}`);
    } catch (err) {
      console.error('Error during interview setup:', err);
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setIsSubmitting(false);
      setProgressiveLoading(false);
    }
  };

  // Add loading state for auth check
  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Set Up Your Interview</h1>
      
      {error && (
        <div className="mb-6 bg-red-50 border-l-4 border-red-400 p-4">
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
      
      <div className="bg-white rounded-lg shadow-lg p-6 md:p-8">
        <h1 className="text-3xl font-bold mb-6 text-center">Set Up Your Interview</h1>
        
        <div className="mb-6 bg-indigo-50 p-4 rounded-lg">
          <h2 className="text-lg font-semibold text-indigo-700">Your Plan: {userPlan}</h2>
          <p className="text-sm text-indigo-600 mt-1">
            {planFeatureSettings.maxInterviews === -1 
              ? 'Unlimited interviews' 
              : `${planFeatureSettings.maxInterviews} interviews per month`}, 
            up to {planFeatureSettings.interview_duration_max} minutes each
          </p>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <div>
              <label htmlFor="jobTitle" className="block text-sm font-medium text-gray-700 mb-1">
                Job Title *
              </label>
              <input
                type="text"
                id="jobTitle"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="e.g. Frontend Developer"
                required
              />
            </div>
            
            <div>
              <label htmlFor="jobDescription" className="block text-sm font-medium text-gray-700 mb-1">
                Job Description *
              </label>
              <textarea
                id="jobDescription"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                rows={5}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                placeholder="Paste the job description here..."
                required
              />
              <p className="mt-1 text-sm text-gray-500">
                Note: The system will automatically detect the seniority level (junior, mid, or senior) from the job title and description, and tailor questions accordingly.
              </p>
            </div>
            
            <div>
              <label htmlFor="cv" className="block text-sm font-medium text-gray-700 mb-1">
                Upload Your CV/Resume {userPlan === 'Free' || userPlan === 'Basic' ? '(Professional+ Feature)' : '(Optional)'}
              </label>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className={`px-4 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium ${
                    userPlan === 'Free' || userPlan === 'Basic' 
                      ? 'text-gray-400 cursor-not-allowed' 
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                  disabled={userPlan === 'Free' || userPlan === 'Basic'}
                >
                  Choose File
                </button>
                <span className="text-sm text-gray-500">
                  {cvFile ? cvFile.name : 'No file chosen'}
                </span>
                <input
                  type="file"
                  id="cv"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".pdf,.doc,.docx"
                  className="hidden"
                  disabled={userPlan === 'Free' || userPlan === 'Basic'}
                />
              </div>
              <p className="mt-1 text-xs text-gray-500">
                {userPlan === 'Free' || userPlan === 'Basic' 
                  ? 'CV/Resume review is available in Professional and Enterprise plans.' 
                  : 'Supported formats: PDF, DOC, DOCX'}
              </p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="interviewType" className="block text-sm font-medium text-gray-700 mb-1">
                Interview Type
              </label>
              <select
                id="interviewType"
                value={interviewType}
                onChange={(e) => setInterviewType(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="general">General</option>
                <option value="technical">Technical</option>
                <option value="behavioral">Behavioral</option>
                <option value="leadership">Leadership</option>
              </select>
            </div>
            
            <div>
              <label htmlFor="duration" className="block text-sm font-medium text-gray-700 mb-1">
                Duration (minutes)
              </label>
              <select
                id="duration"
                value={selectedDuration}
                onChange={handleDurationChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              >
                {availableDurations.map(d => (
                  <option key={d} value={d.toString()}>{d} minutes ({d} questions)</option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">
                The interview will generate 1 question per minute of duration. Your plan allows up to {planFeatureSettings.interview_duration_max} minutes.
              </p>
            </div>
          </div>
          
          {planFeatureSettings.voiceMode && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium text-gray-900">Voice Mode</h3>
                  <p className="text-sm text-gray-500">Enable voice conversation with the AI interviewer</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    className="sr-only peer" 
                    checked={useVoiceMode}
                    onChange={handleVoiceModeToggle}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
              {useVoiceMode && (
                <div className="mt-3 text-sm text-gray-600 bg-indigo-50 p-3 rounded-md">
                  <p>Voice mode will allow you to:</p>
                  <ul className="list-disc pl-5 mt-1 space-y-1">
                    <li>Speak your answers instead of typing</li>
                    <li>Hear the interviewer's questions</li>
                    <li>Have a more natural conversation experience</li>
                  </ul>
                  <p className="mt-2 text-xs">Note: This requires microphone access.</p>
                </div>
              )}
            </div>
          )}
          
          {!planFeatureSettings.voiceMode && (
            <div className="mt-4 p-4 bg-gray-100 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium text-gray-500">Voice Mode (Basic+ Feature)</h3>
                  <p className="text-sm text-gray-500">Upgrade to Basic plan or higher to enable voice conversation</p>
                </div>
                <div className="relative inline-flex items-center">
                  <div className="w-11 h-6 bg-gray-300 rounded-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5"></div>
                </div>
              </div>
            </div>
          )}
          
          {planFeatureSettings.videoMode && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium text-gray-900">Video Mode</h3>
                  <p className="text-sm text-gray-500">Enable video for a more realistic interview experience</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    className="sr-only peer" 
                    checked={useVideoMode}
                    onChange={handleVideoModeToggle}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
              {useVideoMode && (
                <div className="mt-3 text-sm text-gray-600 bg-indigo-50 p-3 rounded-md">
                  <p>Video mode will allow you to:</p>
                  <ul className="list-disc pl-5 mt-1 space-y-1">
                    <li>See yourself during the interview</li>
                    <li>Practice your facial expressions and body language</li>
                    <li>Create a more realistic interview environment</li>
                  </ul>
                  <p className="mt-2 text-xs">Note: This requires camera access. You can toggle video on/off during the interview.</p>
                </div>
              )}
            </div>
          )}
          
          {!planFeatureSettings.videoMode && (
            <div className="mt-4 p-4 bg-gray-100 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium text-gray-500">Video Mode (Professional+ Feature)</h3>
                  <p className="text-sm text-gray-500">Upgrade to Professional plan or higher to enable video interviews</p>
                </div>
                <div className="relative inline-flex items-center">
                  <div className="w-11 h-6 bg-gray-300 rounded-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5"></div>
                </div>
              </div>
            </div>
          )}
          
          <div className="mt-8 flex justify-between">
            <Link
              href="/"
              className="px-6 py-3 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={isSubmitting}
              className={`px-6 py-3 rounded-md bg-indigo-600 text-white font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                isSubmitting ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {isSubmitting ? (
                <div className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Setting up interview...
                </div>
              ) : (
                'Start Interview'
              )}
            </button>
          </div>
          
          {isSubmitting && (
            <div className="mt-4 p-3 bg-gray-100 rounded-md text-sm text-gray-700">
              <p className="font-medium">Setup Progress:</p>
              <p>{progressPercent}% complete</p>
              
              {progressiveLoading && (
                <div className="mt-3">
                  <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                    <div className="bg-indigo-600 h-2.5 rounded-full" style={{ width: `${progressPercent}%` }}></div>
                  </div>
                  <p className="text-xs text-gray-500">Generating questions: {progressPercent}% complete</p>
                  
                  {progressiveQuestions.length > 0 && (
                    <div className="mt-3">
                      <p className="font-medium text-sm">Questions generated so far:</p>
                      <div className="mt-2 max-h-40 overflow-y-auto text-xs">
                        {progressiveQuestions.slice(0, 5).map((q, i) => (
                          <div key={i} className="mb-1 pb-1 border-b border-gray-100">
                            {i+1}. {q.question.substring(0, 100)}{q.question.length > 100 ? '...' : ''}
                          </div>
                        ))}
                        {progressiveQuestions.length > 5 && (
                          <p className="text-gray-500 italic">
                            +{progressiveQuestions.length - 5} more questions...
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </form>
      </div>
    </div>
  );
} 