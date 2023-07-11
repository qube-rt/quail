import React from 'react';

import { makeStyles } from '@mui/styles';
import { CircularProgress, Button } from '@mui/material';

const useStyles = makeStyles((theme) => ({
  root: {
    display: 'flex',
    alignItems: 'center',
  },
  buttonRoot: {
    display: 'flex',
    alignItems: 'center',
  },
  wrapper: {
    margin: theme.spacing(0.25),
    position: 'relative',
  },
  buttonSpinner: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    marginTop: -12,
    marginLeft: -12,
  },
}));

export default function DebouncedButton(props) {
  const classes = useStyles();

  const {
    onClick, variant, engaged, disabled, color, startIcon, children,
  } = props;

  return (
    <div className={classes.root}>
      <div className={classes.wrapper}>
        <Button
          variant={variant}
          color={color}
          disabled={disabled || engaged}
          startIcon={startIcon}
          onClick={onClick}
        >
          {children}
        </Button>
        { engaged
     && <CircularProgress size={24} className={classes.buttonSpinner} />}
      </div>
    </div>
  );
}
