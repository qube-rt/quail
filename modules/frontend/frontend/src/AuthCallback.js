import React from 'react';
import { useNavigate } from 'react-router-dom';

import queryString from 'query-string';

import axios from './axios';
import Config from './config';
import {
  getCodeVerifier, getAuthState, handleLogin, handleLogout,
} from './utils';

function AuthCallback() {
  const navigate = useNavigate();

  // remove the leading hash from the callback params in order to parse the query string
  const urlParams = new URLSearchParams(window.location.search);
  const receivedCode = urlParams.get('code');
  const receivedState = urlParams.get('state');

  const savedState = getAuthState();
  const codeVerifier = getCodeVerifier();

  if (receivedState !== savedState) {
    // eslint-disable-next-line no-console
    console.error('Auth state mismatch detected, redirecting to login.');
    navigate('/auth-initiate');
  }

  React.useEffect(() => {
    axios.post(Config.auth.tokenEndpointUrl, queryString.stringify({
      grant_type: 'authorization_code',
      client_id: Config.auth.cognitoClientId,
      redirect_uri: Config.auth.redirectUrl,
      code: receivedCode,
      code_challenge_method: 'S256',
      code_verifier: codeVerifier,
    }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }).then((response) => {
      const { id_token: idToken, refresh_token: refreshToken } = response.data;
      handleLogin(idToken, refreshToken);
      navigate('/');
    }).catch(() => {
    // eslint-disable-next-line no-console
      console.error('Auth failed, redirecting to logout.');
      handleLogout();
    });
  }, []);

  return (
    <div className="AuthCallback">
      <header className="AuthCallback-header" />
    </div>
  );
}

export default AuthCallback;
