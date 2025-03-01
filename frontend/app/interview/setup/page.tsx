'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function InterviewSetup() {
  const router = useRouter();
  const [jobTitle, setJobTitle] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [interviewType, setInterviewType] = useState('general');
  const [duration, setDuration] = useState(30);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setCvFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
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
        
        const response = await fetch('http://localhost:8000/api/upload-cv', {
          method: 'POST',
          body: formData,
        });
        
        if (!response.ok) {
          throw new Error('Failed to upload CV');
        }
        
        const cvUploadResponse = await response.json();
        cvText = cvUploadResponse.cv_text;
      }

      // Generate interview
      const interviewResponse = await fetch('http://localhost:8000/api/interview/questions', {
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
      });

      if (!interviewResponse.ok) {
        const errorData = await interviewResponse.json();
        throw new Error(errorData.detail || 'Failed to generate interview');
      }

      const interviewData = await interviewResponse.json();
      
      // Store interview data in localStorage for now (in a real app, this would be in a database)
      localStorage.setItem('currentInterview', JSON.stringify({
        id: interviewData.interview_id,
        jobTitle,
        jobDescription,
        interviewType,
        duration,
        questions: interviewData.questions,
        cvFilename: cvFile ? cvFile.name : null,
      }));

      // Navigate to the interview page
      router.push(`/interview/session/${interviewData.interview_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      console.error('Error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="bg-white rounded-lg shadow-lg p-6 md:p-8">
        <h1 className="text-3xl font-bold mb-6 text-center">Set Up Your Text Interview</h1>
        
        <div className="mb-6 text-center">
          <p className="text-gray-600 mb-2">Prefer a voice conversation?</p>
          <Link 
            href="/interview/audio" 
            className="text-indigo-600 hover:text-indigo-800 font-medium"
          >
            Switch to Voice Interview →
          </Link>
        </div>
        
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
                <option value="5">5 minutes</option>
                <option value="15">15 minutes</option>
                <option value="30">30 minutes</option>
                <option value="60">60 minutes</option>
              </select>
            </div>
          </div>
          
          <div className="flex justify-between pt-4">
            <Link
              href="/"
              className="px-6 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={isLoading}
              className={`px-6 py-2 rounded-md bg-indigo-600 text-white font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                isLoading ? 'opacity-70 cursor-not-allowed' : ''
              }`}
            >
              {isLoading ? 'Setting up...' : 'Start Interview'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
} 