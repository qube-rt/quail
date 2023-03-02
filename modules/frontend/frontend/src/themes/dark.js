import { createTheme } from '@material-ui/core/styles';
import { red } from '@material-ui/core/colors';

// A dark theme for this app, adapted from https://www.58bits.com/blog/2020/05/27/material-ui-theme-switcher-react
const theme = createTheme({
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 960,
      lg: 1420,
      xl: 1920,
    },
  },
  overrides: {
    MuiTooltip: {
      tooltipPlacementBottom: {
        margin: '4 0',
      },
    },
  },
  palette: {
    type: 'dark',
    primary: {
      main: '#26292C',
      light: 'rgb(81, 91, 95)',
      dark: 'rgb(26, 35, 39)',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#FFB74D',
      light: 'rgb(255, 197, 112)',
      dark: 'rgb(200, 147, 89)',
      contrastText: 'rgba(0, 0, 0, 0.87)',
    },
    background: {
      default: '#414445',
    },
    error: {
      main: red.A400,
    },
    titleBar: {
      main: '#555555',
      contrastText: '#ffffff',
    },
  },
});

export default theme;
