import React, { useState } from 'react';

import { makeStyles } from '@mui/styles';
import { AddCircle as AddCircleIcon } from '@mui/icons-material';
import {
  Paper, Grid, LinearProgress, TextField,
} from '@mui/material';
import { AdapterMoment } from '@mui/x-date-pickers/AdapterMoment';
import { DateTimePicker, LocalizationProvider } from '@mui/x-date-pickers';
import { Alert } from '@mui/lab';

import SelectField from './SelectField';
import DebouncedButton from './DebouncedButton';
import labels from '../labels';

const useStyles = makeStyles((theme) => ({
  formControl: {
    marginTop: theme.spacing(1),
    marginBottom: theme.spacing(1),
    marginLeft: theme.spacing(2),
    marginRight: theme.spacing(2),
    minWidth: 120,
    width: '85%',
  },
  selectEmpty: {
    marginTop: theme.spacing(2),
  },
  alert: {
    margin: '1em',
  },
}));

const InstanceForm = (props) => {
  const classes = useStyles();
  const {
    is_superuser,
    regions,
    selectedRegion,
    instanceTypes,
    selectedInstanceType,
    operatingSystems,
    selectedOperatingSystem,
    expiry,
    maxExpiry,
    instanceName,
    username,
    email,

    onDateChange,
    onFieldChange,
    onSubmit,
    formLoading,
    nonFormError,
    formErrors,
    provisionLoading,
  } = props;

  const [open, setOpen] = useState(false);

  // Calculated values
  const formDisabled = !!nonFormError;

  // Render
  let content;
  if (formLoading) {
    content = <LinearProgress />;
  } else if (formDisabled) {
    content = (
      <Grid container spacing={3} justify="center" alignItems="center">
        <Alert variant="standard" severity="error" className={classes.alert}>
          { nonFormError}
        </Alert>
      </Grid>
    );
  } else {
    content = (
      <>
        {is_superuser ? (
          <Grid container spacing={3} justifyContent="center" alignItems="center">
            <Grid item xs={3}>
              <TextField
                label="User name"
                value={username}
                onChange={(e) => onFieldChange(e, 'username')}
                error={!!formErrors.username}
                helperText={formErrors.username}
                disabled={formDisabled}
                variant="standard"
              />
            </Grid>
            <Grid item xs={3}>
              <TextField
                label="User email"
                value={email}
                onChange={(e) => onFieldChange(e, 'email')}
                error={!!formErrors.email}
                helperText={formErrors.email}
                disabled={formDisabled}
                variant="standard"
              />
            </Grid>
          </Grid>
        ) : ''}

        <Grid container spacing={3} justifyContent="center" alignItems="center">
          <Grid item xs={2}>
            <SelectField
              label="Region"
              fieldName="region"
              values={regions}
              valueLabels={labels.regions}
              selected={selectedRegion}
              onFieldChange={onFieldChange}
              disabled={formDisabled}
              classes={classes}
            />
          </Grid>

          <Grid item xs={2}>
            <SelectField
              label="Instance Type"
              fieldName="instanceType"
              values={instanceTypes}
              valueLabels={labels.instanceTypes}
              selected={selectedInstanceType}
              disabled={formDisabled}
              onFieldChange={onFieldChange}
              classes={classes}
            />
          </Grid>

          <Grid item xs={2}>
            <SelectField
              label="Operating System"
              fieldName="operatingSystem"
              values={operatingSystems}
              selected={selectedOperatingSystem}
              onFieldChange={onFieldChange}
              disabled={formDisabled}
              classes={classes}
            />
          </Grid>

          <Grid item xs={2}>
            <LocalizationProvider dateAdapter={AdapterMoment}>
              <DateTimePicker
                label="Instance expiry"
                open={open}
                onOpen={() => setOpen(true)}
                onClose={() => setOpen(false)}
                ampm={false}
                disablePast
                views={['day', 'hours']}
                maxDate={maxExpiry}
                value={expiry}
                onChange={(e) => onDateChange(e.toDate(), 'expiry')}
                disabled={formDisabled}
                renderInput={(params) => (
                  <TextField
                    // eslint-disable-next-line react/jsx-props-no-spreading
                    {...params}
                    onClick={() => setOpen(true)}
                    variant="standard"
                    error={!!formErrors.expiry}
                    helperText={formErrors.expiry}
                  />
                )}
              />
            </LocalizationProvider>
          </Grid>

          <Grid item xs={2}>
            <TextField
              label="Instance Name"
              value={instanceName}
              onChange={(e) => onFieldChange(e, 'instanceName')}
              error={!!formErrors.instanceName}
              helperText={formErrors.instanceName}
              disabled={formDisabled}
              variant="standard"
            />
          </Grid>

          <Grid item xs={2} className={classes.buttonRoot}>
            <DebouncedButton
              variant="contained"
              color="primary"
              engaged={provisionLoading}
              startIcon={<AddCircleIcon />}
              disabled={formDisabled}
              onClick={onSubmit}
            >
              Provision
            </DebouncedButton>
          </Grid>

        </Grid>
      </>
    );
  }

  return (
    <Paper>
      {content}
    </Paper>
  );
};

export default InstanceForm;
