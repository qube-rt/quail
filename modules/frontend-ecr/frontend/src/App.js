import React from 'react';
import {
  Route,
  Routes,
  useNavigate,
} from 'react-router-dom';
import { LoginCallback, Security } from '@okta/okta-react';
import { OktaAuth, toRelativeUrl } from '@okta/okta-auth-js';

import { SnackbarProvider } from 'notistack';
import Config from './config';
import Dashboard from './Dashboard';
import RequiredAuth from './components/SecuredRoute';
import { AxiosInterceptor } from './Axios';

const oktaAuth = new OktaAuth(Config.oidc);

function App() {
  const navigate = useNavigate();
  const restoreOriginalUri = (_oktaAuth, originalUri) => {
    navigate(toRelativeUrl(originalUri || '/', window.location.origin));
  };

  return (
    <Security oktaAuth={oktaAuth} restoreOriginalUri={restoreOriginalUri}>
      <AxiosInterceptor>
        <SnackbarProvider anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} autoHideDuration={5000} />
        <Routes>
          <Route exact path="/" element={<RequiredAuth />}>
            <Route path="" element={<Dashboard />} />
          </Route>
          {/* <Route  path="/" element={<Dashboard />} /> */}
          {/* <Route path="/auth-callback" element={<AuthCallback />} /> */}
          {/* <Route path="/auth-initiate" element={<AuthInitiate />} /> */}
          <Route path="/login/callback" element={<LoginCallback />} />
        </Routes>
      </AxiosInterceptor>
    </Security>
  );
}

export default App;
