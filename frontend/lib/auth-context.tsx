'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import axios from 'axios';

interface Subscription {
  id: string;
  status: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  plan: {
    id: string;
    name: string;
  };
}

interface Invoice {
  id: string;
  created: string;
  paid: boolean;
  amount_paid: number;
  description: string;
}

interface User {
  id: string;
  email: string;
  full_name: string;
  is_admin: boolean;
  subscription?: Subscription;
  invoices?: Invoice[];
  phone_number?: string;
  job_title?: string;
  industry?: string;
  experience_level?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
  getAccessToken: () => Promise<string>;
  setAuthState: (token: string, userData: User) => void;
  refreshUserData: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  login: () => {},
  logout: () => {},
  getAccessToken: async () => '',
  setAuthState: () => {},
  refreshUserData: async () => {},
});

export const useAuth = () => useContext(AuthContext);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const { isAuthenticated: isAuth0Authenticated, isLoading: isAuth0Loading, loginWithRedirect, logout: auth0Logout, getAccessTokenSilently, user: auth0User } = useAuth0();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Function to fetch user data from our API
  const fetchUserData = async (token: string) => {
    try {
      const response = await axios.get(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching user data:', error);
      return null;
    }
  };

  // Function to refresh user data
  const refreshUserData = async () => {
    if (!isAuthenticated) return;
    
    try {
      const token = await getAccessToken();
      const userData = await fetchUserData(token);
      
      if (userData) {
        setUser(userData);
        localStorage.setItem('user', JSON.stringify(userData));
      }
    } catch (error) {
      console.error('Error refreshing user data:', error);
    }
  };

  // Function to set authentication state after traditional login
  const setAuthState = async (token: string, userData: User) => {
    localStorage.setItem('token', token);
    
    // Fetch fresh user data to ensure we have the latest subscription info
    const freshUserData = await fetchUserData(token);
    const finalUserData = freshUserData || userData;
    
    localStorage.setItem('user', JSON.stringify(finalUserData));
    setUser(finalUserData);
    setIsAuthenticated(true);
    setIsLoading(false);
    
    // Set up axios default headers
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  };

  useEffect(() => {
    const initAuth = async () => {
      // Check if we're still loading Auth0
      if (isAuth0Loading) return;

      // Check if user is authenticated with Auth0
      if (isAuth0Authenticated && auth0User) {
        try {
          // Get the access token
          const token = await getAccessTokenSilently();
          
          // Fetch user data from our API
          const userData = await fetchUserData(token);
          
          if (userData) {
            setUser(userData);
            setIsAuthenticated(true);
            
            // Store token and user data in localStorage for persistence
            localStorage.setItem('token', token);
            localStorage.setItem('user', JSON.stringify(userData));
            
            // Set up axios default headers
            axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
          } else {
            // If we couldn't get user data, we're not fully authenticated
            setIsAuthenticated(false);
            localStorage.removeItem('token');
            localStorage.removeItem('user');
          }
        } catch (error) {
          console.error('Authentication error:', error);
          setIsAuthenticated(false);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      } else {
        // Check for traditional login (fallback)
        const storedUser = localStorage.getItem('user');
        const storedToken = localStorage.getItem('token');
        
        if (storedUser && storedToken) {
          try {
            // Validate the token by making a request to the API
            const userData = await fetchUserData(storedToken);
            
            if (userData) {
              setUser(userData);
              setIsAuthenticated(true);
              
              // Set up axios default headers
              axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`;
            } else {
              // Token is invalid or expired
              setIsAuthenticated(false);
              localStorage.removeItem('token');
              localStorage.removeItem('user');
            }
          } catch (error) {
            console.error('Error validating stored token:', error);
            setIsAuthenticated(false);
            localStorage.removeItem('token');
            localStorage.removeItem('user');
          }
        } else {
          setIsAuthenticated(false);
        }
      }
      
      setIsLoading(false);
    };

    initAuth();
  }, [isAuth0Loading, isAuth0Authenticated, auth0User, getAccessTokenSilently]);

  // Set up Axios interceptor to include the token in all requests
  useEffect(() => {
    const interceptor = axios.interceptors.request.use(async (config) => {
      if (isAuthenticated) {
        try {
          const token = await getAccessToken();
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        } catch (error) {
          console.error('Error getting token for request:', error);
        }
      }
      return config;
    });

    return () => {
      axios.interceptors.request.eject(interceptor);
    };
  }, [isAuthenticated]);

  const login = () => {
    loginWithRedirect();
  };

  const getAccessToken = async (): Promise<string> => {
    if (isAuth0Authenticated) {
      return await getAccessTokenSilently();
    }
    
    // Fallback to traditional token
    return localStorage.getItem('token') || '';
  };

  const handleLogout = () => {
    // Clear local storage
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    
    // If using Auth0, log out from there too
    if (isAuth0Authenticated) {
      auth0Logout({ 
        logoutParams: {
          returnTo: window.location.origin 
        }
      });
    }
    
    // Update state
    setUser(null);
    setIsAuthenticated(false);
  };

  const value = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout: handleLogout,
    getAccessToken,
    setAuthState,
    refreshUserData,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext; 