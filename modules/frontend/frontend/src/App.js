import React from 'react';
import {
  BrowserRouter as Router,
  Switch,
  Route,
} from 'react-router-dom';

import Dashboard from './Dashboard';
import AuthCallback from './AuthCallback';
import AuthInitiate from './AuthInitiate';

function App() {
  return (
    <Router>
      <Switch>
        <Route exact path="/">
          <Dashboard />
        </Route>
        <Route path="/auth-callback">
          <AuthCallback />
        </Route>
        <Route path="/auth-initiate">
          <AuthInitiate />
        </Route>
      </Switch>
    </Router>
  );
}

export default App;
