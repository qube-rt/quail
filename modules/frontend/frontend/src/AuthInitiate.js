import React, { useEffect } from 'react';

import Config from './config';
import {
  getCodeChallenge, getAuthState, getAuthToken, handleLogin, clearAuthData,
} from './utils';

function AuthInitiate() {
  // Check if the user has id_token stored
  if (getAuthToken()) {
    handleLogin();
  } else {
    clearAuthData();
  }

  // Get identity provider from query
  const urlParams = new URLSearchParams(window.location.search);
  const cognitoIdentityProviderName = urlParams.get('identity_provider');

  // Generate login url and redirect user there
  useEffect(async () => {
    const authState = getAuthState();
    const codeChallenge = await getCodeChallenge();
    const loginUrl = Config.auth.getLoginUrl(cognitoIdentityProviderName, authState, codeChallenge);
    window.location = loginUrl;
  }, []);

  return (
    <div>
      <div />
    </div>
  );
}

export default AuthInitiate;
