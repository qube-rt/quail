import 'react-app-polyfill/ie11';
import 'react-app-polyfill/stable';

import React from 'react';
import ReactDOM from 'react-dom';
import { BrowserRouter } from 'react-router-dom';

import { CssBaseline } from '@mui/material';

import App from './App';
import CustomThemeProvider from './themes/CustomThemeProvider';
import './index.css';
// ========================================

ReactDOM.render(
  // Unfortunately, Theming clashes with Strict mode
  <React.StrictMode>
    <CustomThemeProvider>
      <CssBaseline />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </CustomThemeProvider>
  </React.StrictMode>,

  document.getElementById('root'),
);
