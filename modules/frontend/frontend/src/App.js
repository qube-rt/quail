import React from 'react';
import {
  BrowserRouter as Router,
  Route,
  Routes,
} from 'react-router-dom';

import Dashboard from './Dashboard';
import AuthCallback from './AuthCallback';
import AuthInitiate from './AuthInitiate';

function App() {
  return (
    <Router>
      <Routes>
        <Route exact path="/" element={<Dashboard />} />
        <Route path="/auth-callback" element={<AuthCallback />} />
        <Route path="/auth-initiate" element={<AuthInitiate />} />
      </Routes>
    </Router>
  );
}

export default App;
