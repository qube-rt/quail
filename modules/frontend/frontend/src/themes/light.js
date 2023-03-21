import { createTheme } from '@mui/material/styles';
import { red } from '@mui/material/colors';

// A light theme for this app, adapted from https://www.58bits.com/blog/2020/05/27/material-ui-theme-switcher-react
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
    type: 'light',
    primary: {
      main: '#556cd6',
    },
    secondary: {
      main: '#cc4444',
    },
    error: {
      main: red.A400,
    },
    background: {
      default: '#f5f5f5',
    },
    titleBar: {
      main: '#eeeeee',
      contrastText: '#222222',
    },
  },
});

export default theme;
