import React, { useContext } from 'react';

import { useOktaAuth } from '@okta/okta-react';
import { makeStyles } from '@mui/styles';
import {
  AppBar, Toolbar, Button, FormControlLabel, Switch, Select, MenuItem, selectClasses, Box,
} from '@mui/material';
import { Brightness4 as Brightness4Icon } from '@mui/icons-material';

import { CustomThemeContext } from '../themes/CustomThemeProvider';
import { getLabel, getUserData } from '../utils';
import logo from '../logo.png';

const useStyles = makeStyles(() => ({
  root: {
    flexGrow: 1,
  },
  toolbar: {
    justifyContent: 'space-between',
  },
  logoButton: {
    backgroundColor: 'transparent',
    border: 0,
    cursor: 'pointer',
    outline: 0,
  },
  logo: {
    height: 28,
  },
  toggleIcon: {
    'margin-top': 5,
  },
  username: {

  },
  selectRoot: {
    padding: 0,
    color: '#fff',
    '&.Mui-focused': {
      backgroundColor: 'inherit',
    },
    '&.MuiOutlinedInput-input': {
      backgroundColor: 'red',
    },
    [`& .${selectClasses.iconStandard}`]: {
      fill: '#fff',
    },
    [`& .${selectClasses.select}`]: {
      paddingBottom: 0,
    },
  },
}));

const TopAppBar = ({ onReload, selectedGroup, setSelectedGroup }) => {
  const classes = useStyles();

  const { oktaAuth } = useOktaAuth();
  const logout = async () => oktaAuth.signOut();

  const { username, groups } = getUserData();

  const { currentTheme, setTheme } = useContext(CustomThemeContext);
  const isDark = Boolean(currentTheme === 'dark');

  const handleThemeChange = (event) => {
    const { checked } = event.target;
    if (checked) {
      setTheme('dark');
    } else {
      setTheme('light');
    }
  };

  return (
    <AppBar position="static" className={classes.appBar}>
      <Toolbar className={classes.toolbar}>
        <button type="button" onClick={onReload} className={classes.logoButton}>
          <img src={logo} alt="Logo" className={classes.logo} />
        </button>
        <Box>
          <Box sx={{
            display: 'inline',

            mx: 2,
          }}
          >
            {username}
          </Box>
          <Select
            value={selectedGroup}
            label="Group"
            variant="standard"
            onChange={(e) => setSelectedGroup(e.target.value)}
            className={classes.selectRoot}
            disableUnderline
            sx={{
              fontWeight: 'bold',
            }}
          >
            {groups.map((group) => (
              <MenuItem value={group} key={group}>{getLabel('groupLabels', group)}</MenuItem>
            ))}
          </Select>
        </Box>
        <div>
          <FormControlLabel
            control={<Switch checked={isDark} onChange={handleThemeChange} color="primary" />}
            label={<Brightness4Icon className={classes.toggleIcon} />}
          />
          <Button onClick={logout} color="inherit">Logout</Button>
        </div>
      </Toolbar>
    </AppBar>
  );
};

export default TopAppBar;
