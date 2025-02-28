import Link from 'next/link';
import Image from 'next/image';

export default function About() {
  return (
    <div className="container mx-auto px-4 py-12">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-8 text-center">About AI Interview Prep</h1>
        
        <div className="bg-white rounded-lg shadow-lg p-8 mb-12">
          <h2 className="text-2xl font-semibold mb-4">Our Mission</h2>
          <p className="text-gray-700 mb-6">
            At AI Interview Prep, we believe that everyone deserves the opportunity to showcase their best self during job interviews. 
            Our mission is to democratize interview preparation by leveraging cutting-edge AI technology to provide personalized, 
            realistic interview practice that's accessible to all.
          </p>
          <p className="text-gray-700">
            We're committed to helping job seekers build confidence, improve their communication skills, and ultimately 
            land their dream jobs through effective preparation and practice.
          </p>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8 mb-12">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">How It Works</h2>
            <ol className="list-decimal list-inside space-y-3 text-gray-700">
              <li>Enter your target job details and upload your CV</li>
              <li>Our AI analyzes the information to generate relevant interview questions</li>
              <li>Practice with our AI interviewer through video or text</li>
              <li>Receive detailed feedback and performance evaluation</li>
              <li>Track your progress and improve with each practice session</li>
            </ol>
          </div>
          
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">Our Technology</h2>
            <p className="text-gray-700 mb-4">
              We combine state-of-the-art technologies to create a seamless and effective interview preparation experience:
            </p>
            <ul className="list-disc list-inside space-y-2 text-gray-700">
              <li>Advanced AI models for question generation and evaluation</li>
              <li>WebRTC for real-time video communication</li>
              <li>Monaco Editor for technical coding challenges</li>
              <li>Responsive web design for access on any device</li>
            </ul>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow-lg p-8 mb-12">
          <h2 className="text-2xl font-semibold mb-6 text-center">Meet the Team</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-32 h-32 rounded-full bg-gray-300 mx-auto mb-4 overflow-hidden">
                {/* Replace with actual team member image */}
                <div className="w-full h-full flex items-center justify-center text-gray-500">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
              </div>
              <h3 className="text-xl font-medium">Jane Doe</h3>
              <p className="text-gray-600">CEO & Founder</p>
            </div>
            
            <div className="text-center">
              <div className="w-32 h-32 rounded-full bg-gray-300 mx-auto mb-4 overflow-hidden">
                {/* Replace with actual team member image */}
                <div className="w-full h-full flex items-center justify-center text-gray-500">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
              </div>
              <h3 className="text-xl font-medium">John Smith</h3>
              <p className="text-gray-600">CTO</p>
            </div>
            
            <div className="text-center">
              <div className="w-32 h-32 rounded-full bg-gray-300 mx-auto mb-4 overflow-hidden">
                {/* Replace with actual team member image */}
                <div className="w-full h-full flex items-center justify-center text-gray-500">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
              </div>
              <h3 className="text-xl font-medium">Sarah Johnson</h3>
              <p className="text-gray-600">AI Research Lead</p>
            </div>
          </div>
        </div>
        
        <div className="bg-indigo-600 text-white rounded-lg shadow-lg p-8 text-center">
          <h2 className="text-2xl font-semibold mb-4">Ready to Ace Your Next Interview?</h2>
          <p className="mb-6 max-w-2xl mx-auto">
            Start practicing today and gain the confidence you need to succeed in your job interviews.
          </p>
          <Link 
            href="/interview/setup" 
            className="inline-block bg-white text-indigo-600 hover:bg-gray-100 font-bold py-3 px-8 rounded-lg text-lg transition-colors duration-300"
          >
            Get Started
          </Link>
        </div>
      </div>
    </div>
  );
} 