'use client';

import { useRouter } from 'next/navigation';
import { Auth0Provider } from '@auth0/auth0-react';
import { ReactNode } from 'react';

interface Auth0ProviderWithNavigateProps {
  children: ReactNode;
}

export default function Auth0ProviderWithNavigate({ children }: Auth0ProviderWithNavigateProps) {
  const router = useRouter();
  
  // Environment variables
  const domain = process.env.NEXT_PUBLIC_AUTH0_DOMAIN;
  const clientId = process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID;
  const audience = process.env.NEXT_PUBLIC_AUTH0_AUDIENCE;
  
  if (!domain || !clientId || !audience) {
    console.error('Auth0 environment variables are not set');
    return <>{children}</>;
  }

  const onRedirectCallback = (appState: any) => {
    router.push(appState?.returnTo || '/');
  };

  return (
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : '',
        audience: audience,
        scope: 'openid profile email',
        connection: 'google-oauth2'
      }}
      onRedirectCallback={onRedirectCallback}
      cacheLocation="localstorage"
    >
      {children}
    </Auth0Provider>
  );
} 