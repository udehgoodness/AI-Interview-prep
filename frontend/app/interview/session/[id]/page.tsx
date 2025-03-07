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
  
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const conversationContainerRef = useRef<HTMLDivElement>(null);

  // Load interview data from localStorage
  useEffect(() => {
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
      if (messages.length === 0) {
        // Check if we already have a greeting message to prevent duplication
        const hasGreeting = messages.some(msg => 
          msg.role === 'assistant' && 
          (msg.content.toLowerCase().includes('hello') || 
           msg.content.toLowerCase().includes('hi') ||
           msg.content.toLowerCase().includes('welcome'))
        );
        
        if (!hasGreeting) {
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
          
          setMessages([initialMessage]);
          
          // Play the greeting message if voice mode is enabled
          if (parsedData.useVoiceMode) {
            // Use setTimeout to ensure the component is fully mounted before playing audio
            setTimeout(() => {
              speakMessage(initialMessage.content).catch(err => {
                console.error('Error playing greeting message:', err);
              });
            }, 1000);
          }
        }
      }
    } catch (err) {
      console.error('Error loading interview data:', err);
      setError('Failed to load interview data. Please set up a new interview.');
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
          // Store the current timer state in localStorage
          localStorage.setItem(`interview_timer_${interviewData.id}`, JSON.stringify({
            remainingTime: prev,
            lastUpdated: Date.now()
          }));
          
          // When time is up, handle the end of interview
          if (prev <= 1) {
            clearInterval(timerRef.current as NodeJS.Timeout);
            handleTimeUp();
            return 0;
          }
          
          // When there's only 1 minute left, send a time warning
          if (prev === 60 && interviewData.useVoiceMode) {
            handleTimeWarning();
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

  // Handle time warning when 1 minute is left
  const handleTimeWarning = async () => {
    if (!interviewData || !interviewData.useVoiceMode) return;
    
    try {
      // Check if we already have a time warning message to prevent duplication
      // Improved detection logic to catch more variations of time warning messages
      const hasTimeWarning = messages.some(msg => {
        if (msg.role !== 'assistant') return false;
        
        const content = msg.content.toLowerCase();
        return (
          content.includes('minute left') || 
          content.includes('wrap up') ||
          content.includes('running low') ||
          content.includes('one minute') ||
          content.includes('time is short') ||
          content.includes('time is running') ||
          content.includes('almost out of time') ||
          content.includes('finishing up') ||
          content.includes('concluding') ||
          content.includes('final thoughts')
        );
      });
      
      if (hasTimeWarning) {
        console.log("Time warning already issued, skipping duplicate");
        return;
      }
      
      // Add a time warning message to the conversation
      const timeWarningMessage = { 
        role: 'assistant', 
        content: "We have about one minute left in our interview. I'll wrap up now and give you a chance for any final thoughts." 
      };
      
      // Update state with the new message - use functional update to ensure we're working with the latest state
      setMessages(prevMessages => [...prevMessages, timeWarningMessage]);
      
      // Speak the time warning message
      await speakMessage(timeWarningMessage.content);
    } catch (err) {
      console.error("Error handling time warning:", err);
    }
  };

  // Handle time up scenario
  const handleTimeUp = async () => {
    if (!interviewData) return;
    
    // Clear the timer data from localStorage
    localStorage.removeItem(`interview_timer_${interviewData.id}`);
    
    // Clear the question index data from localStorage
    localStorage.removeItem(`interview_question_${interviewData.id}`);
    
    // For voice mode, add a final message from the AI
    if (interviewData.useVoiceMode && !isSubmitting) {
      // Don't add the message if already submitting or if AI is speaking
      if (!isSpeaking) {
        try {
          // Check if we already have a time up message to prevent duplication
          // Improved detection logic to catch more variations of closing messages
          const hasTimeUpMessage = messages.some(msg => {
            if (msg.role !== 'assistant') return false;
            
            const content = msg.content.toLowerCase();
            return (
              content.includes('time is up') || 
              content.includes('thank you for your time') ||
              content.includes('that concludes our interview') ||
              content.includes('wrap up') ||
              content.includes('appreciate your candidness') ||
              content.includes('appreciate your insights') ||
              content.includes('best of luck') ||
              content.includes('next steps') ||
              content.includes('hiring process') ||
              content.includes('get back to you') ||
              (content.includes('thank') && content.includes('interview'))
            );
          });
          
          if (hasTimeUpMessage) {
            console.log("Time up message already issued, skipping duplicate");
            // Submit the interview without adding another message
            setTimeout(() => {
              handleSubmitInterview();
            }, 1000);
            return;
          }
          
          // Get a special time-up message from the AI
          const response = await fetch(`${API_BASE_URL}/api/interview/conversation`, {
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
          
          // Speak the time up message and ensure it completes before submitting
          await speakMessage(timeUpMessage);
          
          // Add a delay to ensure the message is fully processed before submitting
          setTimeout(() => {
            handleSubmitInterview();
          }, 2000);
        } catch (err) {
          console.error("Error getting time up message:", err);
          // If there's an error, still try to submit the interview
          setTimeout(() => {
            handleSubmitInterview();
          }, 1000);
        }
      } else {
        // If AI is speaking, wait for it to finish before submitting
        console.log("AI is currently speaking, waiting before submitting...");
        // Check every second if AI has finished speaking
        const checkInterval = setInterval(() => {
          if (!isSpeaking) {
            clearInterval(checkInterval);
            handleSubmitInterview();
          }
        }, 1000);
        
        // Set a maximum wait time of 10 seconds
        setTimeout(() => {
          clearInterval(checkInterval);
          handleSubmitInterview();
        }, 10000);
      }
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
        mediaStream.getTracks().forEach(track => {
          track.stop();
          console.log(`Cleanup: Stopped track: ${track.kind}, enabled: ${track.enabled}, readyState: ${track.readyState}`);
        });
        
        // Clear the srcObject to fully release the camera
        localVideoRef.current.srcObject = null;
      }
      
      // Also stop any recording if active
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        mediaRecorderRef.current.stop();
      }
    };
  }, [interviewData, showVideo, isRecording]);

  const initializeWebRTC = async () => {
    try {
      // Only initialize camera if video is enabled
      if (!showVideo) {
        return;
      }
      
      console.log('Initializing WebRTC for video');
      
      // First, check if we already have a video stream
      if (localVideoRef.current && localVideoRef.current.srcObject) {
        const currentStream = localVideoRef.current.srcObject as MediaStream;
        const hasVideoTracks = currentStream.getVideoTracks().length > 0;
        
        // If we already have video tracks, just ensure they're enabled
        if (hasVideoTracks) {
          currentStream.getVideoTracks().forEach(track => {
            track.enabled = true;
          });
          
          console.log('Reusing existing video stream');
          setIsVideoConnected(true);
          return;
        }
      }
      
      console.log('Getting new video stream');
      
      // Check if we already have a media stream from recording
      let existingAudioStream = null;
      if (mediaRecorderRef.current && mediaRecorderRef.current.stream) {
        existingAudioStream = mediaRecorderRef.current.stream;
        console.log('Found existing audio stream from recorder');
      }
      
      // Get user media (camera and microphone)
      const constraints = {
        video: true,
        audio: !existingAudioStream // Only request audio if we don't already have it
      };
      
      console.log('Requesting media with constraints:', constraints);
      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      console.log('Got new media stream with tracks:', mediaStream.getTracks().map(t => t.kind).join(', '));
      
      // If we have an existing audio stream, add those tracks to our new stream
      if (existingAudioStream) {
        console.log('Adding existing audio tracks to new stream');
        
        // Remove any existing audio tracks from the new stream to avoid duplicates
        mediaStream.getAudioTracks().forEach(t => {
          t.stop(); // Stop the track
          mediaStream.removeTrack(t); // Remove it from the stream
          console.log('Removed new audio track to avoid duplication');
        });
        
        // Add the existing audio tracks to the new stream
        existingAudioStream.getAudioTracks().forEach(track => {
          // Clone the track to avoid affecting the original stream
          const clonedTrack = track.clone();
          mediaStream.addTrack(clonedTrack);
          console.log('Added existing audio track to new stream');
        });
      }
      
      // Set the stream to the video element
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = mediaStream;
        console.log('Set new media stream to video element');
      }

      // Set video connected state
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
    
    // Clear the timer data from localStorage
    localStorage.removeItem(`interview_timer_${interviewData.id}`);
    
    // Clear the question index data from localStorage
    localStorage.removeItem(`interview_question_${interviewData.id}`);
    
    try {
      // Stop all media tracks and ensure they're fully stopped
      if (localVideoRef.current && localVideoRef.current.srcObject) {
        const mediaStream = localVideoRef.current.srcObject as MediaStream;
        mediaStream.getTracks().forEach(track => {
          track.stop();
          console.log(`Stopped track: ${track.kind}, enabled: ${track.enabled}, readyState: ${track.readyState}`);
        });
        
        // Clear the srcObject to fully release the camera
        localVideoRef.current.srcObject = null;
      }
      
      // Stop recording if active
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        mediaRecorderRef.current.stop();
        setIsRecording(false);
      }
      
      // Force a global cleanup of all media devices before navigation
      try {
        // Get all media devices and stop them
        const allDevices = await navigator.mediaDevices.enumerateDevices();
        console.log(`Cleaning up ${allDevices.length} media devices before navigation`);
        
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
      } catch (err) {
        console.error('Error during global media cleanup:', err);
      }
      
      // Format answers for submission
      const formattedAnswers = interviewData.questions.map(question => ({
        question_id: question.id,
        question: question.question,
        question_type: question.type,
        answer: answers[question.id] || ''
      }));
      
      // Submit answers for evaluation
      let headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      
      try {
        // Try to get the access token if available
        const token = await getAccessToken();
        console.log('Authentication token obtained:', token ? 'Token exists' : 'No token');
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
      } catch (err) {
        // If getAccessToken fails, continue without authentication
        console.error('Error getting access token:', err);
        console.log('Continuing without authentication');
      }
      
      console.log('Making request to API with headers:', headers);
      
      // Use the production endpoint with authentication
      try {
        const response = await fetch(`${API_BASE_URL}/api/interview/feedback`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            interview_id: interviewData.id,
            answers: formattedAnswers,
            job_title: interviewData.jobTitle,
            interview_type: interviewData.interviewType,
            questions: interviewData.questions // Include the questions in the evaluation request
          }),
        });
        
        console.log('API response status:', response.status);
        
        if (response.ok) {
          const evaluationData = await response.json();
          
          // Store evaluation data with a unique key that includes the interview ID
          localStorage.setItem(`interviewEvaluation_${interviewData.id}`, JSON.stringify({
            interviewId: interviewData.id,
            jobTitle: interviewData.jobTitle,
            interviewType: interviewData.interviewType,
            timestamp: new Date().toISOString(), // Add timestamp to track when this evaluation was created
            ...evaluationData
          }));
          
          // Also store the latest evaluation ID for easy access
          localStorage.setItem('latestInterviewEvaluation', interviewData.id || '');
        } else {
          console.error('Failed to submit interview feedback, using local evaluation');
          // Always use the local evaluation if the API fails
          await generateLocalEvaluation(formattedAnswers);
        }
      } catch (error) {
        console.error('Error submitting interview feedback:', error);
        // Always use the local evaluation if there's an error
        await generateLocalEvaluation(formattedAnswers);
      }
      
      // Navigate to results page
      router.push(`/interview/results/${interviewData.id}`);
    } catch (err) {
      console.error('Error submitting interview:', err);
      setError('Failed to submit interview. Please try again.');
      setIsSubmitting(false);
    }
  };
  
  // Function to generate a local evaluation using the conversation API or fallback data
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
    
    // If all answers are empty, use a predefined evaluation instead of trying to generate one
    if (forceZeroScore) {
      console.log('Using predefined evaluation for empty or nonsensical answers');
      
      const emptyEvaluation = {
        interviewId: interviewData?.id,
        jobTitle: interviewData?.jobTitle,
        interviewType: interviewData?.interviewType,
        timestamp: new Date().toISOString(),
        score: 0,
        feedback: "The answers provided are empty, making it impossible to evaluate the candidate's knowledge and reasoning skills for the position.",
        strengths: [],
        weaknesses: [
          "No answers provided",
          "Lack of demonstration of technical knowledge",
          "Inability to articulate troubleshooting processes"
        ],
        improvement_areas: [
          "Provide detailed answers to interview questions",
          "Showcase problem-solving and technical skills",
          "Explain concepts clearly and concisely"
        ],
        answers: formattedAnswers,
        questions: interviewData?.questions
      };
      
      // Store the evaluation
      localStorage.setItem(`interviewEvaluation_${interviewData?.id}`, JSON.stringify(emptyEvaluation));
      localStorage.setItem('latestInterviewEvaluation', interviewData?.id || '');
      return;
    }
    
    try {
      // Create a more detailed prompt for evaluation that includes the specific job and answers
      let evaluationPrompt = `You are an expert interview evaluator for ${interviewData?.interviewType || 'technical'} positions. 
Please evaluate the following interview for the position of ${interviewData?.jobTitle || 'Software Engineer'}.

Job Title: ${interviewData?.jobTitle || 'Software Engineer'}
Interview Type: ${interviewData?.interviewType || 'technical'}

Questions and Answers:
`;
      
      // Add questions and answers with more context
      interviewData?.questions.forEach((question, index) => {
        const answer = answers[question.id] || "No answer provided";
        evaluationPrompt += `Question ${index + 1}: ${question.question}\nCandidate's Answer: ${answer}\n\n`;
      });
      
      // Add special instructions for empty answers
      if (hasEmptyAnswers) {
        evaluationPrompt += `
IMPORTANT: The candidate has not provided any substantive answers to the interview questions. 
For candidates who do not provide answers, you should:
1. Give a score of 0 out of 100
2. Provide feedback that clearly states they did not engage with the questions
3. List minimal strengths related only to completing the interview process
4. Focus on the lack of engagement as the primary area for improvement
5. Recommend preparation strategies for future interviews
`;
      }
      
      evaluationPrompt += `
Based on the above interview, please provide a comprehensive evaluation with the following sections:

1. Score: Give a score out of 100 based on the quality, relevance, and completeness of the answers.${hasEmptyAnswers ? ' For empty or minimal answers with no meaningful content, the score should be 0.' : ''}

2. Feedback: Provide detailed overall feedback that highlights key observations from the interview, including the candidate's communication style, technical knowledge, and problem-solving approach.

3. Strengths: List at least 3-5 specific strengths demonstrated in the answers, with brief explanations of each.

4. Areas for Improvement: List at least 3-5 specific areas where the candidate could improve, with brief explanations of each.

5. Recommendations: Provide at least 3-5 specific actionable recommendations for professional development that would help the candidate improve in future interviews.

Format your response with clear section headers (Score, Feedback, Strengths, Areas for Improvement, Recommendations).
Make sure your evaluation is specific to this candidate's actual answers and the ${interviewData?.jobTitle || 'Software Engineer'} position.
`;
      
      let headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      
      try {
        const token = await getAccessToken();
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
      } catch (err) {
        console.error('Error getting access token for local evaluation:', err);
      }
      
      // Make multiple attempts to get an AI-generated evaluation
      let aiGeneratedEvaluation = null;
      
      // First attempt: Try to use the conversation API
      try {
        console.log('Attempting to generate evaluation using conversation API...');
        const response = await fetch(`${API_BASE_URL}/api/interview/conversation`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            job_title: interviewData?.jobTitle || '',
            job_description: interviewData?.jobDescription || interviewData?.jobTitle || '',
            conversation_history: [
              { role: "system", content: "You are an expert interview evaluator for technical positions. Provide a detailed, honest, and constructive evaluation with specific examples from the candidate's answers." },
              { role: "user", content: evaluationPrompt }
            ],
            is_code_submission: false,
            include_follow_up: false
          }),
        });
        
        if (response.ok) {
          const data = await response.json();
          
          // Parse the AI response to extract evaluation components
          const aiText = data.text || "";
          console.log('AI generated evaluation text:', aiText);
          
          // Extract score using regex
          const scoreMatch = aiText.match(/(\d+)\/100|score:?\s*(\d+)|rating:?\s*(\d+)/i);
          let score = scoreMatch ? parseInt(scoreMatch[1] || scoreMatch[2] || scoreMatch[3]) : 70;
          
          // Force score to 0 for empty or nonsensical answers
          if (forceZeroScore) {
            console.log('Forcing score to 0 for empty or nonsensical answers (AI response)');
            score = 0;
          }
          
          console.log('Final score from AI:', score, 'Empty answers:', hasEmptyAnswers, 'Nonsensical answers:', hasNonsensicalAnswers);
          
          // Extract sections
          const feedbackMatch = aiText.match(/feedback:(.*?)(?=strengths:|$)/i);
          const strengthsMatch = aiText.match(/strengths:(.*?)(?=areas for improvement:|weaknesses:|$)/i);
          const weaknessesMatch = aiText.match(/(?:areas for improvement:|weaknesses:)(.*?)(?=recommendations:|suggestions:|$)/i);
          const recommendationsMatch = aiText.match(/(?:recommendations:|suggestions:)(.*?)(?=$)/i);
          
          // Extract lists using regex
          const extractList = (text: string): string[] => {
            if (!text) return [];
            
            // Try to extract numbered or bulleted lists
            const listItems = text.split(/\n\s*[-•*\d]+\.?\s+/).filter((item: string) => item.trim().length > 0);
            
            if (listItems.length > 1) {
              return listItems;
            }
            
            // If no list found, try to split by newlines
            const lines = text.split(/\n+/).filter((line: string) => line.trim().length > 0);
            
            if (lines.length > 1) {
              return lines;
            }
            
            // If still no list, just return the whole text as one item
            return [text.trim()];
          };
          
          const feedback = feedbackMatch ? feedbackMatch[1].trim() : "Thank you for completing the interview.";
          const strengths = strengthsMatch ? extractList(strengthsMatch[1]) : [];
          const weaknesses = weaknessesMatch ? extractList(weaknessesMatch[1]) : [];
          const recommendations = recommendationsMatch ? extractList(recommendationsMatch[1]) : [];
          
          // Check if we have a valid evaluation (has score and at least some content in each section)
          if (score > 0 && 
              feedback.length > 20 && 
              strengths.length > 0 && 
              weaknesses.length > 0 && 
              recommendations.length > 0) {
            
            aiGeneratedEvaluation = {
              interviewId: interviewData?.id,
              jobTitle: interviewData?.jobTitle,
              interviewType: interviewData?.interviewType,
              timestamp: new Date().toISOString(),
              score: score,
              feedback: feedback,
              strengths: strengths,
              weaknesses: weaknesses,
              improvement_areas: recommendations,
              answers: formattedAnswers,
              questions: interviewData?.questions
            };
            
            console.log('Successfully generated AI evaluation');
          } else {
            console.warn('AI evaluation was incomplete, missing some sections');
          }
        }
      } catch (error) {
        console.error('Error generating evaluation with conversation API:', error);
      }
      
      // If we have a valid AI-generated evaluation, use it
      if (aiGeneratedEvaluation) {
        // Use a unique key for each interview evaluation
        localStorage.setItem(`interviewEvaluation_${interviewData?.id}`, JSON.stringify(aiGeneratedEvaluation));
        
        // Also store the latest evaluation ID for easy access
        localStorage.setItem('latestInterviewEvaluation', interviewData?.id || '');
        
        return;
      }
      
      // If we couldn't generate an AI evaluation, use job-specific fallback data
      console.warn('Using fallback evaluation data');
      
      // Create more relevant fallback data based on the job title and interview type
      const jobTitle = interviewData?.jobTitle?.toLowerCase() || '';
      const interviewType = interviewData?.interviewType?.toLowerCase() || 'technical';
      
      let fallbackStrengths = [
        "Technical knowledge and understanding of core concepts",
        "Clear communication of ideas",
        "Structured approach to problem-solving"
      ];
      
      let fallbackWeaknesses = [
        "Could provide more detailed examples from past experience",
        "Some technical explanations could be more comprehensive",
        "Consider addressing edge cases in your solutions"
      ];
      
      let fallbackRecommendations = [
        "Practice explaining complex technical concepts with concrete examples",
        "Develop a framework for answering behavioral questions with the STAR method",
        "Expand knowledge in specific technical areas mentioned in the job description",
        "Prepare more detailed examples of past projects and challenges"
      ];
      
      // Customize fallback data based on job title
      if (jobTitle.includes('devops') || jobTitle.includes('devsecops') || jobTitle.includes('sre')) {
        fallbackStrengths = [
          "Understanding of CI/CD principles and implementation",
          "Knowledge of infrastructure as code concepts",
          "Awareness of security considerations in DevOps pipelines"
        ];
        
        fallbackWeaknesses = [
          "Could provide more specific examples of DevOps tools and practices",
          "Explanations of security integration could be more detailed",
          "Consider discussing monitoring and observability in more depth"
        ];
        
        fallbackRecommendations = [
          "Gain hands-on experience with more DevOps tools like Terraform, Ansible, or Kubernetes",
          "Develop deeper knowledge of security practices in CI/CD pipelines",
          "Practice explaining complex infrastructure setups with diagrams and concrete examples",
          "Explore modern observability tools and practices"
        ];
      } else if (jobTitle.includes('frontend') || jobTitle.includes('ui') || jobTitle.includes('ux')) {
        fallbackStrengths = [
          "Understanding of modern frontend frameworks and libraries",
          "Knowledge of UI/UX principles",
          "Awareness of performance optimization techniques"
        ];
        
        fallbackWeaknesses = [
          "Could provide more specific examples of responsive design implementation",
          "Explanations of state management could be more detailed",
          "Consider discussing accessibility considerations in more depth"
        ];
        
        fallbackRecommendations = [
          "Gain more experience with state management solutions",
          "Develop deeper knowledge of web accessibility standards",
          "Practice explaining UI component architecture with diagrams",
          "Explore modern frontend testing strategies"
        ];
      } else if (jobTitle.includes('backend') || jobTitle.includes('api') || jobTitle.includes('server')) {
        fallbackStrengths = [
          "Understanding of API design principles",
          "Knowledge of database concepts and optimization",
          "Awareness of server-side performance considerations"
        ];
        
        fallbackWeaknesses = [
          "Could provide more specific examples of API security implementation",
          "Explanations of database scaling could be more detailed",
          "Consider discussing error handling and logging in more depth"
        ];
        
        fallbackRecommendations = [
          "Gain more experience with different database technologies",
          "Develop deeper knowledge of API security best practices",
          "Practice explaining complex backend architectures with diagrams",
          "Explore modern logging and monitoring solutions"
        ];
      }
      
      // Set appropriate score and feedback based on answer content
      const fallbackScore = forceZeroScore ? 0 : 70;
      console.log('Fallback score:', fallbackScore, 'Empty answers:', hasEmptyAnswers, 'Nonsensical answers:', hasNonsensicalAnswers);
      
      const fallbackFeedback = forceZeroScore 
        ? `Thank you for completing the ${interviewType} interview for the ${interviewData?.jobTitle} position. ${hasEmptyAnswers ? 'However, you did not provide any substantive answers to the questions.' : 'However, your responses appear to be nonsensical or random characters rather than meaningful answers.'} Your score is 0/100 because meaningful responses are required for evaluation.`
        : `Thank you for completing the ${interviewType} interview for the ${interviewData?.jobTitle} position. Your responses have been recorded and evaluated. You demonstrated good technical knowledge but could provide more detailed examples in your answers.`;
      
      // Create the fallback evaluation
      const fallbackEvaluation = {
        interviewId: interviewData?.id,
        jobTitle: interviewData?.jobTitle,
        interviewType: interviewData?.interviewType,
        timestamp: new Date().toISOString(),
        score: fallbackScore,
        feedback: fallbackFeedback,
        strengths: hasEmptyAnswers ? [
          "Completed the interview process",
          "Navigated the interview interface successfully",
          "Submitted the interview for evaluation"
        ] : fallbackStrengths,
        weaknesses: hasEmptyAnswers ? [
          "Did not provide any substantive answers to the interview questions",
          "Unable to demonstrate technical knowledge or problem-solving skills",
          "Did not engage with the interview content"
        ] : fallbackWeaknesses,
        improvement_areas: hasEmptyAnswers ? [
          "Prepare answers for common interview questions in advance",
          "Practice articulating technical concepts clearly and concisely",
          "Engage fully with the interview process by providing detailed responses",
          "Review the technical concepts related to the position before the interview"
        ] : fallbackRecommendations,
        answers: formattedAnswers,
        questions: interviewData?.questions
      };
      
      // Use a unique key for each interview evaluation
      localStorage.setItem(`interviewEvaluation_${interviewData?.id}`, JSON.stringify(fallbackEvaluation));
      
      // Also store the latest evaluation ID for easy access
      localStorage.setItem('latestInterviewEvaluation', interviewData?.id || '');
    } catch (error) {
      console.error('Error generating local evaluation:', error);
      // Fallback to minimal data
      
      const minimalEvaluation = {
        interviewId: interviewData?.id,
        jobTitle: interviewData?.jobTitle,
        interviewType: interviewData?.interviewType,
        timestamp: new Date().toISOString(),
        score: forceZeroScore ? 0 : 70,
        feedback: forceZeroScore 
          ? `Thank you for completing the interview. ${hasEmptyAnswers ? 'However, you did not provide any substantive answers to the questions.' : 'However, your responses appear to be nonsensical or random characters rather than meaningful answers.'} Your score is 0/100 because meaningful responses are required for evaluation.`
          : "Thank you for completing the interview. Your responses have been recorded and evaluated.",
        strengths: forceZeroScore ? [
          "No meaningful strengths could be identified from the provided answers.",
          "Completed the interview process",
          "Submitted the interview for evaluation"
        ] : [
          "Technical knowledge and understanding of core concepts",
          "Clear communication of ideas",
          "Structured approach to problem-solving"
        ],
        weaknesses: forceZeroScore ? [
          hasEmptyAnswers ? "Did not provide any substantive answers to the interview questions" : "Provided nonsensical or random text instead of meaningful answers",
          "Unable to demonstrate technical knowledge or problem-solving skills",
          "Did not engage with the interview content"
        ] : [
          "Could provide more detailed examples from past experience",
          "Some technical explanations could be more comprehensive",
          "Consider addressing edge cases in your solutions"
        ],
        improvement_areas: forceZeroScore ? [
          "Provide thoughtful, relevant answers to interview questions",
          "Take time to understand each question before responding",
          "Engage fully with the interview process by providing detailed responses",
          "Review the technical concepts related to the position before the interview"
        ] : [
          "Practice explaining complex technical concepts with concrete examples",
          "Develop a framework for answering behavioral questions with the STAR method",
          "Expand knowledge in specific technical areas mentioned in the job description",
          "Prepare more detailed examples of past projects and challenges"
        ],
        answers: formattedAnswers,
        questions: interviewData?.questions
      };
      
      // Use a unique key for each interview evaluation
      localStorage.setItem(`interviewEvaluation_${interviewData?.id}`, JSON.stringify(minimalEvaluation));
      
      // Also store the latest evaluation ID for easy access
      localStorage.setItem('latestInterviewEvaluation', interviewData?.id || '');
    }
  };

  // Voice mode functions
  const toggleRecording = async () => {
    // Prevent recording while AI is speaking
    if (isSpeaking) {
      setError('Please wait for the AI to finish speaking before recording.');
      setTimeout(() => setError(''), 3000);
      return;
    }
    
    // Prevent recording while processing audio
    if (isProcessing) {
      setError('Please wait for the audio to be processed before recording again.');
      setTimeout(() => setError(''), 3000);
      return;
    }
    
    if (isRecording) {
      stopRecording();
    } else {
      // If video is on, make sure we have access to the microphone
      if (showVideo && (!localVideoRef.current || !localVideoRef.current.srcObject)) {
        // Initialize WebRTC first to get microphone access
        try {
          await initializeWebRTC();
        } catch (err) {
          console.error('Error initializing WebRTC:', err);
          setError('Failed to access microphone. Please check your permissions.');
          return;
        }
      }
      
      await startRecording();
    }
  };
  
  // Fix the startRecording function to prevent video blanking
  const startRecording = async () => {
    try {
      audioChunksRef.current = [];
      
      // Check if we already have a video stream with audio
      let stream: MediaStream;
      
      // If we have an existing media recorder, stop it first
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        try {
          mediaRecorderRef.current.stop();
          console.log('Stopped existing media recorder');
        } catch (err) {
          console.error('Error stopping existing media recorder:', err);
        }
      }
      
      if (showVideo && localVideoRef.current && localVideoRef.current.srcObject) {
        console.log('Using existing video stream for recording');
        // Get the existing stream
        const existingStream = localVideoRef.current.srcObject as MediaStream;
        
        // Check if it has audio tracks
        if (existingStream.getAudioTracks().length > 0) {
          // Use the existing stream directly if it has audio
          console.log('Using existing stream with audio tracks');
          stream = existingStream;
        } else {
          // If no audio tracks, get audio only without affecting the video
          try {
            console.log('Getting new audio stream to add to existing video stream');
            const audioStream = await navigator.mediaDevices.getUserMedia({ 
              audio: true,
              video: false // Explicitly set video to false
            });
            
            // Create a new stream with both video and audio tracks
            stream = new MediaStream();
            
            // Add all tracks from the existing stream
            existingStream.getTracks().forEach(track => {
              stream.addTrack(track);
            });
            
            // Add audio tracks from the new stream
            audioStream.getAudioTracks().forEach(track => {
              stream.addTrack(track);
            });
            
            // Update the video element with the combined stream
            if (localVideoRef.current) {
              localVideoRef.current.srcObject = stream;
            }
          } catch (err) {
            console.error('Error getting audio stream:', err);
            throw new Error('Failed to access microphone');
          }
        }
      } else {
        // Get a new audio stream if no video stream exists
        console.log('Getting new audio-only stream for recording');
        // Explicitly request only audio to avoid triggering camera
        stream = await navigator.mediaDevices.getUserMedia({ 
          audio: true,
          video: false // Explicitly set video to false
        });
      }
      
      // Create a new MediaRecorder with the stream
      const options = { mimeType: 'audio/webm' };
      const mediaRecorder = new MediaRecorder(stream, options);
      
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
      console.log('Started recording with MediaRecorder state:', mediaRecorder.state);
    } catch (err) {
      setError('Failed to access microphone. Please check your permissions.');
      console.error('Error starting recording:', err);
    }
  };
  
  // Fix the stopRecording function to prevent video blanking
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      try {
        console.log('Stopping recording with MediaRecorder state:', mediaRecorderRef.current.state);
        
        // Only stop if the recorder is active
        if (mediaRecorderRef.current.state !== 'inactive') {
          mediaRecorderRef.current.stop();
          console.log('MediaRecorder stopped');
        }
        
        // Only stop audio tracks from the recorder stream, not from the video stream
        if (mediaRecorderRef.current.stream) {
          // Create a separate reference to the recorder stream
          const recorderStream = mediaRecorderRef.current.stream;
          
          // If we're not showing video, stop all tracks
          if (!showVideo) {
            recorderStream.getTracks().forEach(track => {
              track.stop();
              console.log(`Stopped track: ${track.kind}`);
            });
          } else {
            // If we're showing video, only stop audio tracks that aren't used by the video
            // First, get all audio tracks from the recorder stream
            const audioTracks = recorderStream.getAudioTracks();
            
            // If we have a video stream, don't stop its audio tracks
            if (localVideoRef.current && localVideoRef.current.srcObject) {
              const videoStream = localVideoRef.current.srcObject as MediaStream;
              const videoAudioTracks = videoStream.getAudioTracks();
              
              // Only stop audio tracks that aren't in the video stream
              audioTracks.forEach(track => {
                const isInVideoStream = videoAudioTracks.some(vTrack => vTrack.id === track.id);
                if (!isInVideoStream) {
                  track.stop();
                  console.log(`Stopped audio track not used by video: ${track.id}`);
                } else {
                  console.log(`Kept audio track used by video: ${track.id}`);
                }
              });
            } else {
              // No video stream, stop all audio tracks
              audioTracks.forEach(track => {
                track.stop();
                console.log(`Stopped audio track: ${track.id}`);
              });
            }
          }
          
          console.log('Kept video stream intact during recording stop');
        }
      } catch (err) {
        console.error('Error stopping recording:', err);
      }
      
      setIsRecording(false);
    }
  };
  
  const processAudio = async (audioBlob: Blob) => {
    if (!interviewData) return;
    
    // Check if the audio blob is empty or too small
    if (audioBlob.size < 1000) {
      console.warn('Audio data is too small or empty, skipping transcription');
      setIsProcessing(false);
      return;
    }
    
    setIsProcessing(true);
    
    try {
      // Convert blob to base64
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      
      reader.onloadend = async () => {
        try {
          const base64Audio = reader.result as string;
          // Remove the data URL prefix (e.g., "data:audio/webm;base64,")
          const base64Data = base64Audio.split(',')[1];
          
          // Validate base64 data
          if (!base64Data || base64Data.length < 100) {
            console.warn('Base64 audio data is too small or invalid, skipping transcription');
            setIsProcessing(false);
            return;
          }
          
          // Get authentication token
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
          }
        } catch (err) {
          console.error('Error in audio processing:', err);
          setError('Failed to process audio. Please try again.');
          setIsProcessing(false);
        }
      };
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
    
    // Set a timeout to reset isProcessing if the API call takes too long
    const processingTimeout = setTimeout(() => {
      console.log('API call timeout reached, resetting isProcessing');
      setIsProcessing(false);
    }, 15000); // 15 seconds timeout
    
    try {
      // Check if time is running low (less than 90 seconds)
      const isTimeRunningLow = timeLeft < 90;
      
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
        // If getAccessToken fails, continue without authentication
        console.error('Error getting access token:', err);
        console.log('Continuing without authentication');
      }
      
      console.log('Making request to API with headers:', Object.keys(headers));
      
      // First check if the user is authenticated by making a simple request
      try {
        const authCheckResponse = await fetch(`${API_BASE_URL}/api/health`, {
          method: 'GET',
          headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        });
        
        console.log('Auth check response status:', authCheckResponse.status);
        
        if (authCheckResponse.status === 401) {
          console.warn('User is not authenticated. Redirecting to login page...');
          // Redirect to login page
          router.push('/auth/login');
          clearTimeout(processingTimeout);
          setIsProcessing(false);
          return;
        }
      } catch (err) {
        console.error('Error checking authentication:', err);
        // Continue anyway, the main request will fail if auth is required
      }
      
      const response = await fetch(`${API_BASE_URL}/api/interview/conversation`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          job_title: interviewData.jobTitle,
          job_description: interviewData.jobDescription,
          conversation_history: conversationHistory,
          current_question_index: currentQuestionIndex,
          time_up: timeLeft === 0,
          time_running_low: isTimeRunningLow,
          no_response_detected: isEmptyResponse,
          is_code_submission: isCodeSubmission,
          question_type: interviewData.questions[currentQuestionIndex]?.type || 'general',
          include_follow_up: includeFollowUp
        }),
      });
      
      clearTimeout(processingTimeout);
      
      if (!response.ok) {
        console.error('API error:', response.status, response.statusText);
        const errorText = await response.text();
        console.error('API error details:', errorText);
        throw new Error(`Failed to get AI response: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
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
      
      // Set speaking state immediately to provide visual feedback
      setIsSpeaking(true);
      
      // Get the access token
      let token;
      try {
        token = await getAccessToken();
        console.log('Got access token for text-to-speech');
      } catch (err) {
        console.error('Error getting access token:', err);
        // Continue without token
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
      
      // Preload the audio element to reduce lag
      if (audioRef.current) {
        audioRef.current.preload = 'auto';
      }
      
      // Use a direct fetch to get the base64 audio data
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
        throw new Error(`Failed to generate speech: ${response.status} ${response.statusText}`);
      }
      
      // Get the response as JSON which contains the base64 audio data
      const data = await response.json();
      console.log('Received audio data response');
      
      if (!data || !data.audio) {
        console.error('Received invalid audio data');
        setIsSpeaking(false);
        return Promise.resolve();
      }
      
      // The audio data is already a data URL (data:audio/mp3;base64,...)
      const audioUrl = data.audio;
      console.log('Using audio URL from API response');
      
      // Use the existing audio element instead of creating a new one
      if (audioRef.current) {
        // Set the audio source directly to the data URL
        audioRef.current.src = audioUrl;
        
        // Preload the audio to reduce lag
        audioRef.current.load();
        
        audioRef.current.oncanplaythrough = () => {
          console.log('Audio can play through without buffering');
          // Play the audio once it's loaded
          try {
            const playPromise = audioRef.current?.play();
            if (playPromise) {
              playPromise.catch(err => {
                console.error('Error playing audio:', err);
                setIsSpeaking(false);
              });
            }
          } catch (err) {
            console.error('Error playing audio:', err);
            setIsSpeaking(false);
          }
        };
        
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
        };
      } else {
        console.error('Audio element not found');
        setIsSpeaking(false);
      }
      
      // Return a promise that resolves when the audio finishes playing
      return new Promise((resolve) => {
        if (!audioRef.current) {
          setIsSpeaking(false);
          resolve();
          return;
        }
        
        audioRef.current.onended = () => {
          setIsSpeaking(false);
          resolve();
        };
        
        audioRef.current.onerror = () => {
          setIsSpeaking(false);
          resolve();
        };
        
        // Set a timeout to prevent hanging
        setTimeout(() => {
          if (isSpeaking) {
            setIsSpeaking(false);
            resolve();
          }
        }, 30000); // 30 second timeout
      });
    } catch (err) {
      console.error('Error in speakMessage:', err);
      setIsSpeaking(false);
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
      // First initialize WebRTC, then set the state
      try {
        console.log('Initializing WebRTC before showing video');
        
        // Save the current recording state
        const wasRecording = isRecording;
        let recordingStream = null;
        
        // If recording, pause it temporarily without stopping tracks
        if (wasRecording && mediaRecorderRef.current) {
          try {
            // Save the recording stream for later
            recordingStream = mediaRecorderRef.current.stream;
            console.log('Saved recording stream:', recordingStream.getTracks().map(t => t.kind).join(', '));
            
            // Just pause the recorder without stopping tracks
            if (mediaRecorderRef.current.state === 'recording') {
              mediaRecorderRef.current.pause();
              console.log('Paused recording temporarily');
            }
          } catch (err) {
            console.error('Error pausing recording:', err);
          }
        }
        
        await initializeWebRTC();
        
        // Only set showVideo to true if initialization was successful
        setShowVideo(true);
        setIsVideoConnected(true);
        
        // If we were recording, resume it with the new stream
        if (wasRecording) {
          try {
            // Small delay to ensure everything is initialized
            setTimeout(async () => {
              // If we have a paused recorder, try to resume it
              if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
                try {
                  mediaRecorderRef.current.resume();
                  console.log('Resumed recording');
                } catch (resumeErr) {
                  console.error('Error resuming recording:', resumeErr);
                  // If resume fails, restart recording
                  await startRecording();
                }
              } else {
                // If recorder was stopped or not in paused state, restart it
                await startRecording();
              }
            }, 500);
          } catch (err) {
            console.error('Error resuming recording:', err);
          }
        }
      } catch (err) {
        console.error('Failed to initialize WebRTC:', err);
        setError('Failed to access camera. Please check your permissions.');
      }
    } else {
      // If turning video off, only stop video tracks but keep audio tracks active
      if (localVideoRef.current && localVideoRef.current.srcObject) {
        console.log('Stopping video tracks before hiding video');
        
        // Save the current recording state
        const wasRecording = isRecording;
        let recordingStream = null;
        
        // If recording, pause it temporarily without stopping tracks
        if (wasRecording && mediaRecorderRef.current) {
          try {
            // Save the recording stream for later
            recordingStream = mediaRecorderRef.current.stream;
            console.log('Saved recording stream:', recordingStream.getTracks().map(t => t.kind).join(', '));
            
            // Just pause the recorder without stopping tracks
            if (mediaRecorderRef.current.state === 'recording') {
              mediaRecorderRef.current.pause();
              console.log('Paused recording temporarily');
            }
          } catch (err) {
            console.error('Error pausing recording:', err);
          }
        }
        
        const stream = localVideoRef.current.srcObject as MediaStream;
        
        // Only stop video tracks, keep audio tracks for recording
        stream.getTracks().forEach(track => {
          if (track.kind === 'video') {
            track.stop();
            console.log(`Toggled off: Stopped video track: ${track.kind}, enabled: ${track.enabled}, readyState: ${track.readyState}`);
          }
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
        
        // If we were recording, resume it with the audio-only stream
        if (wasRecording) {
          try {
            // Small delay to ensure everything is initialized
            setTimeout(async () => {
              // If we have a paused recorder, try to resume it
              if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
                try {
                  mediaRecorderRef.current.resume();
                  console.log('Resumed recording');
                } catch (resumeErr) {
                  console.error('Error resuming recording:', resumeErr);
                  // If resume fails, restart recording
                  await startRecording();
                }
              } else {
                // If recorder was stopped or not in paused state, restart it
                await startRecording();
              }
            }, 500);
          } catch (err) {
            console.error('Error resuming recording:', err);
          }
        }
      }
      
      // Set the state after handling the stream
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
    if (timeLeft < 120 && !response.includes("We're running out of time")) {
      response = response + " We're running out of time, so let's move on to the next question.";
    }
    
    // Add the AI response to the conversation
    addAIResponseToConversation(response);
    
    // If in voice mode, play the audio response
    if (interviewData?.useVoiceMode && response) {
      speakMessage(response);
    }
  };

  // Add a cleanup function to stop all media tracks when the component unmounts
  useEffect(() => {
    return () => {
      // Stop all media tracks when component unmounts
      if (localVideoRef.current && localVideoRef.current.srcObject) {
        const stream = localVideoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => {
          track.stop();
        });
        localVideoRef.current.srcObject = null;
      }
      
      // Also stop any recording that might be in progress
      if (mediaRecorderRef.current) {
        try {
          if (mediaRecorderRef.current.state === 'recording') {
            mediaRecorderRef.current.stop();
          }
          if (mediaRecorderRef.current.stream) {
            mediaRecorderRef.current.stream.getTracks().forEach(track => {
              track.stop();
            });
          }
        } catch (err) {
          console.error('Error stopping MediaRecorder during cleanup:', err);
        }
      }
    };
  }, []);

  // Add a cleanup effect when component unmounts or when navigating away
  useEffect(() => {
    // Add event listener for beforeunload to clean up camera
    const handleBeforeUnload = () => {
      console.log('Page is being unloaded, cleaning up media');
      cleanupMedia();
    };
    
    // Function to clean up all media
    const cleanupMedia = () => {
      // Stop all media tracks
      if (localVideoRef.current && localVideoRef.current.srcObject) {
        const stream = localVideoRef.current.srcObject as MediaStream;
        stream.getTracks().forEach(track => {
          track.stop();
          console.log(`Cleanup: Stopped track: ${track.kind}`);
        });
        localVideoRef.current.srcObject = null;
      }
      
      // Stop any active recording
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        if (mediaRecorderRef.current.stream) {
          mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
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
    
    // Add event listeners
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    // For Next.js App Router, we can use the cleanup function to detect navigation away
    // No need to use router.events which is not available in App Router
    
    // Return cleanup function
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      cleanupMedia();
    };
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
                
                {/* Add recording button in video mode */}
                {isVoiceMode && (
                  <div className="mt-4 flex justify-center">
                    <button
                      onClick={toggleRecording}
                      className={`px-4 py-2 rounded-full flex items-center ${
                        isRecording 
                          ? 'bg-red-600 text-white hover:bg-red-700' 
                          : 'bg-indigo-600 text-white hover:bg-indigo-700'
                      } ${(isSpeaking || isProcessing) ? 'opacity-50' : ''}`}
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
            
                {/* Voice mode controls */}
                {isVoiceMode && (
                  <div className="mt-4 flex justify-center">
              <button
                      onClick={toggleRecording}
                      className={`px-4 py-2 rounded-full flex items-center ${
                        isRecording 
                          ? 'bg-red-600 text-white hover:bg-red-700' 
                          : 'bg-indigo-600 text-white hover:bg-indigo-700'
                      } ${(isSpeaking || isProcessing) ? 'opacity-50' : ''}`}
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
      
      {/* Audio element for TTS playback */}
      <audio 
        ref={audioRef} 
        className="hidden" 
        controls={false} 
        autoPlay={false} 
        preload="auto"
        onError={(e) => console.error('Audio element error:', e)}
      ></audio>
    </div>
  );
}
