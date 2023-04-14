import React from 'react';
import { useNavigate } from 'react-router-dom';

import {
  getCodeVerifier, getAuthState, handleLogin, handleLogout,
} from './utils';
import appApi from './api';

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
    appApi.getCognitoToken({ receivedCode, codeVerifier })
      .then((response) => {
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
