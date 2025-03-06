'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '../../lib/auth-context';

// Team member data
const teamMembers = [
  {
    name: 'Sarah Johnson',
    role: 'CEO & Founder',
    bio: 'Former HR executive with 15+ years of experience in talent acquisition and development.',
    image: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?ixlib=rb-1.2.1&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80'
  },
  {
    name: 'Michael Chen',
    role: 'CTO',
    bio: 'AI researcher with a PhD in Natural Language Processing and 10+ years of industry experience.',
    image: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?ixlib=rb-1.2.1&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80'
  },
  {
    name: 'Priya Patel',
    role: 'Head of Product',
    bio: 'Product leader with experience at top tech companies, focused on creating intuitive user experiences.',
    image: 'https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?ixlib=rb-1.2.1&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80'
  },
  {
    name: 'James Wilson',
    role: 'Lead AI Engineer',
    bio: 'Machine learning specialist with expertise in conversational AI and natural language understanding.',
    image: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?ixlib=rb-1.2.1&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80'
  }
];

// FAQ data
const faqs = [
  {
    question: 'How does AI Interview Prep work?',
    answer: 'Our platform uses advanced AI to generate personalized interview questions based on your resume, job description, and industry. You can practice answering these questions in a realistic interview environment, and receive detailed feedback and suggestions for improvement.'
  },
  {
    question: 'Is my data secure?',
    answer: 'Yes, we take data security very seriously. All your personal information, interview responses, and feedback are encrypted and securely stored. We never share your data with third parties without your explicit consent.'
  },
  {
    question: 'How many interviews can I do with the free plan?',
    answer: 'Free users can conduct up to 3 mock interviews per month. If you need more practice, you can upgrade to one of our premium plans for additional interviews and features.'
  },
  {
    question: 'Can I practice technical interviews?',
    answer: 'Absolutely! We offer specialized technical interviews for various roles including software engineering, data science, and more. These interviews include coding challenges and technical questions specific to your field.'
  },
  {
    question: 'How do I get started?',
    answer: 'Simply sign up for a free account, enter your job details, and start practicing! You can upload your resume for more personalized questions, or jump right in with our general interview questions.'
  }
];

