'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import dynamic from 'next/dynamic';

// Dynamically import the Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(
  () => import('@monaco-editor/react'),
  { ssr: false }
);

interface Question {
  id: string;
  question: string;
  type: string;
  expected_answer_points?: string[];
}

interface InterviewData {
  id: string;
  jobTitle: string;
  jobDescription: string;
  interviewType: string;
  duration: number;
  questions: Question[];
  cvFilename?: string | null;
}

export default function InterviewSession({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [interviewData, setInterviewData] = useState<InterviewData | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isRecording, setIsRecording] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [isVideoConnected, setIsVideoConnected] = useState(false);
  
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Load interview data from localStorage
  useEffect(() => {
    const storedData = localStorage.getItem('currentInterview');
    if (storedData) {
      const parsedData = JSON.parse(storedData);
      if (parsedData.id === params.id) {
        setInterviewData(parsedData);
        setTimeLeft(parsedData.duration * 60); // Convert minutes to seconds
        
        // Initialize answers object
        const initialAnswers: Record<string, string> = {};
        parsedData.questions.forEach((q: Question) => {
          initialAnswers[q.id] = '';
        });
        setAnswers(initialAnswers);
      } else {
        setError('Interview data not found');
      }
    } else {
      setError('Interview data not found');
    }
  }, [params.id]);

  // Timer countdown
  useEffect(() => {
    if (timeLeft > 0 && interviewData) {
      timerRef.current = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current as NodeJS.Timeout);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [timeLeft, interviewData]);

  // Initialize WebRTC
  useEffect(() => {
    if (interviewData) {
      initializeWebRTC();
    }

    return () => {
      // Clean up WebRTC connection
      if (peerConnectionRef.current) {
        peerConnectionRef.current.close();
      }
      
      // Stop all media tracks
      if (localVideoRef.current && localVideoRef.current.srcObject) {
        const mediaStream = localVideoRef.current.srcObject as MediaStream;
        mediaStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [interviewData]);

  const initializeWebRTC = async () => {
    try {
      // Get user media (camera and microphone)
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true
      });
      
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = mediaStream;
      }

      // Create RTCPeerConnection
      const configuration = {
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          { urls: 'stun:stun1.l.google.com:19302' }
        ]
      };
      
      const peerConnection = new RTCPeerConnection(configuration);
      peerConnectionRef.current = peerConnection;
      
      // Add local tracks to the connection
      mediaStream.getTracks().forEach(track => {
        peerConnection.addTrack(track, mediaStream);
      });
      
      // Handle ICE candidates
      peerConnection.onicecandidate = (event) => {
        if (event.candidate) {
          // In a real app, send this to the server
          console.log('New ICE candidate:', event.candidate);
        }
      };
      
      // Handle connection state changes
      peerConnection.onconnectionstatechange = () => {
        console.log('Connection state:', peerConnection.connectionState);
        if (peerConnection.connectionState === 'connected') {
          setIsVideoConnected(true);
        } else if (['disconnected', 'failed', 'closed'].includes(peerConnection.connectionState)) {
          setIsVideoConnected(false);
        }
      };
      
      // Handle incoming tracks (would be from the AI in a real implementation)
      peerConnection.ontrack = (event) => {
        if (remoteVideoRef.current && event.streams[0]) {
          remoteVideoRef.current.srcObject = event.streams[0];
        }
      };
      
      // Create and send offer (in a real app, this would go to the server)
      const offer = await peerConnection.createOffer();
      await peerConnection.setLocalDescription(offer);
      
      // Mock server response (in a real app, this would come from the server)
      setTimeout(() => {
        // Simulate receiving an answer from the server
        const mockAnswer: RTCSessionDescriptionInit = {
          type: 'answer',
          sdp: offer.sdp // In a real app, this would be a proper SDP answer
        };
        
        peerConnection.setRemoteDescription(new RTCSessionDescription(mockAnswer))
          .then(() => {
            console.log('Remote description set successfully');
            setIsVideoConnected(true);
          })
          .catch(err => {
            console.error('Error setting remote description:', err);
          });
      }, 1000);
      
      setIsRecording(true);
    } catch (err) {
      console.error('Error initializing WebRTC:', err);
      setError('Failed to access camera or microphone. Please check your permissions.');
    }
  };

  const handleAnswerChange = (value: string | undefined) => {
    if (!interviewData) return;
    
    const currentQuestion = interviewData.questions[currentQuestionIndex];
    setAnswers(prev => ({
      ...prev,
      [currentQuestion.id]: value || ''
    }));
  };

  const handleNextQuestion = () => {
    if (!interviewData) return;
    
    if (currentQuestionIndex < interviewData.questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
    }
  };

  const handleSubmitInterview = async () => {
    if (!interviewData) return;
    
    setIsSubmitting(true);
    setError('');
    
    try {
      // Format answers for submission
      const formattedAnswers = Object.keys(answers).map(questionId => ({
        question_id: questionId,
        answer: answers[questionId]
      }));
      
      // Submit answers for evaluation
      const response = await fetch('http://localhost:8000/api/evaluate-interview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          interview_id: interviewData.id,
          answers: formattedAnswers
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to submit interview');
      }
      
      const evaluationData = await response.json();
      
      // Store evaluation data
      localStorage.setItem('interviewEvaluation', JSON.stringify({
        interviewId: interviewData.id,
        jobTitle: interviewData.jobTitle,
        ...evaluationData
      }));
      
      // Navigate to results page
      router.push(`/interview/results/${interviewData.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Format time (seconds) to MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
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

  if (!interviewData) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="bg-white rounded-lg shadow-lg p-6 md:p-8 text-center">
          <h1 className="text-3xl font-bold mb-6">Loading Interview...</h1>
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
        </div>
      </div>
    );
  }

  const currentQuestion = interviewData.questions[currentQuestionIndex];

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        {/* Header */}
        <div className="bg-gray-800 text-white p-4 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold">{interviewData.jobTitle} Interview</h1>
            <p className="text-sm text-gray-300">{interviewData.interviewType} interview - {interviewData.duration} minutes</p>
          </div>
          <div className="flex items-center space-x-4">
            <div className={`flex items-center ${timeLeft < 60 ? 'text-red-400' : 'text-white'}`}>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-mono">{formatTime(timeLeft)}</span>
            </div>
            <div className={`flex items-center ${isRecording ? 'text-red-400' : 'text-gray-400'}`}>
              <span className={`h-3 w-3 rounded-full ${isRecording ? 'bg-red-500 animate-pulse' : 'bg-gray-500'} mr-1`}></span>
              <span className="text-sm">{isRecording ? 'Recording' : 'Not Recording'}</span>
            </div>
          </div>
        </div>
        
        {/* Main content */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
          {/* Video section */}
          <div className="bg-gray-100 rounded-lg p-4">
            <div className="aspect-video bg-black rounded-lg overflow-hidden relative mb-4">
              {/* Remote video (AI interviewer) */}
              <video
                ref={remoteVideoRef}
                autoPlay
                playsInline
                className="w-full h-full object-cover"
                poster="/ai-interviewer-placeholder.jpg"
              ></video>
              
              {/* Local video (user) */}
              <div className="absolute bottom-4 right-4 w-1/4 h-1/4 bg-gray-800 rounded overflow-hidden border-2 border-white">
                <video
                  ref={localVideoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                ></video>
              </div>
              
              {!isVideoConnected && (
                <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-70 text-white">
                  <div className="text-center">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p>Video connection failed. Using text-based interview mode.</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Question navigation */}
            <div className="flex justify-between items-center">
              <button
                onClick={handlePreviousQuestion}
                disabled={currentQuestionIndex === 0}
                className={`px-4 py-2 rounded-md ${
                  currentQuestionIndex === 0
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-gray-700 text-white hover:bg-gray-800'
                }`}
              >
                Previous
              </button>
              <span className="text-sm font-medium">
                Question {currentQuestionIndex + 1} of {interviewData.questions.length}
              </span>
              <button
                onClick={handleNextQuestion}
                disabled={currentQuestionIndex === interviewData.questions.length - 1}
                className={`px-4 py-2 rounded-md ${
                  currentQuestionIndex === interviewData.questions.length - 1
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-gray-700 text-white hover:bg-gray-800'
                }`}
              >
                Next
              </button>
            </div>
          </div>
          
          {/* Question and answer section */}
          <div className="bg-gray-100 rounded-lg p-4 flex flex-col">
            <div className="mb-4">
              <h2 className="text-lg font-semibold mb-2">
                Question {currentQuestionIndex + 1}: {currentQuestion.type.charAt(0).toUpperCase() + currentQuestion.type.slice(1)}
              </h2>
              <p className="text-gray-800 p-3 bg-white rounded-lg border border-gray-200">
                {currentQuestion.question}
              </p>
            </div>
            
            <div className="flex-grow">
              {currentQuestion.type === 'coding' ? (
                <div className="h-full min-h-[300px] border border-gray-300 rounded-lg overflow-hidden">
                  <MonacoEditor
                    height="100%"
                    language="javascript"
                    theme="vs-dark"
                    value={answers[currentQuestion.id] || '// Write your code here'}
                    onChange={handleAnswerChange}
                    options={{
                      minimap: { enabled: false },
                      scrollBeyondLastLine: false,
                      fontSize: 14,
                    }}
                  />
                </div>
              ) : (
                <textarea
                  value={answers[currentQuestion.id] || ''}
                  onChange={(e) => handleAnswerChange(e.target.value)}
                  placeholder="Type your answer here..."
                  className="w-full h-full min-h-[300px] p-3 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500"
                  rows={10}
                ></textarea>
              )}
            </div>
          </div>
        </div>
        
        {/* Footer */}
        <div className="bg-gray-100 p-4 border-t border-gray-200 flex justify-between items-center">
          <Link
            href="/interview/setup"
            className="px-4 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            End Interview
          </Link>
          <button
            onClick={handleSubmitInterview}
            disabled={isSubmitting || timeLeft === 0}
            className={`px-6 py-2 rounded-md bg-indigo-600 text-white font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
              isSubmitting || timeLeft === 0 ? 'opacity-70 cursor-not-allowed' : ''
            }`}
          >
            {isSubmitting ? 'Submitting...' : timeLeft === 0 ? 'Time\'s Up!' : 'Finish & Submit'}
          </button>
        </div>
      </div>
    </div>
  );
} 