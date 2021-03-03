import 'react-app-polyfill/ie11';
import 'react-app-polyfill/stable';

import React from 'react';
import ReactDOM from 'react-dom';

import CssBaseline from '@material-ui/core/CssBaseline';
import { SnackbarProvider } from 'notistack';

import App from './App';
import CustomThemeProvider from './themes/CustomThemeProvider';
import './index.css';
// ========================================

ReactDOM.render(
  // Unfortunately, Theming clashes with Strict mode
  // <React.StrictMode>
  <CustomThemeProvider>
    <SnackbarProvider anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }} autoHideDuration={5000}>
      <CssBaseline />
      <App />
    </SnackbarProvider>
  </CustomThemeProvider>,
  // </React.StrictMode>

  document.getElementById('root'),
);
