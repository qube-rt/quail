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
import Config from '../config';
import { formatDate } from '../utils';

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
    regionMap,
    selectedRegion,
    selectedAccount,
    selectedInstanceType,
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
  const accounts = regionMap ? Object.keys(regionMap) : [];
  const currentRegionMap = regionMap && selectedAccount && regionMap[selectedAccount]
    ? regionMap[selectedAccount] : undefined;
  const regions = currentRegionMap ? Object.keys(currentRegionMap) : [];
  const instanceTypes = currentRegionMap && selectedRegion
    ? currentRegionMap[selectedRegion].instance_types : [];
  const operatingSystems = currentRegionMap && selectedRegion
    ? currentRegionMap[selectedRegion].os_types : [];

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
          <Grid container spacing={3} justifyContent="center" alignItems="center" pb={1}>
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

        <Grid container spacing={3} justifyContent="center" alignItems="center" pb={1}>
          <Grid item xs={2}>
            <SelectField
              label="Account"
              fieldName="selectedAccount"
              values={accounts}
              selected={selectedAccount}
              onFieldChange={onFieldChange}
              disabled={formDisabled}
              classes={classes}
              valueLabels={Config.accountLabels}
            />
          </Grid>

          <Grid item xs={2}>
            <SelectField
              label="Region"
              fieldName="selectedRegion"
              values={regions}
              valueLabels={Config.regionLabels}
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
              valueLabels={Config.instanceLabels}
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
                rifmFormatter={(unformatted) => formatDate(new Date(unformatted))}
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
        </Grid>

        <Grid container spacing={3} justifyContent="center" alignItems="center" pb={1}>
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
