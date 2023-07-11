import { createTheme } from '@mui/material/styles';
import { red } from '@mui/material/colors';

// A dark theme for this app, adapted from https://www.58bits.com/blog/2020/05/27/material-ui-theme-switcher-react
const theme = createTheme({
  components: {
    MuiSwitch: {
      styleOverrides: {
        switchBase: {
          // Controls default (unchecked) color for the thumb
          color: '#ccc',
        },
        colorPrimary: {
          '&.Mui-checked': {
            // Controls checked color for the thumb
            color: '#fff',
          },
        },
        track: {
          // Controls default (unchecked) color for the track
          opacity: 0.2,
          backgroundColor: '#fff',
          '.Mui-checked.Mui-checked + &': {
            // Controls checked color for the track
            opacity: 0.7,
            backgroundColor: '#fff',
          },
        },
      },
    },
    MuiTypography: {
      variants: [
        {
          props: { variant: 'h5' }, /* component props */
          style: {
            /* your style here: */
            color: 'white',
            fontWeight: 'bold',
          },
        },
      ],
    },
  },
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
  typography: {
    color: 'white',
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
