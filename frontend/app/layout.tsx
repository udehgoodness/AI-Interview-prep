'use client';

import './globals.css';
import { Inter } from 'next/font/google';
import Link from 'next/link';
import Auth0ProviderWithNavigate from '../lib/auth0-provider';
import { AuthProvider } from '../lib/auth-context';
import UserProfile from '../components/ui/user-profile';

const inter = Inter({ subsets: ['latin'] });

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Auth0ProviderWithNavigate>
          <AuthProvider>
            <div className="min-h-screen flex flex-col">
              <header className="bg-white shadow-sm relative z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                  <div className="flex justify-between h-16">
                    <div className="flex">
                      <div className="flex-shrink-0 flex items-center">
                        <Link href="/" className="text-xl font-bold text-indigo-600">
                          AI Interview Prep
                        </Link>
                      </div>
                      <nav className="ml-6 flex space-x-8">
                        <Link
                          href="/"
                          className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                        >
                          Home
                        </Link>
                        <Link
                          href="/interview/setup"
                          className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                        >
                          New Interview
                        </Link>
                        <Link
                          href="/subscription/plans"
                          className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                        >
                          Pricing
                        </Link>
                        <Link
                          href="/about"
                          className="inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                        >
                          About
                        </Link>
                      </nav>
                    </div>
                    <div className="flex items-center">
                      <UserProfile />
                    </div>
                  </div>
                </div>
              </header>
              <main className="flex-grow relative z-0">
                <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
                  {children}
                </div>
              </main>
              <footer className="bg-white relative z-10">
                <div className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
                  <p className="text-center text-sm text-gray-500">
                    &copy; {new Date().getFullYear()} AI Interview Prep. All rights reserved.
                  </p>
                </div>
              </footer>
            </div>
          </AuthProvider>
        </Auth0ProviderWithNavigate>
      </body>
    </html>
  );
}
