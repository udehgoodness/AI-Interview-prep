'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

// Add API base URL configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function InterviewSetup() {
  const router = useRouter();
  const [jobTitle, setJobTitle] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [interviewType, setInterviewType] = useState('general');
  const [duration, setDuration] = useState(30);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [useVoiceMode, setUseVoiceMode] = useState(false);
  const [useVideoMode, setUseVideoMode] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Add states for progressive loading
  const [progressiveQuestions, setProgressiveQuestions] = useState<any[]>([]);
  const [progressiveLoading, setProgressiveLoading] = useState(false);
  const [progressPercent, setProgressPercent] = useState(0);
  
  // Add debug state
  const [debugInfo, setDebugInfo] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setCvFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setDebugInfo('Starting interview setup...');
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
      setDebugInfo('Cleared previous interview data');
      
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
      setDebugInfo('Inputs validated');

      // Upload CV if provided
      let cvText = null;
      if (cvFile) {
        setDebugInfo('Uploading CV...');
        const formData = new FormData();
        formData.append('file', cvFile);
        
        const uploadResponse = await Promise.race([
          fetch(`${API_BASE_URL}/api/upload-cv`, {
            method: 'POST',
            body: formData,
          }),
          timeoutPromise
        ]) as Response;
        
        if (!uploadResponse.ok) {
          throw new Error('Failed to upload CV');
        }
        
        const cvUploadResponse = await uploadResponse.json();
        cvText = cvUploadResponse.cv_text;
        setDebugInfo('CV uploaded successfully');
      }

      // Generate interview with progressive loading
      setDebugInfo('Generating interview questions...');
      console.log('Generating interview questions...');
      
      // Start a polling mechanism to check progress
      const interviewId = `temp_${Date.now()}`;
      let questionsGenerated = 0;
      
      // Set up polling for progressive updates
      const pollInterval = setInterval(async () => {
        try {
          // Check if we already have all questions
          if (questionsGenerated >= duration) {
            clearInterval(pollInterval);
            return;
          }
          
          // Poll for new questions (this is a simulated endpoint - you'd need to implement this on the backend)
          const pollResponse = await fetch(`${API_BASE_URL}/api/interview/questions/progress?id=${interviewId}`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            }
          });
          
          if (pollResponse.ok) {
            const progressData = await pollResponse.json();
            if (progressData.questions && progressData.questions.length > questionsGenerated) {
              // Update with new questions
              setProgressiveQuestions(progressData.questions);
              questionsGenerated = progressData.questions.length;
              
              // Update progress percentage
              const percent = Math.min(Math.round((questionsGenerated / duration) * 100), 99);
              setProgressPercent(percent);
              
              setDebugInfo(`Generated ${questionsGenerated} of ${duration} questions (${percent}%)`);
            }
          }
        } catch (error) {
          // Ignore polling errors
          console.error('Polling error:', error);
        }
      }, 2000); // Poll every 2 seconds
      
      // Make the actual request to generate all questions
      const interviewResponse = await Promise.race([
        fetch(`${API_BASE_URL}/api/interview/questions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            job_title: jobTitle,
            job_description: jobDescription,
            cv_text: cvText,
            interview_type: interviewType,
            duration: duration,
          }),
        }),
        timeoutPromise
      ]) as Response;

      // Clear the polling interval once we have the full response
      clearInterval(pollInterval);

      if (!interviewResponse.ok) {
        const errorData = await interviewResponse.json();
        throw new Error(errorData.detail || 'Failed to generate interview');
      }

      setDebugInfo('Parsing interview data...');
      const interviewData = await interviewResponse.json();
      console.log('Interview data received:', interviewData.interview_id);
      setDebugInfo(`Interview data received: ${interviewData.interview_id}`);
      
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
      setDebugInfo('Interview data stored in localStorage');

      // Navigate to the interview page
      setDebugInfo('Navigating to interview session...');
      router.push(`/interview/session/${interviewData.interview_id}`);
    } catch (err) {
      console.error('Error during interview setup:', err);
      setDebugInfo(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
      setProgressiveLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="bg-white rounded-lg shadow-lg p-6 md:p-8">
        <h1 className="text-3xl font-bold mb-6 text-center">Set Up Your Interview</h1>
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}
        
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
                Upload Your CV/Resume (Optional)
              </label>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
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
                />
              </div>
              <p className="mt-1 text-xs text-gray-500">
                Supported formats: PDF, DOC, DOCX
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
                value={duration}
                onChange={(e) => setDuration(parseInt(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              >
                <option value="5">5 minutes (5 questions)</option>
                <option value="15">15 minutes (15 questions)</option>
                <option value="30">30 minutes (30 questions)</option>
                <option value="60">60 minutes (60 questions)</option>
              </select>
              <p className="mt-1 text-xs text-gray-500">
                The interview will generate 1 question per minute of duration.
              </p>
            </div>
          </div>
          
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
                  onChange={() => setUseVoiceMode(!useVoiceMode)}
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
                  onChange={() => setUseVideoMode(!useVideoMode)}
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
          
          <div className="mt-8 flex justify-between">
            <Link
              href="/"
              className="px-6 py-3 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={isLoading}
              className={`px-6 py-3 rounded-md bg-indigo-600 text-white font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                isLoading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {isLoading ? (
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
          
          {isLoading && (
            <div className="mt-4 p-3 bg-gray-100 rounded-md text-sm text-gray-700">
              <p className="font-medium">Setup Progress:</p>
              <p>{debugInfo}</p>
              
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