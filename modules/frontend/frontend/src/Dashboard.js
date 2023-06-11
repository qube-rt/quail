import React, { useState, useEffect } from 'react';

import pick from 'lodash/pick';
import { Container, Box } from '@mui/material';
import moment from 'moment';
import { enqueueSnackbar } from 'notistack';

import appApi from './api';
import TopAppBar from './components/TopAppBar';
import InstanceForm from './components/InstanceForm';
import InstancesTable from './components/InstancesTable';
import ConfigsTable from './components/ConfigsTable';
import {
  saveConfigurations,
  getConfigurations,
  getUserData,
} from './utils';

const Dashboard = () => {
  const { username: initialUsername, email: initialEmail, is_superuser } = getUserData();

  const [state, setState] = useState({
    regionToOS: undefined,

    regions: [],
    instanceTypes: [],
    operatingSystems: [],
    expiry: undefined,
    region: undefined,
    operatingSystem: undefined,
    instanceType: undefined,
    maxExpiry: undefined,
    instanceName: '',
    username: '',
    email: '',

    currentInstances: undefined,

    formErrors: {},
    nonFormError: '',
    formLoading: true,
    provisionLoading: false,
    pollInterval: undefined,

    previousConfigs: getConfigurations(),
  });
  const updateState = (delta) => setState((oldState) => ({ ...oldState, ...delta }));

  const resetForm = () => {
    updateState({
      instanceName: '',
      email: initialEmail,
      username: initialUsername,
    });
  };

  const handleUnmount = () => {
    const { pollInterval } = state;
    clearInterval(pollInterval);
  };

  const checkForInstanceUpdates = () => {
    const { pollInterval } = state;

    // Don't do anything if the timer is already running
    if (pollInterval !== undefined) {
      return;
    }

    const interval = setInterval(async () => {
      const { data: { instances } } = await appApi.getInstances();
      const currentInstances = instances.sort(
        (a, b) => new Date(a.expiry) - new Date(b.expiry),
      );
      updateState({ currentInstances });

      if (currentInstances.filter((instance) => instance.state !== 'running').length === 0) {
        clearInterval(pollInterval);
        updateState({ pollInterval: undefined });
      }
    }, 30000);

    updateState({ pollInterval: interval });
  };

  const handleReload = () => {
    handleUnmount();

    updateState({
      regions: [],
      instanceTypes: [],
      operatingSystems: [],
      expiry: undefined,
      region: undefined,
      operatingSystem: undefined,
      instanceType: undefined,
      maxExpiry: undefined,
      instanceName: '',
      username: '',
      email: '',

      currentInstances: undefined,

      formErrors: {},
      nonFormError: '',
      formLoading: true,
      provisionLoading: false,
    });
    resetForm();

    // Fetch the params the user has permissions for
    appApi.getParams()
      .then(({ data }) => {
        const { region_map, instance_types, max_days_to_expiry } = data;

        // Create a default expiry date, 25 hours in the future
        const startTime = moment().startOf('hour');
        const expiry = moment(startTime).add(25, 'hours');
        const maxExpiry = moment(startTime).add(parseInt(max_days_to_expiry, 10), 'days');

        const selectedRegion = Object.keys(region_map)[0];
        updateState({
          regionToOS: region_map,
          regions: Object.keys(region_map),
          region: selectedRegion,
          instanceTypes: instance_types,
          instanceType: instance_types[0],
          operatingSystems: region_map[selectedRegion],
          operatingSystem: region_map[selectedRegion][0],
          expiry,
          maxExpiry,
        });

        // If any instances are in the process of being provisioned,
        // check for updates regularly
        checkForInstanceUpdates();
      })
      .catch((response) => {
        updateState({
          regions: [],
          instanceTypes: [],
          operatingSystems: [],
          maxExpiry: '',
          nonFormError: 'Could not fetch user permissions',
        });
        enqueueSnackbar(`Error fetching permissions: ${response.data.message}`, { variant: 'error' });
      })
      .then(() => {
        updateState({ formLoading: false });
      });

    appApi.getInstances()
      .then(({ data: { instances } }) => {
        updateState({
          currentInstances: instances.sort((a, b) => new Date(a.expiry) - new Date(b.expiry)),
        });
      });
  };

  const addPendingInstance = (params) => {
    updateState({
      currentInstances: [
        {
          ...pick(params, ['region', 'instanceType', 'expiry', 'email', 'username', 'instanceName']),
          operatingSystemName: params.operatingSystem,
        },
        ...state.currentInstances,
      ].sort((a, b) => new Date(a.expiry) - new Date(b.expiry)),
    });
  };

  const saveConfiguration = (params) => {
    const lastConfigs = [
      { ...params, timestamp: new Date() },
      ...state.previousConfigs,
    ].slice(0, 10);
    updateState({ previousConfigs: lastConfigs });

    saveConfigurations(lastConfigs);
  };

  const validateInstanceName = () => {
    const { instanceName } = state;

    let errorMsg = null;
    if (!instanceName) {
      errorMsg = 'Name must not be empty.';
    } else if (instanceName.length >= 255) {
      errorMsg = 'Name must not be longer than 255 characters.';
    }

    updateState(
      { formErrors: { ...state.formErrors, instanceName: errorMsg } },
    );
    return errorMsg;
  };

  const validateExpiry = () => {
    const { expiry } = state;

    let errorMsg = null;
    if (expiry < new Date()) {
      errorMsg = 'Expiry date cannot be in the past.';
    } else if (expiry < moment().add(24, 'hours')) {
      enqueueSnackbar('The expiry time is less than 24 hours ahead.', { variant: 'warning' });
    }

    updateState(
      { ...state, formErrors: { ...state.formErrors, expiry: errorMsg } },
    );
    return errorMsg;
  };

  const validatedAll = () => [
    validateExpiry(),
    validateInstanceName(),
  ];

  const handleDeleteClick = async (event, instance) => {
    updateState({
      currentInstances: state.currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { handlingDelete: true, ...item } : item),
      ),
    });

    await appApi.deleteInstance({ instanceId: instance.stackset_id });

    enqueueSnackbar('Instance submitted for deprovisioning.', { variant: 'success' });
    updateState({
      currentInstances: state.currentInstances.filter(
        (item) => item.stackset_id !== instance.stackset_id,
      ),
    });
  };

  const handleExtendClick = async (event, instance) => {
    updateState({
      currentInstances: state.currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, handlingExtend: true } : item),
      ),
    });

    try {
      const response = await appApi.extendInstance({ instanceId: instance.stackset_id });

      enqueueSnackbar('Instance extended.', { variant: 'success' });
      updateState({
        currentInstances: state.currentInstances.map(
          (item) => (item.stackset_id === instance.stackset_id
            ? { ...item, expiry: response.data.expiry, can_extend: response.data.can_extend }
            : item
          ),
        ),
      });
    } catch (response) {
      enqueueSnackbar(`Could not extend: ${response.data.message}`, { variant: 'error' });
      updateState({
        currentInstances: state.currentInstances.map(
          (item) => (item.stackset_id === instance.stackset_id
            ? { ...item, handlingExtend: false } : item),
        ),
      });
    }
  };

  const handleStartClick = async (event, instance) => {
    updateState({
      currentInstances: state.currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, handlingStart: true } : item),
      ),
    });

    try {
      await appApi.startInstance({ instanceId: instance.stackset_id });

      enqueueSnackbar('Instance started.', { variant: 'success' });
      updateState({
        currentInstances: state.currentInstances.map(
          (item) => (item.stackset_id === instance.stackset_id
            ? { ...item, state: 'pending' } : item),
        ),
      });
      checkForInstanceUpdates();
    } catch (response) {
      enqueueSnackbar(`Could not start instance: ${response.data.message}`, { variant: 'error' });
      updateState({
        currentInstances: state.currentInstances.map(
          (item) => (item.stackset_id === instance.stackset_id
            ? { ...item, handlingStart: false } : item),
        ),
      });
    }
  };

  const handleStopClick = async (event, instance) => {
    updateState({
      currentInstances: state.currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, handlingStop: true } : item),
      ),
    });

    try {
      await appApi.stopInstance({ instanceId: instance.stackset_id });

      enqueueSnackbar('Instance stopped.', { variant: 'success' });
      updateState({
        currentInstances: state.currentInstances.map(
          (item) => (item.stackset_id === instance.stackset_id
            ? { ...item, state: 'stopping' } : item),
        ),
      });
      checkForInstanceUpdates();
    } catch (response) {
      enqueueSnackbar(`Could not start instance: ${response.data.message}`, { variant: 'error' });
      updateState({
        currentInstances: state.currentInstances.map(
          (item) => (item.stackset_id === instance.stackset_id
            ? { ...item, handlingStop: false } : item),
        ),
      });
    }
  };

  const handleFieldChange = (event, fieldName) => {
    const changes = {};
    if (fieldName === 'region') {
      changes.operatingSystems = state.regionToOS[event.target.value];
    }

    updateState({
      ...changes,
      [fieldName]: event.target.value,
    });
    // TODO: check it works
    validateInstanceName();
  };

  const handleDateChange = (value, fieldName) => {
  // TODO check it works
    updateState(
      { [fieldName]: value },
    );
    validateExpiry();
  };

  const handleRestoreClick = (event, request) => {
    updateState({
      ...pick(request, ['region', 'operatingSystem', 'instanceType', 'daysToExpiry']),
    });
  };

  const handleInstanceUpdateClick = async (instance, instanceType) => {
    updateState({
      currentInstances: state.currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, state: 'updating' } : item),
      ),
    });

    try {
      await appApi.updateInstance({ instanceId: instance.stackset_id, instanceType });

      enqueueSnackbar('Instance submitted for update.', { variant: 'success' });
      updateState({
        currentInstances: state.currentInstances.map(
          (item) => (item.stackset_id === instance.stackset_id
            ? { ...item, instanceType } : item),
        ),
      });
      checkForInstanceUpdates();
    } catch (response) {
      enqueueSnackbar(`Could not update instance: ${response.data.message}`, { variant: 'error' });
    }
  };

  const handleProvisionClick = async (event) => {
    event.preventDefault();

    const formErrors = validatedAll();
    if (formErrors.filter((error) => !!error).length !== 0) {
      enqueueSnackbar('Please fix form errors before submitting.', { variant: 'error' });
      return;
    }

    updateState({ provisionLoading: true });

    const params = {
      ...pick(state, ['region', 'operatingSystem', 'instanceType', 'daysToExpiry', 'expiry', 'instanceName', 'email', 'username']),
    };
    params.expiry = params.expiry.toISOString();
    saveConfiguration(params);

    try {
      const response = await appApi.createInstance(params);

      addPendingInstance(
        { email: response.data.email, username: response.data.username, ...params },
      );
      resetForm();
      enqueueSnackbar('Instance provisioning started.', { variant: 'success' });
      checkForInstanceUpdates();
    } catch (error) {
      updateState(
        { formErrors: { ...state.formErrors, ...error.data.message } },
      );
      enqueueSnackbar('Could not provision the instance requested.', { variant: 'error' });
    } finally {
      updateState({ provisionLoading: false });
    }
  };

  useEffect(() => {
    handleReload();

    return () => handleUnmount();
  }, []);

  const {
    regions, instanceTypes, operatingSystems, expiry,
    region, instanceType, operatingSystem, maxExpiry,
    currentInstances, previousConfigs, provisionLoading,
    instanceName, formErrors, username,
    email, nonFormError, formLoading,
  } = state;

  return (
    <Container>
      <TopAppBar
        onReload={handleReload}
      />

      <Box my={6}>
        <h2>Currently running instances</h2>
        <InstancesTable
          is_superuser={is_superuser}
          instances={currentInstances}
          instanceTypes={instanceTypes}
          onDeleteClick={handleDeleteClick}
          onExtendClick={handleExtendClick}
          onStartClick={handleStartClick}
          onStopClick={handleStopClick}
          onInstanceUpdateClick={handleInstanceUpdateClick}
        />
      </Box>

      <Box my={6}>
        <h2>Provision a new instance</h2>
        <InstanceForm
          is_superuser={is_superuser}
          regions={regions}
          selectedRegion={region}
          instanceTypes={instanceTypes}
          selectedInstanceType={instanceType}
          operatingSystems={operatingSystems}
          selectedOperatingSystem={operatingSystem}
          expiry={expiry}
          maxExpiry={maxExpiry}
          instanceName={instanceName}
          username={username}
          email={email}
          onFieldChange={handleFieldChange}
          onDateChange={handleDateChange}
          onSubmit={handleProvisionClick}
          formLoading={formLoading}
          formErrors={formErrors}
          nonFormError={nonFormError}
          provisionLoading={provisionLoading}
        />
      </Box>

      <Box my={6}>
        <h2>Most recently used 10 configurations</h2>
        <ConfigsTable configs={previousConfigs} onRestoreClick={handleRestoreClick} />
      </Box>

    </Container>
  );
};

export default Dashboard;
