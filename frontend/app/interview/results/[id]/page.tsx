'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface EvaluationData {
  interviewId: string;
  jobTitle: string;
  interviewType: string;
  score: number;
  feedback: string;
  strengths: string[];
  weaknesses: string[];
  improvement_areas: string[];
}

export default function InterviewResults({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [evaluationData, setEvaluationData] = useState<EvaluationData | null>(null);
  const [error, setError] = useState('');

  // Cleanup any lingering media resources when the results page loads
  useEffect(() => {
    // Force cleanup of any media tracks that might still be running
    try {
      // Stop any active MediaStream tracks that might still be running
      if (navigator.mediaDevices) {
        const allTracks = document.querySelectorAll('video, audio');
        allTracks.forEach(element => {
          const mediaElement = element as HTMLMediaElement;
          if (mediaElement.srcObject) {
            const stream = mediaElement.srcObject as MediaStream;
            if (stream) {
              stream.getTracks().forEach(track => {
                track.stop();
                console.log(`Results page cleanup: Stopped track: ${track.kind}`);
              });
              mediaElement.srcObject = null;
            }
          }
        });
        
        // Additional cleanup for any getUserMedia streams that might be cached
        try {
          // This is a trick to force the browser to release camera permissions
          navigator.mediaDevices.getUserMedia({ audio: true, video: true })
            .then(emptyStream => {
              emptyStream.getTracks().forEach(track => {
                track.stop();
                console.log(`Results page: Stopped empty stream track: ${track.kind}`);
              });
            })
            .catch(err => {
              console.log('No additional media streams to clean up');
            });
        } catch (err) {
          console.log('Could not perform additional media cleanup:', err);
        }
      }
    } catch (err) {
      console.error('Error during media cleanup on results page:', err);
    }
  }, []);

  useEffect(() => {
    // Load evaluation data from localStorage
    const storedData = localStorage.getItem('interviewEvaluation');
    if (storedData) {
      const parsedData = JSON.parse(storedData);
      if (parsedData.interviewId === params.id) {
        setEvaluationData(parsedData);
      } else {
        setError('Evaluation data not found');
      }
    } else {
      setError('Evaluation data not found');
    }
  }, [params.id]);

  // Function to get score color class
  const getScoreColorClass = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 75) return 'text-blue-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  // Function to get score label
  const getScoreLabel = (score: number) => {
    if (score >= 90) return 'Excellent';
    if (score >= 75) return 'Good';
    if (score >= 60) return 'Satisfactory';
    if (score >= 40) return 'Needs Improvement';
    return 'Poor';
  };

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="bg-white rounded-lg shadow-lg p-6 md:p-8 text-center">
          <h1 className="text-3xl font-bold mb-6">Error</h1>
          <p className="text-red-600 mb-6">{error}</p>
          <Link
            href="/interview/setup"
            className="px-6 py-2 rounded-md bg-indigo-600 text-white font-medium hover:bg-indigo-700"
          >
            Set Up New Interview
          </Link>
        </div>
      </div>
    );
  }

  if (!evaluationData) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="bg-white rounded-lg shadow-lg p-6 md:p-8 text-center">
          <h1 className="text-3xl font-bold mb-6">Loading Results...</h1>
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        {/* Header */}
        <div className="bg-gray-800 text-white p-6">
          <h1 className="text-2xl font-bold mb-2">Interview Evaluation</h1>
          <p className="text-gray-300">{evaluationData.jobTitle} Position</p>
          <p className="text-gray-400 text-sm mt-1">
            {evaluationData.interviewType ? 
              `${evaluationData.interviewType.charAt(0).toUpperCase() + evaluationData.interviewType.slice(1)} Interview` : 
              'Interview'}
          </p>
        </div>
        
        {/* Score section */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex flex-col items-center">
            <div className="text-5xl font-bold mb-2 flex items-center">
              <span className={getScoreColorClass(evaluationData.score)}>
                {evaluationData.score}
              </span>
              <span className="text-gray-400 text-2xl ml-1">/100</span>
            </div>
            <div className={`text-xl font-medium ${getScoreColorClass(evaluationData.score)}`}>
              {getScoreLabel(evaluationData.score)}
            </div>
          </div>
        </div>
        
        {/* Feedback section */}
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold mb-4">Overall Feedback</h2>
          <p className="text-gray-700 whitespace-pre-line">{evaluationData.feedback}</p>
        </div>
        
        {/* Strengths and weaknesses */}
        <div className="grid md:grid-cols-2 gap-6 p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold mb-4 text-green-600">Strengths</h2>
            <ul className="list-disc pl-5 space-y-2">
              {evaluationData.strengths.map((strength, index) => (
                <li key={index} className="text-gray-700">{strength}</li>
              ))}
            </ul>
          </div>
          <div>
            <h2 className="text-xl font-semibold mb-4 text-red-600">Areas for Improvement</h2>
            <ul className="list-disc pl-5 space-y-2">
              {evaluationData.weaknesses.map((weakness, index) => (
                <li key={index} className="text-gray-700">{weakness}</li>
              ))}
            </ul>
          </div>
        </div>
        
        {/* Improvement suggestions */}
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold mb-4">Suggested Improvements</h2>
          <ul className="list-disc pl-5 space-y-2">
            {evaluationData.improvement_areas.map((area, index) => (
              <li key={index} className="text-gray-700">{area}</li>
            ))}
          </ul>
        </div>
        
        {/* Actions */}
        <div className="p-6 bg-gray-50 flex flex-col sm:flex-row justify-between items-center space-y-4 sm:space-y-0">
          <Link
            href="/interview/setup"
            className="px-6 py-2 rounded-md bg-indigo-600 text-white font-medium hover:bg-indigo-700 w-full sm:w-auto text-center"
          >
            Practice Again
          </Link>
          <div className="flex space-x-4 w-full sm:w-auto">
            <button
              onClick={() => window.print()}
              className="px-6 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 flex-1 sm:flex-none"
            >
              Print Results
            </button>
            <Link
              href="/"
              className="px-6 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 flex-1 sm:flex-none text-center"
            >
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
} 