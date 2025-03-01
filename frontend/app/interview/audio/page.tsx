'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function AudioInterview() {
  const router = useRouter();
  const [jobTitle, setJobTitle] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [isInterviewStarted, setIsInterviewStarted] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [error, setError] = useState('');
  
  const audioRef = useRef<HTMLAudioElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  
  // Initialize the interview
  const startInterview = async () => {
    if (!jobTitle.trim() || !jobDescription.trim()) {
      setError('Please enter both job title and job description');
      return;
    }
    
    setError('');
    setIsProcessing(true);
    
    try {
      // Start with an AI interviewer greeting
      const initialMessage = { role: 'assistant', content: `Hello! I'm your AI interviewer for the ${jobTitle} position. I'll be asking you some questions to learn more about your experience and skills. Let's get started!` };
      setMessages([initialMessage]);
      
      // Generate speech for the initial message
      await speakMessage(initialMessage.content);
      
      setIsInterviewStarted(true);
    } catch (err) {
      setError('Failed to start the interview. Please try again.');
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Handle starting/stopping recording
  const toggleRecording = async () => {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  };
  
  // Start recording audio
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
  
  // Stop recording audio
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Stop all audio tracks
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }
  };
  
  // Process recorded audio
  const processAudio = async (audioBlob: Blob) => {
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
        
        // Get AI response
        await getAIResponse(updatedMessages);
      };
    } catch (err) {
      setError('Failed to process audio. Please try again.');
      console.error(err);
      setIsProcessing(false);
    }
  };
  
  // Get AI response for the conversation
  const getAIResponse = async (conversationHistory: Array<{ role: string; content: string }>) => {
    try {
      const response = await fetch('http://localhost:8000/api/interview/conversation', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          job_title: jobTitle,
          job_description: jobDescription,
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
      
      // Increment question index if this was a question
      if (data.text.includes('?')) {
        setCurrentQuestionIndex(prev => prev + 1);
      }
      
      // Play the audio response
      if (data.audio) {
        const audioSrc = `data:audio/mp3;base64,${data.audio}`;
        if (audioRef.current) {
          audioRef.current.src = audioSrc;
          await audioRef.current.play();
        }
      }
    } catch (err) {
      setError('Failed to get AI response. Please try again.');
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Speak a message using text-to-speech
  const speakMessage = async (text: string) => {
    try {
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
        audioRef.current.src = audioUrl;
        await audioRef.current.play();
      }
    } catch (err) {
      console.error('Failed to speak message:', err);
    }
  };
  
  // End the interview
  const endInterview = () => {
    // In a real app, you might want to save the conversation or generate a summary
    router.push('/');
  };
  
  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {!isInterviewStarted ? (
        <div className="bg-white rounded-lg shadow-lg p-6 md:p-8">
          <h1 className="text-3xl font-bold mb-6 text-center">Audio Interview Setup</h1>
          
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
              {error}
            </div>
          )}
          
          <form onSubmit={(e) => { e.preventDefault(); startInterview(); }} className="space-y-6">
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
            
            <div className="flex justify-between pt-4">
              <Link
                href="/"
                className="px-6 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={isProcessing}
                className={`px-6 py-2 rounded-md bg-indigo-600 text-white font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                  isProcessing ? 'opacity-70 cursor-not-allowed' : ''
                }`}
              >
                {isProcessing ? 'Starting...' : 'Start Audio Interview'}
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          {/* Header */}
          <div className="bg-gray-800 text-white p-4 flex justify-between items-center">
            <div>
              <h1 className="text-xl font-bold">{jobTitle} Interview</h1>
              <p className="text-sm text-gray-300">Audio Conversation Mode</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className={`flex items-center ${isRecording ? 'text-red-400' : 'text-gray-400'}`}>
                <span className={`h-3 w-3 rounded-full ${isRecording ? 'bg-red-500 animate-pulse' : 'bg-gray-500'} mr-1`}></span>
                <span className="text-sm">{isRecording ? 'Recording' : 'Not Recording'}</span>
              </div>
            </div>
          </div>
          
          {/* Conversation area */}
          <div className="p-4 h-96 overflow-y-auto bg-gray-50">
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
          
          {/* Controls */}
          <div className="bg-gray-100 p-4 border-t border-gray-200">
            <div className="flex justify-center mb-4">
              <button
                onClick={toggleRecording}
                disabled={isProcessing}
                className={`w-16 h-16 rounded-full flex items-center justify-center ${
                  isRecording 
                    ? 'bg-red-600 hover:bg-red-700' 
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
            </div>
            
            <div className="text-center mb-4">
              <p className="text-sm text-gray-600">
                {isRecording 
                  ? 'Click to stop recording' 
                  : 'Click to start recording your answer'}
              </p>
            </div>
            
            <div className="flex justify-between">
              <button
                onClick={endInterview}
                className="px-4 py-2 border border-gray-300 rounded-md bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                End Interview
              </button>
            </div>
          </div>
          
          {/* Hidden audio element for playing responses */}
          <audio ref={audioRef} className="hidden" />
        </div>
      )}
    </div>
  );
} 