export default function AboutPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const [activeTab, setActiveTab] = useState('mission');
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);

  const toggleFaq = (index: number) => {
    if (expandedFaq === index) {
      setExpandedFaq(null);
    } else {
      setExpandedFaq(index);
    }
  };

  return (
    <div className="bg-white">
      {/* Hero section */}
      <div className="relative isolate overflow-hidden bg-gradient-to-b from-indigo-100/20">
        <div className="mx-auto max-w-7xl pb-24 pt-10 sm:pb-32 lg:grid lg:grid-cols-1 lg:gap-x-8 lg:px-8 lg:py-40">
          <div className="px-6 lg:px-0 lg:pt-4">
            <div className="mx-auto max-w-2xl">
              <div className="max-w-lg">
                <h1 className="mt-10 text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
                  Revolutionizing Interview Preparation
                </h1>
                <p className="mt-6 text-lg leading-8 text-gray-600">
                  We're on a mission to help job seekers worldwide ace their interviews through personalized AI-powered practice and feedback.
                </p>
              </div>
            </div>
          </div>
        </div>
        <div className="absolute inset-x-0 bottom-0 -z-10 h-24 bg-gradient-to-t from-white sm:h-32" />
      </div>

      {/* Tabs section */}
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          <div className="mt-6 sm:mt-10 flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('mission')}
              className={`px-4 py-2 text-sm font-medium ${
                activeTab === 'mission'
                  ? 'border-b-2 border-indigo-500 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Our Mission
            </button>
            <button
              onClick={() => setActiveTab('technology')}
              className={`ml-8 px-4 py-2 text-sm font-medium ${
                activeTab === 'technology'
                  ? 'border-b-2 border-indigo-500 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Our Technology
            </button>
            <button
              onClick={() => setActiveTab('team')}
              className={`ml-8 px-4 py-2 text-sm font-medium ${
                activeTab === 'team'
                  ? 'border-b-2 border-indigo-500 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Our Team
            </button>
            <button
              onClick={() => setActiveTab('faq')}
              className={`ml-8 px-4 py-2 text-sm font-medium ${
                activeTab === 'faq'
                  ? 'border-b-2 border-indigo-500 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              FAQ
            </button>
          </div>

          <div className="mt-8 flow-root">
            {activeTab === 'mission' && (
              <div className="prose prose-lg prose-indigo mx-auto text-gray-500">
                <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">Our Mission</h2>
                <p className="mt-6">
                  At AI Interview Prep, we believe that everyone deserves the opportunity to showcase their true potential in job interviews. Our mission is to democratize interview preparation by leveraging cutting-edge AI technology to provide personalized, effective, and accessible interview training for job seekers at all levels.
                </p>
                <p className="mt-6">
                  We're committed to helping candidates build confidence, improve their communication skills, and present their qualifications effectively. By providing realistic practice environments and actionable feedback, we aim to level the playing field and help talented individuals land their dream jobs.
                </p>
                <p className="mt-6">
                  Our vision is a world where interview success is determined by a candidate's true abilities and potential, not by their access to expensive coaching or insider connections. We're working to make that vision a reality through technology that's accessible to everyone.
                </p>
              </div>
            )}

            {activeTab === 'technology' && (
              <div className="prose prose-lg prose-indigo mx-auto text-gray-500">
                <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">Our Technology</h2>
                <p className="mt-6">
                  Our platform is built on state-of-the-art AI models that understand the nuances of different industries and job roles. The system analyzes your resume and the job description to generate relevant questions, evaluates your responses in real-time, and provides detailed feedback on content, delivery, and overall impression.
                </p>
                <h3 className="text-xl font-bold text-gray-900 mt-8">Key Features</h3>
                <ul className="mt-4 space-y-4">
                  <li className="flex items-start">
                    <div className="flex-shrink-0">
                      <svg className="h-6 w-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <p className="ml-3">
                      <strong className="font-semibold text-gray-900">Natural Language Understanding</strong> - Our AI comprehends the context and intent behind interview questions and your responses.
                    </p>
                  </li>
                  <li className="flex items-start">
                    <div className="flex-shrink-0">
                      <svg className="h-6 w-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <p className="ml-3">
                      <strong className="font-semibold text-gray-900">Speech Recognition and Analysis</strong> - For voice interviews, we analyze not just what you say, but how you say it.
                    </p>
                  </li>
                  <li className="flex items-start">
                    <div className="flex-shrink-0">
                      <svg className="h-6 w-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <p className="ml-3">
                      <strong className="font-semibold text-gray-900">Industry-Specific Knowledge</strong> - Our models are trained on data from various industries to provide relevant and accurate feedback.
                    </p>
                  </li>
                  <li className="flex items-start">
                    <div className="flex-shrink-0">
                      <svg className="h-6 w-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <p className="ml-3">
                      <strong className="font-semibold text-gray-900">Personalized Recommendations</strong> - Get tailored suggestions to improve your interview performance based on your specific strengths and weaknesses.
                    </p>
                  </li>
                </ul>
              </div>
            )}

            {activeTab === 'team' && (
              <div>
                <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">Our Team</h2>
                <p className="mt-6 text-lg text-gray-500">
                  AI Interview Prep was founded by a team of AI researchers, HR professionals, and career coaches who recognized the potential of artificial intelligence to transform the interview preparation process.
                </p>
                <div className="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
                  {teamMembers.map((member, index) => (
                    <div key={index} className="bg-white overflow-hidden shadow rounded-lg">
                      <div className="aspect-w-3 aspect-h-2">
                        <img
                          className="object-cover w-full h-48"
                          src={member.image}
                          alt={member.name}
                        />
                      </div>
                      <div className="px-4 py-5 sm:p-6">
                        <h3 className="text-lg font-medium text-gray-900">{member.name}</h3>
                        <p className="text-sm text-indigo-600 mb-3">{member.role}</p>
                        <p className="text-sm text-gray-500">{member.bio}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'faq' && (
              <div>
                <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">Frequently Asked Questions</h2>
                <p className="mt-6 text-lg text-gray-500">
                  Find answers to common questions about AI Interview Prep.
                </p>
                <div className="mt-10 space-y-6 divide-y divide-gray-200">
                  {faqs.map((faq, index) => (
                    <div key={index} className="pt-6">
                      <dt>
                        <button
                          onClick={() => toggleFaq(index)}
                          className="flex w-full items-start justify-between text-left text-gray-900"
                        >
                          <span className="text-lg font-semibold">{faq.question}</span>
                          <span className="ml-6 flex h-7 items-center">
                            <svg
                              className={`h-6 w-6 transform ${expandedFaq === index ? 'rotate-180' : 'rotate-0'}`}
                              xmlns="http://www.w3.org/2000/svg"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </span>
                        </button>
                      </dt>
                      {expandedFaq === index && (
                        <dd className="mt-2 pr-12">
                          <p className="text-base text-gray-500">{faq.answer}</p>
                        </dd>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* CTA section */}
      <div className="bg-indigo-50 mt-24">
        <div className="mx-auto max-w-7xl py-12 px-6 lg:flex lg:items-center lg:justify-between lg:py-16 lg:px-8">
          <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            <span className="block">Ready to improve your interview skills?</span>
            <span className="block text-indigo-600">Start practicing today.</span>
          </h2>
          <div className="mt-8 flex lg:mt-0 lg:flex-shrink-0">
            <div className="inline-flex rounded-md shadow">
              {isLoading ? (
                <div className="animate-pulse rounded-md bg-indigo-600 px-8 py-3 w-40 h-12"></div>
              ) : isAuthenticated ? (
                <Link
                  href="/interview/setup"
                  className="inline-flex items-center justify-center rounded-md border border-transparent bg-indigo-600 px-5 py-3 text-base font-medium text-white hover:bg-indigo-700"
                >
                  Start a Mock Interview
                </Link>
              ) : (
                <Link
                  href="/auth/signup"
                  className="inline-flex items-center justify-center rounded-md border border-transparent bg-indigo-600 px-5 py-3 text-base font-medium text-white hover:bg-indigo-700"
                >
                  Sign up for free
                </Link>
              )}
            </div>
            <div className="ml-3 inline-flex rounded-md shadow">
              <Link
                href="/subscription/plans"
                className="inline-flex items-center justify-center rounded-md border border-transparent bg-white px-5 py-3 text-base font-medium text-indigo-600 hover:bg-indigo-50"
              >
                View pricing
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 