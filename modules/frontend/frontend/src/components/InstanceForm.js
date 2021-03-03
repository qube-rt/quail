import React from 'react';

import { makeStyles } from '@material-ui/core/styles';
import AddCircleIcon from '@material-ui/icons/AddCircle';
import Paper from '@material-ui/core/Paper';
import Grid from '@material-ui/core/Grid';
import TextField from '@material-ui/core/TextField';
import LinearProgress from '@material-ui/core/LinearProgress';
import { MuiPickersUtilsProvider, DateTimePicker } from '@material-ui/pickers';
import MomentUtils from '@date-io/moment';
import MuiAlert from '@material-ui/lab/Alert';

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

export default function InstanceForm(props) {
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

  // Calculated values
  const formDisabled = !!nonFormError;

  // Render
  let content;
  if (formLoading) {
    content = <LinearProgress />;
  } else if (formDisabled) {
    content = (
      <Grid container spacing={3} justify="center" alignItems="center">
        <MuiAlert variant="standard" severity="error" className={classes.alert}>
          { nonFormError}
        </MuiAlert>
      </Grid>
    );
  } else {
    content = (
      <>
        {is_superuser ? (
          <Grid container spacing={3} justify="center" alignItems="center">
            <Grid item xs={3}>
              <TextField
                label="User name"
                value={username}
                onChange={(e) => onFieldChange(e, 'username')}
                error={!!formErrors.username}
                helperText={formErrors.username}
                disabled={formDisabled}
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
              />
            </Grid>
          </Grid>
        ) : ''}

        <Grid container spacing={3} justify="center" alignItems="center">
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
            <MuiPickersUtilsProvider utils={MomentUtils}>
              <DateTimePicker
                label="Instance expiry"
                ampm={false}
                disablePast
                views={['date', 'hours']}
                maxDate={maxExpiry}
                value={expiry}
                error={!!formErrors.expiry}
                helperText={formErrors.expiry}
                onChange={(e) => onDateChange(e, 'expiry')}
                disabled={formDisabled}
              />
            </MuiPickersUtilsProvider>
          </Grid>

          <Grid item xs={2}>
            <TextField
              label="Instance Name"
              value={instanceName}
              onChange={(e) => onFieldChange(e, 'instanceName')}
              error={!!formErrors.instanceName}
              helperText={formErrors.instanceName}
              disabled={formDisabled}
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
}
