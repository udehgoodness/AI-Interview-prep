import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Interview Prep",
  description: "AI-powered interview preparation platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="flex flex-col min-h-screen">
          {/* Header */}
          <header className="bg-gray-900 text-white shadow-md">
            <div className="container mx-auto px-6 py-4">
              <div className="flex justify-between items-center">
                <Link href="/" className="text-2xl font-bold">
                  AI Interview Prep
                </Link>
                <nav className="hidden md:flex space-x-8">
                  <Link href="/" className="hover:text-indigo-400 transition-colors">
                    Home
                  </Link>
                  <Link href="/interview/setup" className="hover:text-indigo-400 transition-colors">
                    Practice
                  </Link>
                  <Link href="/about" className="hover:text-indigo-400 transition-colors">
                    About
                  </Link>
                </nav>
                <div className="flex space-x-4">
                  <Link 
                    href="/auth/login" 
                    className="hover:text-indigo-400 transition-colors"
                  >
                    Login
                  </Link>
                  <Link 
                    href="/auth/signup" 
                    className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg transition-colors"
                  >
                    Sign Up
                  </Link>
                </div>
              </div>
            </div>
          </header>

          {/* Main content */}
          <main className="flex-grow">
            {children}
          </main>

          {/* Footer */}
          <footer className="bg-gray-900 text-white py-8">
            <div className="container mx-auto px-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div>
                  <h3 className="text-xl font-bold mb-4">AI Interview Prep</h3>
                  <p className="text-gray-400">
                    Prepare for your next interview with our AI-powered platform.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-4">Quick Links</h3>
                  <ul className="space-y-2">
                    <li>
                      <Link href="/" className="text-gray-400 hover:text-white transition-colors">
                        Home
                      </Link>
                    </li>
                    <li>
                      <Link href="/interview/setup" className="text-gray-400 hover:text-white transition-colors">
                        Practice Interview
                      </Link>
                    </li>
                    <li>
                      <Link href="/about" className="text-gray-400 hover:text-white transition-colors">
                        About Us
                      </Link>
                    </li>
                  </ul>
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-4">Contact</h3>
                  <ul className="space-y-2 text-gray-400">
                    <li>Email: contact@aiinterviewprep.com</li>
                    <li>Follow us on Twitter: @aiinterviewprep</li>
                  </ul>
                </div>
              </div>
              <div className="border-t border-gray-800 mt-8 pt-6 text-center text-gray-400">
                <p>&copy; {new Date().getFullYear()} AI Interview Prep. All rights reserved.</p>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
