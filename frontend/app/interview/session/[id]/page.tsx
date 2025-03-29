'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useAuth } from '../../../../lib/auth-context';
import axios from 'axios';

// Add API base URL configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Dynamically import the Monaco Editor to avoid SSR issues
const MonacoEditor = dynamic(
  () => import('@monaco-editor/react'),
  { ssr: false }
);

interface Question {
  id: string;
  question: string;
  type: string;
  difficulty?: string; // basic, intermediate, advanced
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
  useVideoMode?: boolean;
  seniority_level?: string; // junior, mid, senior
}

export default function InterviewSession({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { getAccessToken } = useAuth();
  const [interviewData, setInterviewData] = useState<InterviewData | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [isVideoConnected, setIsVideoConnected] = useState(false);
  const [showVideo, setShowVideo] = useState(false);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [answeredQuestions, setAnsweredQuestions] = useState<Set<string>>(new Set());
  const [voiceModeEnabled, setVoiceModeEnabled] = useState(false);
  const [timeWarningShown, setTimeWarningShown] = useState(false);
  const [timeUpMessageShown, setTimeUpMessageShown] = useState(false);
  const [finalMessageSpoken, setFinalMessageSpoken] = useState(false);
  
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const conversationContainerRef = useRef<HTMLDivElement>(null);
  const localVideoStreamRef = useRef<MediaStream | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);

  // Load interview data from localStorage
  useEffect(() => {
    const loadInterviewData = async () => {
      try {
        // First check if we have the interview data in localStorage
        const storedData = localStorage.getItem('currentInterview');
        if (!storedData) {
          setError('Interview data not found. Please set up a new interview.');
          return;
        }
        
        const parsedData = JSON.parse(storedData);
        if (parsedData.id !== params.id) {
          setError('Interview ID mismatch. Please set up a new interview.');
          return;
        }

        console.log('Loading interview data:', parsedData);
        setInterviewData(parsedData);
        
        // Check if time's up message has been shown
        const timeUpShown = localStorage.getItem(`time_up_shown_${parsedData.id}`);
        if (timeUpShown) {
          setTimeUpMessageShown(true);
        }
        
        // Check if final message has been spoken
        const finalMessageSpokenFromStorage = localStorage.getItem(`final_message_spoken_${parsedData.id}`);
        if (finalMessageSpokenFromStorage) {
          setFinalMessageSpoken(true);
        }
        
        // Set voice mode based on interview data
        setVoiceModeEnabled(parsedData.useVoiceMode === true);
        
        // Check if we have a stored question index for this interview
        const storedQuestionIndex = localStorage.getItem(`interview_question_${params.id}`);
        if (storedQuestionIndex) {
          setCurrentQuestionIndex(parseInt(storedQuestionIndex, 10));
        }
        
        // Check if we have a stored timer value for this interview
        const storedTimerData = localStorage.getItem(`interview_timer_${params.id}`);
        
        if (storedTimerData) {
          // If we have stored timer data, use it
          const { remainingTime, lastUpdated } = JSON.parse(storedTimerData);
          
          // Calculate how much time has passed since the timer was last updated
          const timeElapsed = Math.floor((Date.now() - lastUpdated) / 1000);
          
          // Calculate the new remaining time, ensuring it doesn't go below 0
          const newTimeLeft = Math.max(0, remainingTime - timeElapsed);
          
          // Set the timer to the calculated value
          setTimeLeft(newTimeLeft);
          
          // If time is up, handle it
          if (newTimeLeft === 0) {
            handleTimeUp();
          }
        } else {
          // If no stored timer data, initialize with the full duration
          setTimeLeft(parsedData.duration * 60); // Convert minutes to seconds
        }
        
        // Set video state based on useVideoMode setting
        setShowVideo(parsedData.useVideoMode === true);
        
        // Initialize answers object
        const initialAnswers: Record<string, string> = {};
        parsedData.questions.forEach((q: Question) => {
          initialAnswers[q.id] = '';
        });
        setAnswers(initialAnswers);

        // Initialize messages with first question for both voice and text mode
        // Only do this if messages is empty (first load)
        if (messages.length === 0) {
          let initialMessage;
          
          if (parsedData.useVoiceMode) {
            initialMessage = { 
              role: 'assistant', 
              content: `Hello! I'll be your AI interviewer today. Let's start with the first question: ${parsedData.questions[0].question}` 
            };
          } else {
            // For text mode, include a note about answering as many questions as possible
            const seniorityLevel = parsedData.seniority_level || 'appropriate';
            initialMessage = { 
              role: 'assistant', 
              content: `Welcome to your interview! This is a ${seniorityLevel}-level interview based on the job description you provided. You have ${parsedData.duration} minutes to answer as many questions as you can. The questions are tailored to the seniority level of the position. Let's begin with the first question: ${parsedData.questions[0].question}` 
            };
          }
          
          // Set the messages state with the initial message
          setMessages([initialMessage]);
          
          // Play the greeting message if voice mode is enabled
          // Use a separate useEffect for this to avoid re-renders
        }
      } catch (err) {
        console.error('Error loading interview data:', err);
        setError('Failed to load interview data. Please set up a new interview.');
      }
    };
    
    loadInterviewData();
  }, [params.id]);

  // Separate effect for playing the greeting message
  useEffect(() => {
    // Only run this effect if we have interview data and messages
    if (!interviewData || messages.length === 0) return;
    
    // Only play greeting for voice mode
    if (interviewData.useVoiceMode) {
      // Check if we've already played the greeting for this interview
      const greetingPlayed = localStorage.getItem(`greeting_played_${interviewData.id}`);
      
      if (!greetingPlayed) {
        // Mark that we've played the greeting immediately to prevent duplicates
        localStorage.setItem(`greeting_played_${interviewData.id}`, 'true');
        
        // Use setTimeout to ensure the component is fully mounted before playing audio
        setTimeout(() => {
          // Get the first message which should be the greeting
          const initialMessage = messages[0];
          if (initialMessage && initialMessage.role === 'assistant') {
            speakMessage(initialMessage.content).catch(err => {
              console.error('Error playing greeting message:', err);
            });
          }
        }, 1000);
      }
    }
  }, [interviewData, messages]);

  // Add audio ended event listener
  useEffect(() => {
    // This effect is no longer needed as we're using the onEnded prop on the audio element
    // The handleAudioEnded function is defined below and used directly in the audio element
  }, []);

  // Timer countdown
  useEffect(() => {
    if (timeLeft > 0 && interviewData) {
      timerRef.current = setInterval(() => {
        setTimeLeft(prev => {
          // Store the updated timer value in localStorage
          localStorage.setItem(`interview_timer_${interviewData.id}`, JSON.stringify({
            remainingTime: prev - 1,
            lastUpdated: Date.now()
          }));
          
          // Show time warning when 2 minutes are left (exactly 120 seconds)
          if (prev === 121) { // Check at 121 so it triggers when changing to 120
            console.log("Triggering time warning at 2 minutes remaining");
            
            // Check if time warning has already been handled
            const timeWarningHandledKey = `interview_time_warning_handled_${interviewData.id}`;
            const timeWarningHandled = localStorage.getItem(timeWarningHandledKey) === 'true';
            
            if (!timeWarningHandled && !isSubmitting && !isSpeaking && !isProcessing) {
              handleTimeWarning();
            } else {
              console.log("Skipping time warning - already handled or busy state");
            }
          }
          
          // Handle time up when timer reaches 0
          if (prev === 1) {
            console.log("Triggering time up at 0 seconds remaining");
            
            // Check if time up has already been handled
            const timeUpHandledKey = `interview_time_up_handled_${interviewData.id}`;
            const timeUpHandled = localStorage.getItem(timeUpHandledKey) === 'true';
            
            if (!timeUpHandled && !isSubmitting) {
              handleTimeUp();
            } else {
              console.log("Skipping time up - already handled or submitting");
            }
          }
          
          return prev - 1;
        });
      }, 1000);
    } else if (timeLeft === 0 && interviewData) {
      // Check if time up has already been handled
      const timeUpHandledKey = `interview_time_up_handled_${interviewData.id}`;
      const timeUpHandled = localStorage.getItem(timeUpHandledKey) === 'true';
      
      if (!timeUpHandled && !isSubmitting) {
        console.log("Triggering time up at timeLeft === 0");
        handleTimeUp();
      } else {
        console.log("Skipping time up at timeLeft === 0 - already handled or submitting");
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [timeLeft, interviewData, isSubmitting, isSpeaking, isProcessing]);

  // Handle time warning when 2 minutes are left
  const handleTimeWarning = async () => {
    if (!interviewData) return;
    
    console.log("Handling time warning at 2 minutes remaining");
    
    // Check if time warning has already been handled
    const timeWarningHandledKey = `interview_time_warning_handled_${interviewData.id}`;
    const timeWarningHandled = localStorage.getItem(timeWarningHandledKey) === 'true';
    
    if (timeWarningHandled) {
      console.log("Time warning already handled, skipping duplicate");
      return;
    }
    
    // For voice mode, use getAIResponse to get a time warning message
    if (interviewData.useVoiceMode && !isSubmitting && !isSpeaking && !isProcessing) {
      console.log("Getting time warning message via getAIResponse");
      
      try {
        // IMPORTANT: Do NOT set the flag before the API call
        // This ensures the time_running_low flag is properly passed to the backend
        
        // Use getAIResponse with time_running_low flag
        await getAIResponse(
          messages,
          false, // not an empty response
          false, // not a code submission
          false  // don't include follow-up questions
        );
        
        // Set the flag AFTER successful API call
        localStorage.setItem(timeWarningHandledKey, 'true');
        console.log("Time warning handled successfully, flag set");
      } catch (error) {
        console.error("Error getting time warning message:", error);
        // Still set the flag to prevent repeated attempts that might fail
        localStorage.setItem(timeWarningHandledKey, 'true');
      }
    } else {
      console.log("Skipping voice time warning due to current state");
      // Set the flag even if we skip the warning to prevent repeated checks
      localStorage.setItem(timeWarningHandledKey, 'true');
    }
  };

  // Single source of truth for handling time up scenario
  const handleTimeUp = async () => {
    if (!interviewData) return;
    
    console.log("Handling time up");
    
    // Check if time up has already been handled
    const timeUpHandledKey = `interview_time_up_handled_${interviewData.id}`;
    const timeUpHandled = localStorage.getItem(timeUpHandledKey) === 'true';
    
    if (timeUpHandled) {
      console.log("Time up already handled, skipping duplicate");
      return;
    }
    
    // Clear timer and question index data from localStorage
    localStorage.removeItem(`interview_timer_${interviewData.id}`);
    localStorage.removeItem(`interview_question_${interviewData.id}`);
    
    // For voice mode, use getAIResponse to get a time up message
    if (interviewData.useVoiceMode && !isSubmitting && !isSpeaking && !isProcessing) {
      console.log("Getting time up message via getAIResponse");
      
      try {
        // IMPORTANT: Do NOT set the flag before the API call
        // This ensures the time_up flag is properly passed to the backend
        
        // Use getAIResponse with time_up flag
        await getAIResponse(
          messages,
          false, // not an empty response
          false, // not a code submission
          false  // don't include follow-up questions
        );
        
        // Set the flag AFTER successful API call
        localStorage.setItem(timeUpHandledKey, 'true');
        console.log("Time up handled successfully, flag set");
        
        // Wait for audio to finish before submitting
        await new Promise(resolve => setTimeout(resolve, 5000));
      } catch (error) {
        console.error("Error getting time up message:", error);
        // Still set the flag to prevent repeated attempts that might fail
        localStorage.setItem(timeUpHandledKey, 'true');
      }
    } else {
      console.log("Skipping voice time up message due to current state");
      // Set the flag even if we skip the message
      localStorage.setItem(timeUpHandledKey, 'true');
    }
    
    // Submit the interview after a short delay to ensure audio is finished
    setTimeout(() => {
      handleSubmitInterview();
    }, interviewData.useVoiceMode ? 3000 : 1000);
  };

  // Initialize WebRTC
  useEffect(() => {
    let mounted = true;
    
    if (interviewData && showVideo) {
      // Use a small delay to ensure DOM is fully rendered
      const initTimer = setTimeout(() => {
        if (mounted) {
          initializeWebRTC().catch(err => {
            console.error('Failed to initialize WebRTC in useEffect:', err);
          });
        }
      }, 500);
      
      return () => {
        mounted = false;
        clearTimeout(initTimer);
        
        // Stop all media tracks
        if (localVideoRef.current && localVideoRef.current.srcObject) {
          const mediaStream = localVideoRef.current.srcObject as MediaStream;
          
          // First disable tracks before stopping them
          mediaStream.getTracks().forEach(track => {
            track.enabled = false;
          });
          
          // Small delay before stopping tracks
          setTimeout(() => {
            if (mediaStream) {
              mediaStream.getTracks().forEach(track => {
                track.stop();
                console.log(`Cleanup: Stopped track: ${track.kind}, enabled: ${track.enabled}, readyState: ${track.readyState}`);
              });
            }
            
            // Clear the srcObject to fully release the camera
            if (localVideoRef.current) {
              localVideoRef.current.srcObject = null;
            }
          }, 100);
        }
        
        // Also stop any recording if active
        if (mediaRecorderRef.current && isRecording) {
          try {
            mediaRecorderRef.current.stop();
            mediaRecorderRef.current.stream.getTracks().forEach(track => {
              track.enabled = false;
              setTimeout(() => track.stop(), 100);
            });
          } catch (err) {
            console.error('Error stopping recording during cleanup:', err);
          }
        }
      };
    }
  }, [interviewData, showVideo, isRecording]);

  const initializeWebRTC = async () => {
    try {
      // Only initialize camera if video is enabled
      if (!showVideo) {
        return;
      }
      
      // If we already have a video stream, reuse it instead of requesting a new one
      if (localVideoStreamRef.current && localVideoRef.current) {
        // Check if any tracks are active before reusing
        const hasActiveTracks = localVideoStreamRef.current.getVideoTracks().some(track => 
          track.readyState === 'live' && !track.muted
        );
        
        if (hasActiveTracks) {
          console.log('Reusing existing video stream');
          localVideoRef.current.srcObject = localVideoStreamRef.current;
          setIsVideoConnected(true);
          return;
        }
      }
      
      // Get user media (camera only) with specific constraints for stability
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 }
        },
        audio: false // Don't request audio in video stream, keep them separate
      });
      
      if (localVideoRef.current) {
        // Store the stream in a ref to maintain it across renders
        localVideoStreamRef.current = mediaStream;
        localVideoRef.current.srcObject = mediaStream;
      }

      // Set video connected state
      setIsVideoConnected(true);
    } catch (err) {
      console.error('Error initializing WebRTC:', err);
      setError('Failed to access camera. Please check your permissions.');
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

  const handleSubmitAnswer = async () => {
    if (!interviewData) return;
    
    // Don't allow submission while AI is speaking or processing
    if (isSpeaking || isProcessing || isRecording) {
      console.log('Cannot submit answer: isSpeaking:', isSpeaking, 'isProcessing:', isProcessing, 'isRecording:', isRecording);
      return;
    }
    
    const currentQuestion = interviewData.questions[currentQuestionIndex];
    const answer = answers[currentQuestion.id];
    
    // Don't allow resubmission if already answered
    if (answeredQuestions.has(currentQuestion.id)) {
      setError('You have already submitted an answer for this question.');
      setTimeout(() => setError(''), 3000);
      return;
    }
    
    if (!answer || answer.trim() === '') {
      setError('Please provide an answer before submitting.');
      setTimeout(() => setError(''), 3000);
      return;
    }
    
    console.log('Setting isProcessing to true');
    setIsProcessing(true);
    
    try {
      // In text mode, we don't need to use the conversation API
      // Just store the answer and mark the question as answered
      
      // For voice mode, we still need to update the conversation
      if (interviewData.useVoiceMode) {
        // Add user message with answer to conversation
        const userMessage = { 
          role: 'user', 
          content: answer
        };
        
        // Update the conversation with the user's answer
        const updatedMessages = [...messages, userMessage];
        setMessages(updatedMessages);
        
        // Get AI response with the answer
        // Always include follow-up questions in voice mode
        const includeFollowUp = true;
        await getAIResponse(updatedMessages, false, false, includeFollowUp);
      } else {
        // For text mode, just add a simple AI acknowledgment message
        const userMessage = { role: 'user', content: answer };
        const aiMessage = { 
          role: 'assistant', 
          content: `Thank you for your answer. ${currentQuestionIndex < interviewData.questions.length - 1 ? 'Please proceed to the next question when ready.' : 'You have completed all questions. You can now submit the interview for evaluation.'}`
        };
        
        setMessages([...messages, userMessage, aiMessage]);
      }
      
      // Mark this question as answered
      setAnsweredQuestions(prev => {
        const updated = new Set(prev);
        updated.add(currentQuestion.id);
        return updated;
      });
      
    } catch (err) {
      setError('Failed to submit answer. Please try again.');
      console.error(err);
    } finally {
      console.log('Setting isProcessing to false in handleSubmitAnswer finally block');
      setIsProcessing(false);
    }
  };

  const handleSubmitCode = async () => {
    if (!interviewData) return;
    
    // Don't allow submission while AI is speaking or processing
    if (isSpeaking || isProcessing) {
      return;
    }
    
    const currentQuestion = interviewData.questions[currentQuestionIndex];
    const codeAnswer = answers[currentQuestion.id];
    
    if (!codeAnswer || codeAnswer.trim() === '' || codeAnswer.trim() === '// Write your code here') {
      setError('Please write some code before submitting.');
      setTimeout(() => setError(''), 3000);
      return;
    }
    
    // Don't allow resubmission if already answered
    if (answeredQuestions.has(currentQuestion.id)) {
      setError('You have already submitted code for this question.');
      setTimeout(() => setError(''), 3000);
      return;
    }
    
    setIsProcessing(true);
    
    try {
      // Format the code answer with markdown code block
      const formattedCodeAnswer = `Here's my code for the question "${currentQuestion.question}":\n\n\`\`\`javascript\n${codeAnswer}\n\`\`\``;
      
      // Add user message with code to conversation
      const userMessage = { 
        role: 'user', 
        content: formattedCodeAnswer
      };
      
      // In text mode, we don't need to use the conversation API
      // Just store the answer and mark the question as answered
      if (!interviewData.useVoiceMode) {
        // For text mode, just add a simple AI acknowledgment message
        const aiMessage = { 
          role: 'assistant', 
          content: `Thank you for submitting your code. ${currentQuestionIndex < interviewData.questions.length - 1 ? 'Please proceed to the next question when ready.' : 'You have completed all questions. You can now submit the interview for evaluation.'}`
        };
        
        setMessages([...messages, userMessage, aiMessage]);
      } else {
        // For voice mode, we still need to update the conversation
        const updatedMessages = [...messages, userMessage];
        setMessages(updatedMessages);
        
        // Get AI response with code analysis
        await getAIResponse(updatedMessages, false, true);
      }
      
      // Mark this question as answered
      setAnsweredQuestions(prev => {
        const updated = new Set(prev);
        updated.add(currentQuestion.id);
        return updated;
      });
    } catch (err) {
      setError('Failed to submit code. Please try again.');
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleNextQuestion = async () => {
    console.log('handleNextQuestion called, current state:', {
      voiceModeEnabled,
      isSpeaking,
      isRecording,
      isProcessing,
      currentQuestionIndex,
      totalQuestions: interviewData?.questions.length
    });
    
    if (!interviewData) return;
    
    // If we're at the last question, show a message that more questions could be generated
    if (currentQuestionIndex >= interviewData.questions.length - 1) {
      console.log('At last question, showing message about more questions');
      
      // Add a message to the conversation indicating more questions are available
      if (!voiceModeEnabled && !messages.some(m => m.content.includes("You've reached the end of the prepared questions"))) {
        const moreQuestionsMessage = { 
          role: 'assistant', 
          content: "You've reached the end of the prepared questions. Continue answering until your time runs out. The interview will automatically end when the timer reaches zero." 
        };
        setMessages(prev => [...prev, moreQuestionsMessage]);
      }
      
      return;
    }
    
    // If there's an answer for the current question but it hasn't been submitted yet, submit it first
    const currentQuestion = interviewData.questions[currentQuestionIndex];
    const answer = answers[currentQuestion.id];
    
    // Force reset isProcessing if it's been true for too long
    if (isProcessing) {
      console.log('Force resetting isProcessing before navigation');
      setIsProcessing(false);
    }
    
    // Only try to submit if the answer exists and hasn't been submitted yet
    if (answer && answer.trim() !== '' && !isProcessing && !answeredQuestions.has(currentQuestion.id)) {
      console.log('Submitting answer before navigating');
      await handleSubmitAnswer();
    }
    
    console.log('Advancing to next question');
    // Advance to the next question
    const nextIndex = currentQuestionIndex + 1;
    setCurrentQuestionIndex(nextIndex);
    
    // If in voice mode, speak the next question
    if (voiceModeEnabled) {
      const nextQuestion = interviewData.questions[nextIndex].question;
      if (nextQuestion) {
        await speakMessage(nextQuestion);
      }
    } else {
      // In text mode, add the next question to the conversation
      const nextQuestion = interviewData.questions[nextIndex].question;
      const questionMessage = { role: 'assistant', content: nextQuestion || '' };
      setMessages(prev => [...prev, questionMessage]);
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      // Check if the current question has been answered
      const currentQuestion = interviewData?.questions[currentQuestionIndex];
      const previousQuestion = interviewData?.questions[currentQuestionIndex - 1];
      
      if (currentQuestion && previousQuestion) {
        const previousAnswer = answers[previousQuestion.id];
        
        // Only allow going back if the previous question hasn't been answered yet
        if (!previousAnswer || previousAnswer.trim() === '') {
          setCurrentQuestionIndex(prev => prev - 1);
        } else {
          // Show an error message if trying to go back to an answered question
          setError("You can't go back to a question after submitting an answer.");
          setTimeout(() => setError(''), 3000);
        }
      }
    }
  };

  const handleSubmitInterview = async () => {
    if (!interviewData) return;
    
    // Prevent multiple submission attempts
    if (isSubmitting) {
      console.log("Already submitting, skipping duplicate submission");
      return;
    }
    
    // Check if evaluation has already been generated for this interview
    const evaluationGeneratedKey = `interview_evaluation_generated_${interviewData.id}`;
    const evaluationGenerated = localStorage.getItem(evaluationGeneratedKey);
    
    if (evaluationGenerated) {
      console.log('Evaluation already generated, skipping duplicate submission');
      // Just navigate to results page
      router.push(`/interview/results/${interviewData.id}`);
      return;
    }
    
    console.log("Starting interview submission process");
    setIsSubmitting(true);
    setError('');
    
    // Set the flag at the beginning of the evaluation process to prevent duplicates
    localStorage.setItem(evaluationGeneratedKey, 'true');
    
    // Wait for any ongoing speech to finish before proceeding
    if (isSpeaking) {
      console.log("Waiting for speech to finish before submitting...");
      // Wait up to 5 seconds for speech to finish
      for (let i = 0; i < 10; i++) {
        if (!isSpeaking) break;
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
    
    // Ensure all audio is stopped
    if (audioRef.current) {
      try {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        if (audioRef.current.src) {
          URL.revokeObjectURL(audioRef.current.src);
          audioRef.current.src = '';
        }
      } catch (e) {
        console.error("Error stopping audio:", e);
      }
    }
    
    // Stop any browser speech synthesis that might be running
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    
    // Clear all interview-related flags from localStorage
    localStorage.removeItem(`interview_timer_${interviewData.id}`);
    localStorage.removeItem(`interview_question_${interviewData.id}`);
    localStorage.removeItem(`interview_time_warning_handled_${interviewData.id}`);
    localStorage.removeItem(`interview_time_up_handled_${interviewData.id}`);
    
    try {
      // Clean up all media before navigation
      cleanupMedia();
      
      // Format answers for submission
      let formattedAnswers;
      
      if (interviewData.useVoiceMode) {
        // For voice mode, extract answers from the conversation history
        const conversationAnswers: Record<string, string> = {};
        
        // Initialize with empty answers
        interviewData.questions.forEach(q => {
          conversationAnswers[q.id] = '';
        });
        
        // Process the conversation to extract user responses
        let currentQuestionId = '';
        let currentAnswer = '';
        
        // First, identify all questions in the conversation
        const questionMap = new Map();
        interviewData.questions.forEach(q => {
          questionMap.set(q.question, q.id);
        });
        
        // Then process the conversation to extract answers
        for (let i = 0; i < messages.length; i++) {
          const msg = messages[i];
          
          if (msg.role === 'assistant') {
            // Find which question this is
            for (const [questionText, questionId] of questionMap.entries()) {
              if (msg.content.includes(questionText)) {
                currentQuestionId = questionId;
                currentAnswer = ''; // Reset the answer for this question
                
                // Look ahead for user responses to this question
                let j = i + 1;
                while (j < messages.length && j < messages.length - 1) {
                  // Only process user messages
                  if (messages[j].role === 'user') {
                    if (currentAnswer) {
                      currentAnswer += ' ' + messages[j].content;
                    } else {
                      currentAnswer = messages[j].content;
                    }
                  }
                  
                  j++;
                  
                  // Stop if we encounter another question from the assistant
                  if (j < messages.length && messages[j].role === 'assistant') {
                    let isNextQuestion = false;
                    for (const [qText, qId] of questionMap.entries()) {
                      if (messages[j].content.includes(qText)) {
                        isNextQuestion = true;
                        break;
                      }
                    }
                    if (isNextQuestion) break;
                  }
                }
                
                // Store the answer for this question
                if (currentAnswer) {
                  conversationAnswers[currentQuestionId] = currentAnswer;
                  console.log(`Extracted answer for question ${currentQuestionId}: ${currentAnswer.substring(0, 50)}...`);
                }
                
                break;
              }
            }
          }
        }
        
        // Format the conversation answers
        formattedAnswers = interviewData.questions.map(question => ({
          question_id: question.id,
          question: question.question,
          question_type: question.type,
          answer: conversationAnswers[question.id] || answers[question.id] || 'No answer provided'
        }));
        
        console.log('Voice mode answers extracted from conversation:', formattedAnswers);
      } else {
        // For text mode, use the answers state directly
        formattedAnswers = interviewData.questions.map(question => ({
          question_id: question.id,
          question: question.question,
          question_type: question.type,
          answer: answers[question.id] || 'No answer provided'
        }));
      }
      
      // Try to get the evaluation from the API first
      let evaluationData = null;
      
      try {
        // Get authentication token
        const token = await getAccessToken();
        const headers = {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        };
        
        console.log('Making request to API with headers:', Object.keys(headers));
        
        // Make the API request - this will try OpenAI first, then DeepSeek as fallback
        const response = await fetch(`${API_BASE_URL}/api/interview/feedback`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            interview_id: interviewData.id,
            answers: formattedAnswers,
            job_title: interviewData.jobTitle,
            interview_type: interviewData.interviewType,
            questions: interviewData.questions, // Include the questions in the evaluation request
            conversation_history: interviewData.useVoiceMode ? 
              // Filter out system messages and format conversation history
              messages.filter(msg => msg.role !== 'system').map(msg => ({
                role: msg.role,
                content: msg.content
              })) : 
              undefined // Include conversation history for voice mode
          }),
        });
        
        console.log('API response status:', response.status);
        
        if (response.ok) {
          evaluationData = await response.json();
          console.log('Successfully received evaluation data from API (OpenAI or DeepSeek)');
        } else {
          console.error('Failed to get evaluation from API (both OpenAI and DeepSeek failed), falling back to local evaluation');
        }
      } catch (apiError) {
        console.error('Error calling evaluation API:', apiError);
      }
      
      // If API evaluation failed (both OpenAI and DeepSeek), use local evaluation as last resort fallback
      if (!evaluationData) {
        console.log('Using local evaluation as last resort fallback (both OpenAI and DeepSeek failed)');
        evaluationData = await generateLocalEvaluation(formattedAnswers);
      }
      
      // Store the evaluation data
      if (evaluationData) {
        localStorage.setItem(`interview_evaluation_${interviewData.id}`, JSON.stringify({
          interviewId: interviewData.id,
          jobTitle: interviewData.jobTitle,
          interviewType: interviewData.interviewType,
          timestamp: new Date().toISOString(), // Add timestamp to track when this evaluation was created
          ...evaluationData
        }));
        
        // Also store the latest evaluation ID for easy access
        localStorage.setItem('latestInterviewEvaluation', interviewData.id || '');
      }
      
      // Clean up media again before navigation to ensure everything is released
      cleanupMedia();
      
      // Navigate to results page
      router.push(`/interview/results/${interviewData.id}`);
    } catch (err) {
      console.error('Error submitting interview:', err);
      setError('Failed to submit interview. Please try again.');
      setIsSubmitting(false);
      
      // Remove the evaluation generated flag so the user can try again
      localStorage.removeItem(evaluationGeneratedKey);
    }
  };

  // Function to generate a local evaluation as a last resort fallback when both OpenAI and DeepSeek evaluations fail
  const generateLocalEvaluation = async (formattedAnswers: any[]) => {
    const isTextMode = !interviewData?.useVoiceMode;
    
    // Check if all answers are empty or meaningless
    const hasEmptyAnswers = formattedAnswers.every(answer => {
      // Check if answer is empty, just whitespace, or a default placeholder
      const answerText = answer.answer || '';
      const trimmedAnswer = answerText.trim();
      
      // Consider answers empty if they are:
      // - Empty strings
      // - Just whitespace
      // - Default placeholders like "No answer provided"
      // - Just a few characters (likely not meaningful)
      // - Just code comments or placeholders
      return (
        !trimmedAnswer || 
        trimmedAnswer === 'No answer provided' ||
        trimmedAnswer === '// Write your code here' ||
        trimmedAnswer.length < 5 ||
        /^\/\/.*$/.test(trimmedAnswer) || // Just a comment
        /^s\.\s*s\s*sdd$/.test(trimmedAnswer) // The specific "s. s sdd" text seen in the screenshot
      );
    });
    
    // Check if answers are nonsensical (random characters, very short, etc.)
    const hasNonsensicalAnswers = formattedAnswers.every(answer => {
      const answerText = answer.answer || '';
      const trimmedAnswer = answerText.trim();
      
      // Skip empty answers
      if (!trimmedAnswer || trimmedAnswer.length < 5) {
        return true;
      }
      
      // Check if answer has actual words (at least 3 words with 3+ characters each)
      const words = trimmedAnswer.split(/\s+/).filter((word: string) => word.length >= 3);
      const hasRealWords = words.length >= 3;
      
      // Check if answer is mostly random characters
      const hasRandomChars = /^[a-z]{5,}$/.test(trimmedAnswer) || // Random lowercase letters
                            /^[a-zA-Z]{5,}$/.test(trimmedAnswer) || // Random mixed case letters
                            /^[a-z\s]{5,}$/.test(trimmedAnswer); // Random lowercase letters with spaces
      
      // Answer is nonsensical if it doesn't have real words or has random characters
      return !hasRealWords || hasRandomChars;
    });
    
    console.log('All answers empty:', hasEmptyAnswers);
    console.log('All answers nonsensical:', hasNonsensicalAnswers);
    
    // If all answers are empty or nonsensical, force a score of 0
    const forceZeroScore = hasEmptyAnswers || hasNonsensicalAnswers;
    
    try {
      // If all answers are empty or nonsensical, return a zero score evaluation
      if (forceZeroScore) {
        return {
          score: 0,
          feedback: "The candidate did not provide substantive answers to the interview questions. The responses were either empty, too short, or consisted of random characters that did not address the questions.",
          strengths: [],
          areas_for_improvement: [
            "Providing substantive responses to interview questions",
            "Demonstrating knowledge and skills relevant to the position",
            "Engaging meaningfully with the interview questions"
          ],
          recommendations: [
            "Prepare answers to common interview questions in advance",
            "Practice articulating thoughts clearly and concisely",
            "Research the company and position before interviews"
          ]
        };
      }

      // For non-empty answers, return an error message since both API evaluations failed
      return {
        score: 50, // Neutral score
        feedback: "We encountered technical difficulties while evaluating your interview. This is a system-generated fallback evaluation as both our primary and secondary evaluation services were unavailable. Please consider retaking the interview for a more accurate assessment.",
        strengths: [
          "Interview completed successfully",
          "Answers were provided for the questions"
        ],
        areas_for_improvement: [
          "Technical issues prevented a complete evaluation",
          "Consider retaking the interview for a more accurate assessment"
        ],
        recommendations: [
          "Try the interview again with a stable connection",
          "Contact support if this issue persists"
        ]
      };
    } catch (error) {
      console.error('Error in generateLocalEvaluation:', error);
      
      // Return a basic error message if there's an exception
      return {
        score: forceZeroScore ? 0 : 50,
        feedback: "We encountered an error while evaluating your interview. This is a system-generated fallback evaluation as our evaluation services were unavailable.",
        strengths: [
          "Interview completed successfully"
        ],
        areas_for_improvement: [
          "Technical issues prevented a complete evaluation",
          "Consider retaking the interview for a more accurate assessment"
        ],
        recommendations: [
          "Try the interview again with a stable connection",
          "Contact support if this issue persists"
        ]
      };
    }
  };

  // Voice mode functions
  const toggleRecording = async () => {
    // Prevent recording while AI is speaking or processing
    if (isSpeaking || isProcessing) {
      console.log('Cannot toggle recording while AI is speaking or processing');
      return;
    }
    
    // Prevent rapid toggling by setting processing state
    setIsProcessing(true);
    
    try {
      if (isRecording) {
        stopRecording();
      } else {
        await startRecording();
      }
    } catch (err) {
      console.error('Error toggling recording:', err);
      setError('Failed to toggle recording.');
      setIsProcessing(false);
    }
  };
  
  // Fix the startRecording function to make it independent of video
  const startRecording = async () => {
    try {
      // If already recording, don't do anything
      if (isRecording || mediaRecorderRef.current) {
        console.log('Already recording, ignoring duplicate start request');
        return;
      }
      
      // Reset audio chunks
      audioChunksRef.current = [];
      
      // Set a flag to indicate we're initializing recording
      // This prevents UI flicker
      setIsProcessing(true);
      
      try {
        // Always get a fresh audio stream, independent of video
        const audioStream = await navigator.mediaDevices.getUserMedia({ 
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          } 
        });
        
        // Store the audio stream in its own ref
        audioStreamRef.current = audioStream;
        
        // Create a new MediaRecorder instance with the audio stream
        const mediaRecorder = new MediaRecorder(audioStream, {
          mimeType: 'audio/webm'
        });
        
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };
        
        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          await processAudio(audioBlob);
        };
        
        // Start recording
        mediaRecorder.start();
        mediaRecorderRef.current = mediaRecorder;
        setIsRecording(true);
        
        console.log('Started recording audio with separate stream');
      } catch (err) {
        console.error('Error starting recording:', err);
        setError('Failed to access microphone. Please check your permissions.');
      } finally {
        // Always clear the processing state
        setIsProcessing(false);
      }
    } catch (err) {
      setError('Failed to access microphone. Please check your permissions.');
      console.error('Error in startRecording:', err);
      setIsProcessing(false);
    }
  };
  
  // Fix the stopRecording function to make it independent of video
  const stopRecording = () => {
    if (!mediaRecorderRef.current || !isRecording) {
      console.log('Not recording, ignoring stop request');
      return;
    }
    
    try {
      // Set processing flag to prevent UI flicker
      setIsProcessing(true);
      
      try {
        // Stop the media recorder
        mediaRecorderRef.current.stop();
        
        // Stop only the audio tracks from the recorder
        if (audioStreamRef.current) {
          // First disable tracks before stopping to prevent visual glitches
          audioStreamRef.current.getTracks().forEach(track => {
            track.enabled = false;
          });
          
          // Small delay before stopping tracks
          setTimeout(() => {
            if (audioStreamRef.current) {
              audioStreamRef.current.getTracks().forEach(track => {
                track.stop();
              });
              // Clear the audio stream reference
              audioStreamRef.current = null;
            }
            
            // Clear the media recorder reference
            mediaRecorderRef.current = null;
          }, 100);
        }
        
        // Update recording state
        setIsRecording(false);
      } catch (err) {
        console.error('Error stopping recording:', err);
        setError('Failed to stop recording.');
        setIsRecording(false);
      } finally {
        // Clear processing state after a short delay
        setTimeout(() => {
          setIsProcessing(false);
        }, 300);
      }
    } catch (err) {
      console.error('Error in stopRecording:', err);
      setError('Failed to stop recording.');
      setIsRecording(false);
      setIsProcessing(false);
    }
  };
  
  const processAudio = async (audioBlob: Blob) => {
    try {
      console.log('Processing audio blob:', audioBlob.size, 'bytes, type:', audioBlob.type);
      setIsProcessing(true);
      
      // Convert the blob to base64
      const reader = new FileReader();
      
      reader.onload = async (event) => {
        try {
          if (!event.target || !event.target.result) {
            throw new Error('Failed to read audio data');
          }
          
          // Get the base64 data
          const base64Data = (event.target.result as string).split(',')[1];
          
          // Prepare headers
          let headers: Record<string, string> = {
            'Content-Type': 'application/json',
          };
          
          try {
            const token = await getAccessToken();
            if (token) {
              headers['Authorization'] = `Bearer ${token}`;
            }
          } catch (err) {
            console.error('Error getting access token:', err);
            handleAuthError();
            setIsProcessing(false);
            return;
          }
          
          // Send to speech-to-text API
          const response = await fetch(`${API_BASE_URL}/api/speech-to-text`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
              audio: base64Data,
              language: 'en'
            }),
          });
          
          if (!response.ok) {
            const errorText = await response.text();
            console.error('Speech-to-text API error:', errorText);
            
            // Handle authentication error
            if (response.status === 401) {
              handleAuthError();
              setIsProcessing(false);
              return;
            }
            
            throw new Error(`Failed to transcribe audio: ${response.status} ${response.statusText}`);
          }
          
          const data = await response.json();
          let transcribedText = data.text.trim();
          
          // If we got a transcription, add it to the messages
          if (transcribedText) {
            // Add user message to conversation
            const newMessage = { role: 'user', content: transcribedText };
            setMessages(prev => [...prev, newMessage]);
            
            // Get AI response
            await getAIResponse([...messages, newMessage], false, false, true);
          } else {
            setError('No speech detected. Please try again.');
            setIsProcessing(false);
          }
        } catch (err) {
          console.error('Error in audio processing:', err);
          setError('Failed to process audio. Please try again.');
          setIsProcessing(false);
        }
      };
      
      reader.onerror = () => {
        console.error('Error reading audio file');
        setError('Failed to read audio data. Please try again.');
        setIsProcessing(false);
      };
      
      // Read the blob as data URL
      reader.readAsDataURL(audioBlob);
    } catch (err) {
      console.error('Error setting up audio processing:', err);
      setError('Failed to process audio. Please try again.');
      setIsProcessing(false);
    }
  };
  
  const getAIResponse = async (
    conversationHistory: Array<{ role: string; content: string }>, 
    isEmptyResponse: boolean = false,
    isCodeSubmission: boolean = false,
    includeFollowUp: boolean = true
  ) => {
    if (!interviewData) return;
    
    // Set a processing flag to prevent multiple simultaneous calls
    if (isProcessing) {
      console.log("Already processing AI response, skipping duplicate call");
      return;
    }
    
    // Check time states directly from timeLeft
    const isTimeRunningLow = timeLeft <= 120;
    const isTimeUp = timeLeft === 0;
    
    // Check if time warning and time up have already been handled
    const timeWarningHandledKey = `interview_time_warning_handled_${interviewData.id}`;
    const timeUpHandledKey = `interview_time_up_handled_${interviewData.id}`;
    const timeWarningHandled = localStorage.getItem(timeWarningHandledKey) === 'true';
    const timeUpHandled = localStorage.getItem(timeUpHandledKey) === 'true';
    
    // Log the current state for debugging
    console.log(`Time states before API call - Running low: ${isTimeRunningLow} (handled: ${timeWarningHandled}), Time up: ${isTimeUp} (handled: ${timeUpHandled}), timeLeft: ${timeLeft}`);
    
    setIsProcessing(true);
    setError('');
    
    // Set a timeout to reset isProcessing if the API call takes too long
    const processingTimeout = setTimeout(() => {
      console.log('API call timeout reached, resetting isProcessing');
      setIsProcessing(false);
    }, 15000); // 15 seconds timeout
    
    try {
      // Check time states again (in case they changed during async operations)
      const isTimeVeryLow = timeLeft <= 60;
      
      // If time is running low or up, never include follow-up questions regardless of the parameter
      const shouldIncludeFollowUp = includeFollowUp && !isTimeRunningLow && !isTimeUp;
      
      // Prepare headers with authentication
      let headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      
      let token = '';
      try {
        // Try to get the access token if available
        token = await getAccessToken();
        console.log('Authentication token obtained:', token ? 'Token exists' : 'No token');
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
      } catch (err) {
        // If getAccessToken fails, handle authentication error
        console.error('Error getting access token:', err);
        handleAuthError();
        clearTimeout(processingTimeout);
        setIsProcessing(false);
        return;
      }
      
      console.log('Making request to API with headers:', Object.keys(headers));
      
      // First check if the user is authenticated by making a simple request
      try {
        const authCheckResponse = await fetch(`${API_BASE_URL}/api/health`, {
          method: 'GET',
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        });
        
        if (!authCheckResponse.ok && authCheckResponse.status === 401) {
          console.error('Authentication check failed');
          handleAuthError();
          clearTimeout(processingTimeout);
          setIsProcessing(false);
          return;
        }
      } catch (err) {
        console.error('Error checking authentication:', err);
        // Continue anyway, the main request will handle auth errors
      }
      
      // Make the API request to get the AI response
      const aiResponse = await fetch(`${API_BASE_URL}/api/interview/conversation`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          job_title: interviewData.jobTitle,
          job_description: interviewData.jobDescription,
          conversation_history: conversationHistory,
          current_question_index: currentQuestionIndex,
          // IMPORTANT: For time-related flags, we need to check if they've been handled
          // We only want to set these flags if they haven't been handled yet
          time_up: isTimeUp && !timeUpHandled,
          time_running_low: isTimeRunningLow && !timeWarningHandled,
          no_response_detected: isEmptyResponse,
          is_code_submission: isCodeSubmission,
          question_type: interviewData.questions[currentQuestionIndex]?.type || 'general',
          include_follow_up: shouldIncludeFollowUp
        }),
      });
      
      if (!aiResponse.ok) {
        // Handle authentication error
        if (aiResponse.status === 401) {
          console.error('Authentication error in conversation API');
          handleAuthError();
          clearTimeout(processingTimeout);
          setIsProcessing(false);
          return;
        }
        
        throw new Error(`Failed to get AI response: ${aiResponse.status} ${aiResponse.statusText}`);
      }
      
      clearTimeout(processingTimeout);
      
      const data = await aiResponse.json();
      console.log('AI response data:', data);
      
      if (!data || !data.response) {
        console.error('Invalid response from API:', data);
        throw new Error('Failed to get AI response: Invalid response format');
      }
      
      const aiResponseText = data.response;
      
      // Add AI response to conversation
      const aiMessage = { role: 'assistant', content: aiResponseText };
      setMessages([...conversationHistory, aiMessage]);
      
      // Play the audio response only if in voice mode
      if (interviewData.useVoiceMode) {
        if (data.audio && typeof data.audio === 'string' && data.audio.trim() !== '') {
          try {
            console.log('Received audio data in response, playing...');
            // Convert base64 to blob
            const audioBlob = base64ToBlob(data.audio, 'audio/mpeg');
            
            if (audioBlob.size === 0) {
              console.warn('Audio blob is empty, falling back to TTS');
              await speakMessage(aiResponseText);
              return;
            }
            
            const audioUrl = URL.createObjectURL(audioBlob);
            
            // Use the existing audio element
            if (audioRef.current) {
              // Clean up previous audio URL if it exists
              if (audioRef.current.src) {
                URL.revokeObjectURL(audioRef.current.src);
              }
              
              audioRef.current.src = audioUrl;
              audioRef.current.onplay = () => {
                console.log('Audio started playing');
                setIsSpeaking(true);
              };
              
              audioRef.current.onended = () => {
                console.log('Audio playback ended');
                setIsSpeaking(false);
                URL.revokeObjectURL(audioUrl);
              };
              
              audioRef.current.onerror = (e) => {
                console.error('Audio playback error:', e);
                setIsSpeaking(false);
                URL.revokeObjectURL(audioUrl);
                // Fallback to TTS
                speakMessage(aiResponseText).catch(err => {
                  console.error('Fallback TTS failed:', err);
                });
              };
              
              // Play the audio
              try {
                console.log('Attempting to play audio from AI response');
                const playPromise = audioRef.current.play();
                
                if (playPromise !== undefined) {
                  playPromise
                    .then(() => {
                      console.log('Audio playback started successfully');
                    })
                    .catch(err => {
                      console.error('Error playing audio from AI response:', err);
                      setIsSpeaking(false);
                      URL.revokeObjectURL(audioUrl);
                      
                      // Fallback to browser TTS
                      speakMessage(aiResponseText).catch(err => {
                        console.error('Fallback TTS failed:', err);
                      });
                    });
                }
              } catch (err) {
                console.error('Error playing audio from AI response:', err);
                setIsSpeaking(false);
                URL.revokeObjectURL(audioUrl);
                
                // Fallback to browser TTS
                speakMessage(aiResponseText).catch(err => {
                  console.error('Fallback TTS failed:', err);
                });
              }
            } else {
              console.error('Audio element reference is null');
              // Fallback to browser TTS
              await speakMessage(aiResponseText);
            }
          } catch (err) {
            console.error('Error processing audio data from AI response:', err);
            // Fallback to browser TTS
            await speakMessage(aiResponseText);
          }
        } else {
          console.log('No audio data in response, using TTS');
          // No audio data in response, use browser TTS
          await speakMessage(aiResponseText);
        }
      }
    } catch (error) {
      console.error('Error getting AI response:', error);
      setError('Failed to get AI response. Please try again.');
      // Make sure to set isSpeaking to false in case of error
      setIsSpeaking(false);
      throw error;
    } finally {
      // Clear the timeout
      clearTimeout(processingTimeout);
      
      // Always set isProcessing to false when done
      setIsProcessing(false);
      console.log('AI response processing completed, isProcessing set to false');
    }
  };
  
  // Fix the speakMessage function to handle the audio playback correctly
  const speakMessage = async (text: string): Promise<void> => {
    try {
      // Check if text is valid
      if (!text) {
        console.error('Invalid text for speech synthesis:', text);
        setIsSpeaking(false);
        return Promise.resolve();
      }
      
      setIsSpeaking(true);
      
      // Get the access token
      let token;
      try {
        token = await getAccessToken();
        console.log('Got access token for text-to-speech');
      } catch (err) {
        console.error('Error getting access token:', err);
        // Handle authentication error
        handleAuthError();
        setIsSpeaking(false);
        return Promise.resolve();
      }
      
      // Safely get a substring for logging
      const textPreview = text ? text.substring(0, Math.min(50, text.length)) : '';
      console.log('Sending text-to-speech request:', textPreview + '...');
      
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      // Use a direct fetch to get the audio data
      const response = await fetch(`${API_BASE_URL}/api/text-to-speech`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          text,
          voice: 'alloy'
        }),
      });
      
      if (!response.ok) {
        console.error('Text-to-speech API error:', response.status, response.statusText);
        
        // Handle authentication error
        if (response.status === 401) {
          handleAuthError();
          setIsSpeaking(false);
          return Promise.resolve();
        }
        
        throw new Error(`Failed to generate speech: ${response.status} ${response.statusText}`);
      }
      
      // Get the response as JSON
      const data = await response.json();
      
      if (!data.audio) {
        console.error('No audio data in response');
        throw new Error('No audio data in response');
      }
      
      console.log('Received audio data from API');
      
      // The audio data is already a data URL with base64 encoded audio
      const audioUrl = data.audio;
      
      // Use the existing audio element instead of creating a new one
      if (audioRef.current) {
        // Clean up previous audio URL if it exists
        if (audioRef.current.src && audioRef.current.src.startsWith('blob:')) {
          URL.revokeObjectURL(audioRef.current.src);
        }
        
        // Set up event handlers before setting the source
        audioRef.current.onplay = () => {
          console.log('Audio started playing');
          setIsSpeaking(true);
        };
        
        audioRef.current.onended = () => {
          console.log('Audio playback ended');
          setIsSpeaking(false);
        };
        
        audioRef.current.onerror = (e) => {
          console.error('Audio playback error:', e);
          setIsSpeaking(false);
          
          // Fallback to browser's built-in speech synthesis
          if ('speechSynthesis' in window) {
            try {
              const utterance = new SpeechSynthesisUtterance(text);
              utterance.onend = () => {
                setIsSpeaking(false);
              };
              window.speechSynthesis.speak(utterance);
            } catch (err) {
              console.error('Fallback speech synthesis failed:', err);
              setIsSpeaking(false);
            }
          }
        };
        
        // Update all source elements with the new URL
        const sourceElements = audioRef.current.getElementsByTagName('source');
        for (let i = 0; i < sourceElements.length; i++) {
          sourceElements[i].src = audioUrl;
        }
        
        // Set the source after setting up event handlers
        audioRef.current.src = audioUrl;
        
        // Load the audio (important for some browsers)
        audioRef.current.load();
        
        // Play the audio
        try {
          console.log('Attempting to play audio');
          const playPromise = audioRef.current.play();
          
          if (playPromise !== undefined) {
            playPromise
              .then(() => {
                console.log('Audio playback started successfully');
              })
              .catch(err => {
                console.error('Error playing audio:', err);
                
                // Fallback to browser's built-in speech synthesis
                if ('speechSynthesis' in window) {
                  try {
                    const utterance = new SpeechSynthesisUtterance(text);
                    utterance.onend = () => {
                      setIsSpeaking(false);
                    };
                    window.speechSynthesis.speak(utterance);
                  } catch (err) {
                    console.error('Fallback speech synthesis failed:', err);
                    setIsSpeaking(false);
                  }
                }
              });
          }
        } catch (err) {
          console.error('Error playing audio:', err);
          setIsSpeaking(false);
          
          // Fallback to browser's built-in speech synthesis
          if ('speechSynthesis' in window) {
            try {
              const utterance = new SpeechSynthesisUtterance(text);
              utterance.onend = () => {
                setIsSpeaking(false);
              };
              window.speechSynthesis.speak(utterance);
            } catch (err) {
              console.error('Fallback speech synthesis failed:', err);
              setIsSpeaking(false);
            }
          }
        }
        
        // Return a promise that resolves when the audio finishes playing
        return new Promise<void>((resolve) => {
          if (!audioRef.current) {
            setIsSpeaking(false);
            resolve();
        return;
      }
      
          const originalOnEnded = audioRef.current.onended;
          
          audioRef.current.onended = (e) => {
            // Call the original handler if it exists
            if (originalOnEnded && typeof originalOnEnded === 'function') {
              if (audioRef.current) {
                originalOnEnded.call(audioRef.current, e as Event);
              }
            }
            
            setIsSpeaking(false);
            resolve();
          };
          
          const originalOnError = audioRef.current.onerror;
          
          audioRef.current.onerror = (e) => {
            // Call the original handler if it exists
            if (originalOnError && typeof originalOnError === 'function') {
              if (audioRef.current) {
                originalOnError.call(audioRef.current, e);
              }
            }
            
            setIsSpeaking(false);
            resolve();
          };
          
          // Set a timeout to prevent hanging
          setTimeout(() => {
            setIsSpeaking(false);
            resolve();
          }, 60000); // 1 minute timeout
        });
      } else {
        console.error('Audio element reference is null');
        setIsSpeaking(false);
        return Promise.resolve();
      }
    } catch (err) {
      console.error('Error in speakMessage:', err);
      setIsSpeaking(false);
      
      // Fallback to browser's built-in speech synthesis
      if ('speechSynthesis' in window && text) {
        try {
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.onend = () => {
            setIsSpeaking(false);
          };
          window.speechSynthesis.speak(utterance);
        } catch (err) {
          console.error('Fallback speech synthesis failed:', err);
        }
      }
      
      return Promise.resolve();
    }
  };

  // Format time (seconds) to MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Cleanup any lingering media resources when the component unmounts
  useEffect(() => {
    return () => {
      // Final cleanup when component unmounts
      if (localVideoRef.current && localVideoRef.current.srcObject) {
        const mediaStream = localVideoRef.current.srcObject as MediaStream;
        mediaStream.getTracks().forEach(track => {
          track.stop();
          console.log(`Unmount cleanup: Stopped track: ${track.kind}`);
        });
        localVideoRef.current.srcObject = null;
      }
      
      // Stop any active recording
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        try {
          mediaRecorderRef.current.stop();
        } catch (e) {
          console.error('Error stopping media recorder:', e);
        }
      }
      
      // Clear any running timers
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }

      // Force cleanup of all media devices
      try {
        // Get all media devices and stop them
        navigator.mediaDevices.enumerateDevices()
          .then(devices => {
            console.log(`Cleaning up ${devices.length} media devices`);
            
            // Stop any active MediaStream tracks that might still be running
            const allTracks = document.querySelectorAll('video, audio');
            allTracks.forEach(element => {
              const mediaElement = element as HTMLMediaElement;
              if (mediaElement.srcObject) {
                const stream = mediaElement.srcObject as MediaStream;
                if (stream) {
                  stream.getTracks().forEach(track => {
                    track.stop();
                    console.log(`Global cleanup: Stopped track: ${track.kind}`);
                  });
                  mediaElement.srcObject = null;
                }
              }
            });
          })
          .catch(err => {
            console.error('Error during global media cleanup:', err);
          });
      } catch (err) {
        console.error('Error during global media cleanup:', err);
      }
    };
  }, []);

  // Fix the toggleVideo function to prevent video blanking and maintain recording state
  const toggleVideo = async () => {
    // If turning video on
    if (!showVideo) {
      try {
        console.log('Initializing WebRTC before showing video');
        
        // Get user media (camera only) with specific constraints for stability
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            frameRate: { ideal: 30 }
          },
          audio: false // Don't request audio in video stream, keep them separate
        });
        
        if (localVideoRef.current) {
          // Store the stream in a ref to maintain it across renders
          localVideoStreamRef.current = mediaStream;
          localVideoRef.current.srcObject = mediaStream;
          
          // Ensure video tracks are enabled
          mediaStream.getVideoTracks().forEach(track => {
            track.enabled = true;
          });
        }
        
        // Only set showVideo to true if initialization was successful
        setShowVideo(true);
        setIsVideoConnected(true);
      } catch (err) {
        console.error('Failed to initialize WebRTC:', err);
        setError('Failed to access camera. Please check your permissions.');
      }
    } else {
      // If turning video off, only stop video tracks but keep audio tracks active
      if (localVideoRef.current && localVideoRef.current.srcObject) {
        console.log('Stopping video tracks before hiding video');
        const stream = localVideoRef.current.srcObject as MediaStream;
        
        // Only stop video tracks, keep audio tracks for recording
        stream.getVideoTracks().forEach(track => {
          // Disable the track first before stopping to prevent flickering
          track.enabled = false;
          // Small delay before stopping to prevent visual glitches
          setTimeout(() => {
            track.stop();
            console.log(`Toggled off: Stopped video track: ${track.kind}, enabled: ${track.enabled}, readyState: ${track.readyState}`);
          }, 100);
        });
        
        // Keep the audio tracks in the srcObject for recording
        const audioTracks = stream.getAudioTracks();
        if (audioTracks.length > 0) {
          // Create a new stream with only audio tracks
          const audioStream = new MediaStream(audioTracks);
          localVideoRef.current.srcObject = audioStream;
          console.log('Kept audio tracks active for recording');
        } else {
          localVideoRef.current.srcObject = null;
        }
      }
      
      // Update state
      setShowVideo(false);
      setIsVideoConnected(false);
    }
  };

  // Auto-scroll conversation to bottom when messages change
  useEffect(() => {
    if (conversationContainerRef.current) {
      conversationContainerRef.current.scrollTop = conversationContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Utility function to convert base64 to Blob with improved error handling
  const base64ToBlob = (base64: string, mimeType: string): Blob => {
    try {
      // Check if the base64 string is valid
      if (!base64 || typeof base64 !== 'string') {
        console.error('Invalid base64 string:', base64);
        return new Blob([], { type: mimeType });
      }
      
      // Remove any potential data URL prefix
      let cleanBase64 = base64;
      if (base64.includes(',')) {
        cleanBase64 = base64.split(',')[1];
      }
      
      // Decode the base64 string
      const byteCharacters = atob(cleanBase64);
      const byteArrays = [];
      
      for (let offset = 0; offset < byteCharacters.length; offset += 512) {
        const slice = byteCharacters.slice(offset, offset + 512);
        
        const byteNumbers = new Array(slice.length);
        for (let i = 0; i < slice.length; i++) {
          byteNumbers[i] = slice.charCodeAt(i);
        }
        
        const byteArray = new Uint8Array(byteNumbers);
        byteArrays.push(byteArray);
      }
      
      return new Blob(byteArrays, { type: mimeType });
    } catch (error) {
      console.error('Error converting base64 to blob:', error);
      return new Blob([], { type: mimeType });
    }
  };

  // Save current question index to localStorage whenever it changes
  useEffect(() => {
    if (interviewData) {
      localStorage.setItem(`interview_question_${interviewData.id}`, currentQuestionIndex.toString());
    }
  }, [currentQuestionIndex, interviewData]);

  // Save timer state to localStorage every second
  useEffect(() => {
    if (timeLeft > 0 && interviewData) {
      localStorage.setItem(`interview_timer_${interviewData.id}`, JSON.stringify({
        remainingTime: timeLeft,
        lastUpdated: Date.now()
      }));
    }
  }, [timeLeft, interviewData]);

  // Handle audio playback ending
  const handleAudioEnded = () => {
    setIsSpeaking(false);
    if (audioRef.current && audioRef.current.src) {
      URL.revokeObjectURL(audioRef.current.src);
    }
  };

  // Add AI response to conversation
  const addAIResponseToConversation = (response: string) => {
    if (!response) return;
    
    setMessages(prev => [
      ...prev,
      { role: 'assistant', content: response }
    ]);
  };

  // Process AI response
  const processAIResponse = (response: string) => {
    if (!response) return;
    
    // If time is running low, modify the response to avoid follow-up questions
    // and remove any follow-up questions that might be in the response
    if (timeLeft < 120 || timeWarningShown) {
      // Check if the response contains a follow-up question
      const followUpIndicators = [
        "follow-up question",
        "follow up question",
        "another question",
        "next question",
        "let me ask you",
        "could you also",
        "can you elaborate",
        "tell me more about",
        "would you mind explaining",
        "can you describe"
      ];
      
      // If the response contains a follow-up question, truncate it
      for (const indicator of followUpIndicators) {
        if (response.toLowerCase().includes(indicator)) {
          // Find the position of the indicator
          const index = response.toLowerCase().indexOf(indicator);
          // Truncate the response before the follow-up question
          response = response.substring(0, index);
          // Add a closing statement
          response += " We're running out of time, so let's move on to the next question.";
          break;
        }
      }
      
      // If the response doesn't already mention time running out, add it
      if (!response.includes("We're running out of time")) {
        response = response + " We're running out of time, so let's move on to the next question.";
      }
    }
    
    // Add the AI response to the conversation
    addAIResponseToConversation(response);
    
    // If in voice mode, play the audio response
    if (interviewData?.useVoiceMode && response) {
      speakMessage(response);
    }
  };

  // Function to clean up all media
  const cleanupMedia = () => {
    console.log("Performing comprehensive media cleanup");
    
    // Stop all video tracks
    if (localVideoRef.current && localVideoRef.current.srcObject) {
      const stream = localVideoRef.current.srcObject as MediaStream;
      
      // First disable tracks before stopping them to prevent visual glitches
      stream.getTracks().forEach(track => {
        track.enabled = false;
      });
      
      // Small delay before stopping tracks to prevent visual glitches
      setTimeout(() => {
        stream.getTracks().forEach(track => {
          track.stop();
          console.log(`Cleanup: Stopped track: ${track.kind}`);
        });
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = null;
        }
      }, 100);
    }
    
    // Also clean up the stored video stream
    if (localVideoStreamRef.current) {
      localVideoStreamRef.current.getTracks().forEach(track => {
        track.enabled = false;
        setTimeout(() => track.stop(), 100);
      });
      localVideoStreamRef.current = null;
    }
    
    // Clean up the audio stream
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach(track => {
        track.enabled = false;
        setTimeout(() => track.stop(), 100);
      });
      audioStreamRef.current = null;
    }
    
    // Stop any active recording
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch (e) {
        console.error('Error stopping media recorder:', e);
      }
      mediaRecorderRef.current = null;
    }
    
    // Clean up audio element
    if (audioRef.current) {
      try {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
        if (audioRef.current.src) {
          URL.revokeObjectURL(audioRef.current.src);
          audioRef.current.src = '';
        }
      } catch (e) {
        console.error("Error cleaning up audio element:", e);
      }
    }
    
    // Stop any browser speech synthesis that might be running
    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {
        console.error("Error canceling speech synthesis:", e);
      }
    }
    
    // Set state variables to indicate no audio is playing
    setIsSpeaking(false);
    setIsProcessing(false);
    
    console.log("Media cleanup completed");
  };

  // Add a cleanup effect when component unmounts or when navigating away
  useEffect(() => {
    // Add event listener for beforeunload to clean up camera
    const handleBeforeUnload = () => {
      console.log('Page is being unloaded, cleaning up media');
      cleanupMedia();
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    // Return cleanup function
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      cleanupMedia();
    };
  }, []);
  
  // Add a cleanup effect for Next.js route changes
  useEffect(() => {
    // This effect will run when the component is mounted
    console.log('Setting up route change cleanup');
    
    // Function to handle route changes
    const handleRouteChange = () => {
      console.log('Route is changing, cleaning up media');
      cleanupMedia();
    };
    
    // For Next.js App Router, we need to use the cleanup function
    // since there's no direct event API for route changes
    return () => {
      console.log('Component unmounting due to navigation, cleaning up media');
      cleanupMedia();
    };
  }, []);

  // Add audio element initialization effect
  useEffect(() => {
    // Initialize audio element
    if (audioRef.current) {
      // Set up audio element properties
      audioRef.current.volume = 1.0;
      
      // Define event handlers
      const handlePlay = () => {
        console.log('Audio started playing');
      };
      
      const handlePause = () => {
        console.log('Audio paused');
      };
      
      const handleEnded = () => {
        console.log('Audio ended');
      };
      
      const handleError = (e: Event) => {
        console.error('Audio error:', e);
      };
      
      // Add event listeners for debugging
      audioRef.current.addEventListener('play', handlePlay);
      audioRef.current.addEventListener('pause', handlePause);
      audioRef.current.addEventListener('ended', handleEnded);
      audioRef.current.addEventListener('error', handleError);
      
      // Test audio with a silent audio file to ensure browser allows audio playback
      const testAudio = () => {
        try {
          // Create a short silent audio context
          const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
          const oscillator = audioContext.createOscillator();
          const gainNode = audioContext.createGain();
          
          // Set the gain to 0 (silent)
          gainNode.gain.value = 0;
          oscillator.connect(gainNode);
          gainNode.connect(audioContext.destination);
          
          // Play for 100ms
          oscillator.start(audioContext.currentTime);
          oscillator.stop(audioContext.currentTime + 0.1);
          
          console.log('Audio context initialized successfully');
        } catch (err) {
          console.error('Error initializing audio context:', err);
        }
      };
      
      // Run the test
      testAudio();
      
      // Return cleanup function to remove event listeners
      return () => {
        if (audioRef.current) {
          audioRef.current.removeEventListener('play', handlePlay);
          audioRef.current.removeEventListener('pause', handlePause);
          audioRef.current.removeEventListener('ended', handleEnded);
          audioRef.current.removeEventListener('error', handleError);
        }
      };
    }
  }, []);

  // Add a function to handle authentication errors
  const handleAuthError = () => {
    // Redirect to login page
    router.push('/auth/login?redirect=' + encodeURIComponent(`/interview/session/${params.id}`));
  };

  // Add an effect to check authentication on load
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Try to get the access token to check if the user is authenticated
        await getAccessToken();
      } catch (err) {
        console.error('Authentication error:', err);
        handleAuthError();
      }
    };
    
    checkAuth();
  }, []);

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
            <button 
              onClick={toggleVideo}
              className="text-sm bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded flex items-center"
            >
              {showVideo ? (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  Hide Video
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  Show Video
                </>
              )}
            </button>
          </div>
        </div>
        
        {/* Main content */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
          {/* Video section or Voice conversation */}
          <div className="bg-gray-100 rounded-lg p-4">
            {showVideo ? (
              <div className="flex flex-col">
                <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden relative mb-4">
                  {/* User's video as main display */}
                  <video
                    ref={localVideoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover"
                  ></video>
                  
                  {/* Video status indicator */}
                  <div className="absolute bottom-2 right-2 flex items-center bg-gray-800 bg-opacity-75 text-white text-xs px-2 py-1 rounded">
                    {isVideoConnected ? (
                      <>
                        <span className="h-2 w-2 rounded-full bg-green-500 mr-1"></span>
                        <span>Camera On</span>
                      </>
                    ) : (
                      <>
                        <span className="h-2 w-2 rounded-full bg-red-500 mr-1"></span>
                        <span>Camera Off</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              // Show voice conversation UI when video is off
              <div className="h-full flex flex-col">
                <div className="text-center p-4 mb-4">
                  <h2 className="text-xl font-semibold mb-2">Interview in Progress</h2>
                  <p className="text-gray-600">
                    {isVoiceMode 
                      ? "Voice mode is active. Speak clearly to answer questions." 
                      : "Type your answers in the text area below."}
                  </p>
                </div>
              
                {/* Only show conversation transcript in voice mode */}
                {isVoiceMode && (
                  <div className="h-[400px] border border-gray-200 rounded-lg shadow bg-white flex flex-col">
                    <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 text-sm font-medium text-gray-700">
                      Conversation Transcript
                    </div>
                    <div 
                      className="flex-1 overflow-y-auto p-4" 
                      ref={conversationContainerRef}
                      style={{ scrollBehavior: 'smooth' }}
                    >
                      <div className="space-y-4">
                        {messages.map((message, index) => (
                          <div 
                            key={index} 
                            className={`p-3 rounded-lg ${
                              message.role === 'assistant' 
                                ? 'bg-indigo-100 text-indigo-800' 
                                : 'bg-gray-200 text-gray-800 ml-8'
                            }`}
                          >
                            <p>{message.content}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                
                {/* For text mode, show a placeholder or instructions */}
                {!isVoiceMode && (
                  <div className="h-[400px] flex items-center justify-center">
                    <div className="text-center text-gray-500">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mx-auto mb-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                      </svg>
                      <p className="text-lg font-medium">Text Mode Interview</p>
                      <p className="mt-2">Answer the questions in the text area on the right.</p>
                      <p className="mt-1">Click "Submit Answer" when you're ready to proceed.</p>
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {/* Common voice mode controls outside both video and non-video sections */}
            {isVoiceMode && (
              <div className="mt-4 flex justify-center">
                <button
                  onClick={toggleRecording}
                  disabled={isSpeaking || isProcessing}
                  className={`px-4 py-2 rounded-full flex items-center ${
                    isRecording 
                      ? 'bg-red-600 text-white hover:bg-red-700' 
                      : 'bg-indigo-600 text-white hover:bg-indigo-700'
                  } ${(isSpeaking || isProcessing) ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {isRecording ? (
                    <>
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                      </svg>
                      Stop Recording
                    </>
                  ) : (
                    <>
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                      Start Recording
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
          
          {/* Question and answer section */}
          <div className="bg-gray-100 rounded-lg p-4 flex flex-col h-auto">
            <div className="mb-4">
              {isVoiceMode ? (
                <h2 className="text-lg font-semibold mb-2">
                  Voice Interview - Code Editor
                </h2>
              ) : (
                <>
              <h2 className="text-lg font-semibold mb-2">
                Question {currentQuestionIndex + 1}: {currentQuestion.type.charAt(0).toUpperCase() + currentQuestion.type.slice(1)}
                {currentQuestion.difficulty && (
                  <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                    currentQuestion.difficulty === 'basic' ? 'bg-green-100 text-green-800' :
                    currentQuestion.difficulty === 'intermediate' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {currentQuestion.difficulty.charAt(0).toUpperCase() + currentQuestion.difficulty.slice(1)}
                  </span>
                )}
              </h2>
              <p className="text-gray-800 p-3 bg-white rounded-lg border border-gray-200">
                {currentQuestion.question}
              </p>
                </>
              )}
            </div>
            
            <div className="flex-1">
              {isVoiceMode ? (
                <div className="flex flex-col h-[400px] max-h-[400px]">
                  {/* Code Editor for Voice Mode - Fixed Height */}
                  <div className="h-full border border-gray-300 rounded-lg overflow-hidden">
                    <p className="text-sm text-gray-600 p-2 bg-gray-100 border-b border-gray-300">
                      Use this editor to write code for {
                        // Get the latest question from the AI messages if available
                        messages.length > 0 
                          ? (() => {
                              // Find the last assistant message that contains a question
                              const lastAssistantMessages = messages
                                .filter(m => m.role === 'assistant')
                                .reverse();
                              
                              // Try to find a message with a question mark that isn't a time warning
                              for (const msg of lastAssistantMessages) {
                                if (msg && msg.content && msg.content.includes('?') && 
                                    !msg.content.toLowerCase().includes('minute left') && 
                                    !msg.content.toLowerCase().includes('time is running') &&
                                    !msg.content.toLowerCase().includes('wrap up')) {
                                  // Extract the question part
                                  const parts = msg.content.split('?');
                                  if (parts.length > 0) {
                                    return parts[0] + '?';
                                  }
                                }
                              }
                              
                              // Fallback to the current question from interview data
                              return interviewData?.questions[currentQuestionIndex]?.question || 'Loading question...';
                            })()
                          : interviewData?.questions[currentQuestionIndex]?.question || 'Loading question...'
                      }
                    </p>
                    <MonacoEditor
                      height="calc(100% - 35px)"
                      language="javascript"
                      theme="vs-light"
                      value={answers[currentQuestion.id] || '// Write your code here\n\n'}
                      onChange={(value) => handleAnswerChange(value)}
                      options={{
                        minimap: { enabled: false },
                        scrollBeyondLastLine: false,
                        fontSize: 14,
                        automaticLayout: true,
                        wordWrap: 'on',
                        lineNumbers: 'on',
                        tabSize: 2,
                      }}
                    />
                  </div>
                  <div className="mt-2 flex justify-end">
                    <button
                      onClick={() => handleSubmitCode()}
                      disabled={isSpeaking || isProcessing || isRecording}
                      className={`px-4 py-2 rounded-md bg-indigo-600 text-white font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                        isSpeaking || isProcessing || isRecording ? 'opacity-50 cursor-not-allowed' : ''
                      }`}
                    >
                      Submit Code
                    </button>
                  </div>
                </div>
              ) : (
                currentQuestion.type === 'coding' ? (
                  <div className="h-[400px] border border-gray-300 rounded-lg overflow-hidden">
                  <MonacoEditor
                    height="100%"
                    language="javascript"
                      theme="vs-light"
                      value={answers[currentQuestion.id] || '// Write your code here\n\n'}
                      onChange={(value) => handleAnswerChange(value)}
                    options={{
                      minimap: { enabled: false },
                      scrollBeyondLastLine: false,
                      fontSize: 14,
                        automaticLayout: true,
                        wordWrap: 'on',
                        lineNumbers: 'on',
                        tabSize: 2,
                    }}
                  />
                </div>
              ) : (
                  <div className="flex flex-col h-full">
                    <div className="mt-4">
                <textarea
                        value={answers[interviewData.questions[currentQuestionIndex]?.id] || ''}
                  onChange={(e) => handleAnswerChange(e.target.value)}
                  placeholder="Type your answer here..."
                        className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                        rows={6}
                        disabled={isSpeaking || isProcessing}
                      />
                    </div>
                    <div className="mt-2 flex justify-end">
                      <button
                        onClick={handleSubmitAnswer}
                        disabled={isSpeaking || isProcessing || answeredQuestions.has(interviewData.questions[currentQuestionIndex]?.id)}
                        className={`px-4 py-2 rounded-md bg-indigo-600 text-white font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                          isSpeaking || isProcessing || answeredQuestions.has(interviewData.questions[currentQuestionIndex]?.id) ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                      >
                        Submit Answer
                      </button>
                    </div>
                  </div>
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
          
          {/* Navigation buttons - only show in text mode */}
          {!isVoiceMode && (
            <div className="flex space-x-2 items-center">
              <button
                onClick={handlePreviousQuestion}
                disabled={currentQuestionIndex === 0 || (currentQuestionIndex > 0 && answeredQuestions.has(interviewData.questions[currentQuestionIndex - 1]?.id))}
                className={`px-4 py-2 rounded-md ${
                  currentQuestionIndex === 0 || (currentQuestionIndex > 0 && answeredQuestions.has(interviewData.questions[currentQuestionIndex - 1]?.id))
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
          
          <button
            onClick={handleSubmitInterview}
            disabled={isSubmitting && timeLeft > 0}
            className={`px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 flex items-center ${
              isSubmitting ? 'opacity-75 cursor-not-allowed' : ''
            }`}
          >
            {isSubmitting 
              ? 'Submitting...' 
              : timeLeft === 0 
                ? 'Time\'s Up - Submit' 
                : 'Finish & Submit'}
          </button>
        </div>
      </div>
      
      {/* Audio element for TTS playback */}
      <audio 
        ref={audioRef} 
        className="hidden" 
        controls={false} 
        autoPlay={true} 
        preload="auto"
        onEnded={handleAudioEnded}
        onError={(e) => console.error('Audio element error:', e)}
      >
        Your browser does not support the audio element.
      </audio>
    </div>
  );
}