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
  useVoiceMode?: boolean;
}

export default function InterviewSession({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [interviewData, setInterviewData] = useState<InterviewData | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [isVideoConnected, setIsVideoConnected] = useState(false);
  const [showVideo, setShowVideo] = useState(true);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [isSpeaking, setIsSpeaking] = useState(false);
  
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

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

        // If voice mode is enabled, initialize messages with first question
        if (parsedData.useVoiceMode) {
          const initialMessage = { 
            role: 'assistant', 
            content: `Hello! I'm your AI interviewer for the ${parsedData.jobTitle} position. I'll be asking you some questions to learn more about your experience and skills. Let's start with the first question: ${parsedData.questions[0].question}` 
          };
          setMessages([initialMessage]);
          
          // Speak the initial message after a short delay
          setTimeout(() => {
            speakMessage(initialMessage.content);
          }, 1000);
        }
      } else {
        setError('Interview data not found');
      }
    } else {
      setError('Interview data not found');
    }
  }, [params.id]);

  // Add audio ended event listener
  useEffect(() => {
    const audioElement = audioRef.current;
    
    const handleAudioEnded = () => {
      // Audio has finished playing
      console.log('Audio playback completed');
    };
    
    if (audioElement) {
      audioElement.addEventListener('ended', handleAudioEnded);
    }
    
    return () => {
      if (audioElement) {
        audioElement.removeEventListener('ended', handleAudioEnded);
      }
    };
  }, []);

  // Timer countdown
  useEffect(() => {
    if (timeLeft > 0 && interviewData) {
      timerRef.current = setInterval(() => {
        setTimeLeft((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current as NodeJS.Timeout);
            
            // When time is up, handle the end of interview
            handleTimeUp();
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

  // Handle time up scenario
  const handleTimeUp = async () => {
    if (!interviewData) return;
    
    // For voice mode, add a final message from the AI
    if (interviewData.useVoiceMode && !isSubmitting) {
      // Don't add the message if already submitting or if AI is speaking
      if (!isSpeaking) {
        try {
          // Get a special time-up message from the AI
          const response = await fetch('http://localhost:8000/api/interview/conversation', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              job_title: interviewData.jobTitle,
              job_description: interviewData.jobDescription,
              conversation_history: messages,
              current_question_index: currentQuestionIndex,
              time_up: true
            }),
          });
          
          if (!response.ok) {
            throw new Error('Failed to get AI response');
          }
          
          const data = await response.json();
          
          // Process the AI response to ensure it doesn't contain follow-up questions
          let timeUpMessage = data.text;
          
          // Remove any text after question marks that might be follow-up questions
          if (timeUpMessage.includes('?')) {
            const parts = timeUpMessage.split('?');
            timeUpMessage = parts[0] + '?';
          }
          
          // Add AI response to conversation
          const finalMessage = { role: 'assistant', content: timeUpMessage };
          setMessages(prev => [...prev, finalMessage]);
          
          // Speak the time up message
          if (data.audio) {
            const audioSrc = `data:audio/mp3;base64,${data.audio}`;
            if (audioRef.current) {
              audioRef.current.src = audioSrc;
              await audioRef.current.play();
              
              // Wait for audio to finish
              await new Promise<void>((resolve) => {
                const handleEnded = () => {
                  if (audioRef.current) {
                    audioRef.current.removeEventListener('ended', handleEnded);
                  }
                  resolve();
                };
                audioRef.current!.addEventListener('ended', handleEnded);
              });
            }
          } else {
            await speakMessage(timeUpMessage);
          }
        } catch (err) {
          console.error("Error getting time up message:", err);
        }
      }
      
      // Submit the interview after the message is spoken
      setTimeout(() => {
        handleSubmitInterview();
      }, 1000);
    } else {
      // For text mode, just submit directly
      handleSubmitInterview();
    }
  };

  // Initialize WebRTC
  useEffect(() => {
    if (interviewData && showVideo) {
      initializeWebRTC();
    }

    return () => {
      // Stop all media tracks
      if (localVideoRef.current && localVideoRef.current.srcObject) {
        const mediaStream = localVideoRef.current.srcObject as MediaStream;
        mediaStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [interviewData, showVideo]);

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

      // Create a mock video stream for the remote video
      const mockVideoStream = new MediaStream();
      
      // If we have a remote video element, set its source to the mock stream
      if (remoteVideoRef.current) {
        remoteVideoRef.current.srcObject = mockVideoStream;
      }
      
      // Set recording and video connected states
      setIsVideoConnected(true);
    } catch (err) {
      console.error('Error initializing WebRTC:', err);
      setError('Failed to access camera or microphone. Please check your permissions.');
      setShowVideo(false);
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

  const handleNextQuestion = async () => {
    if (!interviewData) return;
    
    // Don't allow moving to next question if currently processing or speaking
    if (isProcessing || isSpeaking || isRecording) {
      return;
    }
    
    if (currentQuestionIndex < interviewData.questions.length - 1) {
      const nextIndex = currentQuestionIndex + 1;
      setCurrentQuestionIndex(nextIndex);
      
      // If voice mode is enabled, speak the next question
      if (interviewData.useVoiceMode) {
        // Add the next question to the conversation
        const nextQuestion = interviewData.questions[nextIndex].question;
        const questionMessage = { role: 'assistant', content: nextQuestion };
        setMessages(prev => [...prev, questionMessage]);
        
        // Speak the next question
        await speakMessage(nextQuestion);
      }
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
    }
  };

  const handleSubmitInterview = async () => {
    if (!interviewData) return;
    
    // Don't allow submission while AI is speaking, unless time is up
    if (isSpeaking && timeLeft > 0) {
      setError('Please wait for the AI to finish speaking before submitting.');
      setTimeout(() => setError(''), 3000); // Clear error after 3 seconds
      return;
    }
    
    // Prevent multiple submission attempts
    if (isSubmitting) return;
    
    setIsSubmitting(true);
    setError('');
    
    try {
      // Stop all media tracks from camera and microphone
      if (localVideoRef.current && localVideoRef.current.srcObject) {
        const mediaStream = localVideoRef.current.srcObject as MediaStream;
        mediaStream.getTracks().forEach(track => track.stop());
      }
      
      // Format answers for submission
      // In voice mode, we may not have answered all predefined questions,
      // but we still submit what we have
      const formattedAnswers = Object.keys(answers).map(questionId => {
        const question = interviewData.questions.find(q => q.id === questionId);
        return {
          question_id: questionId,
          question: question?.question || '',
          answer: answers[questionId]
        };
      });
      
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
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to submit interview');
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
      console.error('Error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Voice mode functions
  const toggleRecording = async () => {
    // Prevent recording while AI is speaking
    if (isSpeaking) {
      return;
    }
    
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  };
  
  const startRecording = async () => {
    try {
      audioChunksRef.current = [];
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await processAudio(audioBlob);
      };
      
      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
    } catch (err) {
      setError('Failed to access microphone. Please check your permissions.');
      console.error(err);
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Stop all audio tracks
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };
  
  const processAudio = async (audioBlob: Blob) => {
    if (!interviewData) return;
    
    setIsProcessing(true);
    
    try {
      // Convert blob to base64
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      
      reader.onloadend = async () => {
        const base64Audio = reader.result as string;
        // Remove the data URL prefix (e.g., "data:audio/webm;base64,")
        const base64Data = base64Audio.split(',')[1];
        
        // Send to speech-to-text API
        const response = await fetch('http://localhost:8000/api/speech-to-text', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            audio: base64Data,
            language: 'en'
          }),
        });
        
        if (!response.ok) {
          throw new Error('Failed to transcribe audio');
        }
        
        const data = await response.json();
        const transcribedText = data.text;
        
        // Add user message to conversation
        const userMessage = { role: 'user', content: transcribedText };
        const updatedMessages = [...messages, userMessage];
        setMessages(updatedMessages);
        
        // Save the answer to the current question
        // We still need to track which question this answer belongs to for evaluation
        const currentQuestion = interviewData.questions[currentQuestionIndex];
        setAnswers(prev => ({
          ...prev,
          [currentQuestion.id]: transcribedText
        }));
        
        // Get AI response
        await getAIResponse(updatedMessages);
      };
    } catch (err) {
      setError('Failed to process audio. Please try again.');
      console.error(err);
      setIsProcessing(false);
    }
  };
  
  const getAIResponse = async (conversationHistory: Array<{ role: string; content: string }>) => {
    if (!interviewData) return;
    
    try {
      const response = await fetch('http://localhost:8000/api/interview/conversation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_title: interviewData.jobTitle,
          job_description: interviewData.jobDescription,
          conversation_history: conversationHistory,
          current_question_index: currentQuestionIndex
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to get AI response');
      }
      
      const data = await response.json();
      
      // Add AI response to conversation
      const aiMessage = { role: 'assistant', content: data.text };
      setMessages([...conversationHistory, aiMessage]);
      
      // Play the audio response
      if (data.audio) {
        const audioSrc = `data:audio/mp3;base64,${data.audio}`;
        if (audioRef.current) {
          audioRef.current.src = audioSrc;
          await audioRef.current.play();
          
          // Wait for audio to finish
          await new Promise<void>((resolve) => {
            const handleEnded = () => {
              if (audioRef.current) {
                audioRef.current.removeEventListener('ended', handleEnded);
              }
              resolve();
            };
            audioRef.current!.addEventListener('ended', handleEnded);
          });
        }
      } else {
        // If no audio in response, generate speech and wait for it to finish
        await speakMessage(data.text);
      }
      
      // We no longer automatically move to the next question
      // The AI's response already includes a question for the user to answer
      
    } catch (err) {
      setError('Failed to get AI response. Please try again.');
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };
  
  const speakMessage = async (text: string): Promise<void> => {
    try {
      setIsSpeaking(true);
      
      const response = await fetch('http://localhost:8000/api/text-to-speech', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text,
          voice: 'alloy'
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate speech');
      }
      
      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      
      if (audioRef.current) {
        return new Promise<void>((resolve) => {
          // Set up one-time event listener for this specific playback
          const handleEnded = () => {
            if (audioRef.current) {
              audioRef.current.removeEventListener('ended', handleEnded);
            }
            setIsSpeaking(false);
            resolve();
          };
          
          // We've already checked that audioRef.current exists in the outer if
          audioRef.current!.addEventListener('ended', handleEnded);
          audioRef.current!.src = audioUrl;
          audioRef.current!.play().catch(err => {
            console.error('Failed to play audio:', err);
            setIsSpeaking(false);
            resolve(); // Resolve anyway to prevent hanging
          });
        });
      }
      setIsSpeaking(false);
      return Promise.resolve(); // Return resolved promise if audioRef.current is null
    } catch (err) {
      console.error('Failed to speak message:', err);
      setIsSpeaking(false);
      return Promise.resolve(); // Return resolved promise on error
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
  const isVoiceMode = interviewData.useVoiceMode === true;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        {/* Header */}
        <div className="bg-gray-800 text-white p-4 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold">{interviewData.jobTitle} Interview</h1>
            <p className="text-sm text-gray-300">
              {interviewData.interviewType} interview - {interviewData.duration} minutes
              {isVoiceMode && " - Voice Mode"}
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <div className={`flex items-center ${timeLeft < 60 ? 'text-red-400' : 'text-white'}`}>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span className="font-mono">{formatTime(timeLeft)}</span>
            </div>
            {isVoiceMode && (
              <div className={`flex items-center ${isRecording ? 'text-red-400' : isSpeaking ? 'text-blue-400' : 'text-gray-400'}`}>
                <span className={`h-3 w-3 rounded-full ${isRecording ? 'bg-red-500 animate-pulse' : isSpeaking ? 'bg-blue-500 animate-pulse' : 'bg-gray-500'} mr-1`}></span>
                <span className="text-sm">{isRecording ? 'Recording' : isSpeaking ? 'AI Speaking' : 'Not Recording'}</span>
              </div>
            )}
            {showVideo && (
              <button 
                onClick={() => setShowVideo(false)}
                className="text-sm bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded"
              >
                Hide Video
              </button>
            )}
            {!showVideo && (
              <button 
                onClick={() => setShowVideo(true)}
                className="text-sm bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded"
              >
                Show Video
              </button>
            )}
          </div>
        </div>
        
        {/* Main content */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
          {/* Video section or Voice conversation */}
          <div className="bg-gray-100 rounded-lg p-4">
            {showVideo ? (
              <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden relative mb-4">
                {/* User's video as main display */}
                <video
                  ref={localVideoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                ></video>
                
                {/* AI interviewer overlay - small picture-in-picture */}
                <div className="absolute top-4 right-4 w-1/4 h-1/4 bg-gray-800 rounded overflow-hidden border-2 border-white">
                  <img 
                    src="/ai-interviewer-avatar.png" 
                    alt="AI Interviewer"
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      // Fallback if the avatar image doesn't exist
                      e.currentTarget.src = "https://via.placeholder.com/150?text=AI+Interviewer";
                    }}
                  />
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
                
                {/* Processing indicator overlay */}
                {isProcessing && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 text-white">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-2"></div>
                      <p>Processing your response...</p>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-64 overflow-y-auto bg-gray-50 rounded-lg mb-4 p-4">
                {messages.map((message, index) => (
                  <div 
                    key={index} 
                    className={`mb-4 p-3 rounded-lg ${
                      message.role === 'assistant' 
                        ? 'bg-blue-100 mr-12' 
                        : 'bg-green-100 ml-12'
                    }`}
                  >
                    <p className="text-sm font-semibold mb-1">
                      {message.role === 'assistant' ? 'AI Interviewer' : 'You'}
                    </p>
                    <p>{message.content}</p>
                  </div>
                ))}
                
                {isProcessing && (
                  <div className="flex justify-center items-center my-4">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                    <span className="ml-2 text-gray-600">Processing...</span>
                  </div>
                )}
              </div>
            )}
            
            {/* Voice controls or Question navigation */}
            {isVoiceMode ? (
              <div className="flex flex-col items-center">
                <button
                  onClick={toggleRecording}
                  disabled={isProcessing || isSpeaking || timeLeft === 0}
                  className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 ${
                    isRecording 
                      ? 'bg-red-600 hover:bg-red-700' 
                      : isSpeaking || timeLeft === 0
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-indigo-600 hover:bg-indigo-700'
                  } text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500`}
                >
                  {isRecording ? (
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <rect x="6" y="6" width="12" height="12" strokeWidth="2" />
                    </svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                  )}
                </button>
                <p className="text-sm text-gray-600 mb-2">
                  {isRecording 
                    ? 'Click to stop recording' 
                    : isSpeaking
                      ? 'Please wait for AI to finish speaking'
                      : timeLeft === 0
                        ? 'Time\'s up! Submitting interview...'
                        : 'Click to start recording your answer'}
                </p>
              </div>
            ) : (
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
            )}
          </div>
          
          {/* Question and answer section */}
          <div className="bg-gray-100 rounded-lg p-4 flex flex-col">
            <div className="mb-4">
              {isVoiceMode ? (
                <h2 className="text-lg font-semibold mb-2">
                  Voice Interview
                </h2>
              ) : (
                <>
                  <h2 className="text-lg font-semibold mb-2">
                    Question {currentQuestionIndex + 1}: {currentQuestion.type.charAt(0).toUpperCase() + currentQuestion.type.slice(1)}
                  </h2>
                  <p className="text-gray-800 p-3 bg-white rounded-lg border border-gray-200">
                    {currentQuestion.question}
                  </p>
                </>
              )}
            </div>
            
            <div className="flex-grow">
              {isVoiceMode ? (
                <div className="h-full min-h-[200px] p-3 border border-gray-300 rounded-lg bg-white overflow-y-auto">
                  <p className="text-gray-500 italic mb-2">Conversation Transcript:</p>
                  {messages.map((message, index) => (
                    <div key={index} className="mb-3">
                      <p className="font-semibold text-sm">
                        {message.role === 'assistant' ? 'AI Interviewer:' : 'You:'}
                      </p>
                      <p className={`pl-2 border-l-2 ${message.role === 'assistant' ? 'border-blue-400' : 'border-green-400'}`}>
                        {message.content}
                      </p>
                    </div>
                  ))}
                  {!messages.length && <p className="text-gray-400">No conversation yet</p>}
                </div>
              ) : (
                currentQuestion.type === 'coding' ? (
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
                )
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
            {isSubmitting 
              ? 'Submitting...' 
              : timeLeft === 0 
                ? 'Time\'s Up - Submitting...' 
                : 'Finish & Submit'}
          </button>
        </div>
      </div>
      
      {/* Hidden audio element for playing responses */}
      <audio ref={audioRef} className="hidden" />
    </div>
  );
} 