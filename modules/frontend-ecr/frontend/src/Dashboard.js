import React, { useState, useEffect } from 'react';

import pick from 'lodash/pick';
import { Container, Box, Typography } from '@mui/material';
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

const defaultPermissions = {
  regionMap: undefined,

  instanceTypes: [],
  maxExpiry: undefined,
};

const Dashboard = () => {
  const {
    username: initialUsername, email: initialEmail, is_superuser, groups,
  } = getUserData();

  const [state, setState] = useState({
    // Create a default expiry date, 25 hours in the future

    formErrors: {},
    nonFormError: '',
    formLoading: true,
    provisionLoading: false,
    pollInterval: undefined,

    previousConfigs: getConfigurations(),
  });
  const [currentInstances, setCurrentInstances] = useState([]);
  const updateState = (delta) => setState((oldState) => ({ ...oldState, ...delta }));

  const resetForm = () => {
    updateState({
      expiry: moment(moment().startOf('hour')).add(25, 'hours'),
      selectedRegion: undefined,
      selectedAccount: undefined,
      operatingSystem: undefined,
      instanceType: undefined,

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
      const newInstances = instances.sort(
        (a, b) => new Date(a.expiry) - new Date(b.expiry),
      );
      setCurrentInstances(newInstances);

      if (newInstances.filter((instance) => !['running', 'stopped'].includes(instance.instance_status)).length === 0) {
        clearInterval(pollInterval);
        updateState({ pollInterval: undefined });
      }
    }, 30000);

    updateState({ pollInterval: interval });
  };

  const [selectedGroup, setSelectedGroup] = useState('');
  useEffect(() => {
    if (groups.length > 0) {
      setSelectedGroup(groups[0]);
    }
    resetForm();
  }, [groups]);

  const [globalPermissions, setGlobalPermissions] = useState({});
  const [groupPermissions, setGroupPermissions] = useState(defaultPermissions);
  useEffect(() => {
    if (groups.length > 1) {
      setSelectedGroup(groups[0]);
    }
  }, [groups]);
  useEffect(() => {
    if (globalPermissions && selectedGroup) {
      setGroupPermissions(globalPermissions[selectedGroup] || defaultPermissions);
    }
  }, [globalPermissions, selectedGroup]);

  const handleReload = async () => {
    handleUnmount();

    updateState({
      selectedRegion: undefined,
      selectedAccount: undefined,
      operatingSystem: undefined,
      instanceType: undefined,
      instanceName: '',
      username: initialUsername,
      email: initialEmail,

      formErrors: {},
      nonFormError: '',
      formLoading: true,
      provisionLoading: false,
    });
    resetForm();

    // Fetch the params the user has permissions for
    appApi.getParams()
      .then(({ data }) => {
        const startTime = moment().startOf('hour');
        const groupData = Object.fromEntries(
          Object.entries(data).map(([groupName, groupConfig]) => {
            const {
              region_map, instance_types, max_days_to_expiry,
            } = groupConfig;

            const maxExpiry = moment(startTime).add(parseInt(max_days_to_expiry, 10), 'days');

            const accounts = Object.keys(region_map);
            const selectedAccount = accounts[0];
            const regions = Object.keys(region_map[selectedAccount]);
            const selectedRegion = regions[0];

            return [groupName, {
              regionMap: region_map,
              instanceTypes: instance_types,
              instanceType: instance_types[0],
              operatingSystems: region_map[selectedAccount][selectedRegion],
              operatingSystem: region_map[selectedAccount][selectedRegion][0],
              maxExpiry,
            }];
          }),
        );

        setGlobalPermissions(groupData);

        // If any instances are in the process of being provisioned,
        // check for updates regularly
        checkForInstanceUpdates();
      })
      .catch((response) => {
        updateState({
          nonFormError: 'Could not fetch user permissions',
        });
        enqueueSnackbar(`Error fetching permissions: ${response.message}`, { variant: 'error' });
      })
      .then(() => {
        updateState({ formLoading: false });
      });

    appApi.getInstances()
      .then(({ data: { instances } }) => {
        setCurrentInstances(instances.sort((a, b) => new Date(a.expiry) - new Date(b.expiry)));
      });
  };

  const addPendingInstance = (params) => {
    setCurrentInstances([
      {
        ...pick(params, [
          'stackset_id', 'region', 'expiry', 'email', 'username', 'group',
        ]),
        account: params.account_id,
        instance_type: params.instanceType,
        instance_name: params.instanceName,
        operating_system: params.operatingSystem,
      },
      ...currentInstances,
    ].sort((a, b) => new Date(a.expiry) - new Date(b.expiry)));
  };

  const saveConfiguration = (params) => {
    const lastConfigs = [
      { ...params, timestamp: new Date() },
      ...state.previousConfigs,
    ].slice(0, 10);
    updateState({ previousConfigs: lastConfigs });

    saveConfigurations(lastConfigs);
  };

  const validateInstanceName = (instanceName) => {
    let errorMsg = null;
    const validUrlRegex = /^([a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])*$/i;
    if (!instanceName) {
      errorMsg = 'Name must not be empty.';
    } else if (instanceName.length >= 255) {
      errorMsg = 'Name must not be longer than 255 characters.';
    } else if (!validUrlRegex.test(instanceName)) {
      errorMsg = 'Name must only contain alphanumeric or dash characters.';
    }

    updateState(
      { formErrors: { ...state.formErrors, instanceName: errorMsg } },
    );
    return errorMsg;
  };

  const validateExpiry = (expiry) => {
    let errorMsg = null;
    if (expiry < new Date()) {
      errorMsg = 'Expiry date cannot be in the past.';
    } else if (expiry < moment().add(24, 'hours')) {
      enqueueSnackbar('The expiry time is less than 24 hours ahead.', { variant: 'warning' });
    }

    updateState(
      { formErrors: { ...state.formErrors, expiry: errorMsg } },
    );
    return errorMsg;
  };

  const validatedAll = () => [
    validateExpiry(state.expiry),
    validateInstanceName(state.instanceName),
  ];

  const handleDeleteClick = async (instance) => {
    setCurrentInstances(currentInstances.map(
      (item) => (item.stackset_id === instance.stackset_id
        ? { handlingDelete: true, ...item } : item),
    ));

    try {
      await appApi.deleteInstance({ instanceId: instance.stackset_id });
      setCurrentInstances(currentInstances.filter(
        (item) => item.stackset_id !== instance.stackset_id,
      ));

      enqueueSnackbar('Instance submitted for deprovisioning.', { variant: 'success' });
    } catch (response) {
      enqueueSnackbar(`Could not delete: ${response.response.data.error || response.message}`, { variant: 'error' });
    }
  };

  const handleExtendClick = async (instance) => {
    setCurrentInstances(currentInstances.map(
      (item) => (item.stackset_id === instance.stackset_id
        ? { ...item, handlingExtend: true } : item),
    ));

    try {
      const response = await appApi.extendInstance({ instanceId: instance.stackset_id });

      enqueueSnackbar('Instance extended.', { variant: 'success' });
      setCurrentInstances(currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? {
            ...item,
            expiry: response.data.expiry,
            can_extend: response.data.can_extend,
            handlingExtend: false,
          }
          : item
        ),
      ));
    } catch (response) {
      enqueueSnackbar(`Could not extend: ${response.response.data.error || response.message}`, { variant: 'error' });
      setCurrentInstances(currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, handlingExtend: false } : item),
      ));
    }
  };

  const handleStartClick = async (instance) => {
    setCurrentInstances(currentInstances.map(
      (item) => (item.stackset_id === instance.stackset_id
        ? { ...item, handlingStart: true } : item),
    ));

    try {
      await appApi.startInstance({ instanceId: instance.stackset_id });

      enqueueSnackbar('Instance started.', { variant: 'success' });
      setCurrentInstances(currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, instance_status: 'pending', handlingStart: true } : item),
      ));
      checkForInstanceUpdates();
    } catch (response) {
      enqueueSnackbar(`Could not start instance: ${response.response.data.error || response.message}`, { variant: 'error' });
      setCurrentInstances(currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, handlingStart: false } : item),
      ));
    }
  };

  const handleStopClick = async (instance) => {
    setCurrentInstances(currentInstances.map(
      (item) => (item.stackset_id === instance.stackset_id
        ? { ...item, handlingStop: true } : item),
    ));

    try {
      await appApi.stopInstance({ instanceId: instance.stackset_id });

      enqueueSnackbar('Instance stopped.', { variant: 'success' });
      setCurrentInstances(currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, instance_status: 'stopping', handlingStop: true } : item),
      ));
      checkForInstanceUpdates();
    } catch (response) {
      enqueueSnackbar(`Could not stop instance: ${response.response.data.error || response.message}`, { variant: 'error' });
      setCurrentInstances(currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, handlingStop: false } : item),
      ));
    }
  };

  const handleFieldChange = (event, fieldName) => {
    let changes = { [fieldName]: event.target.value };

    if (fieldName === 'selectedAccount') {
      const targetAccount = event.target.value;
      const regions = Object.keys(groupPermissions.regionMap[targetAccount]);
      const selectedRegion = regions[0];
      const operatingSystems = groupPermissions.regionMap[targetAccount][selectedRegion];
      changes = {
        selectedRegion,
        operatingSystems,
        operatingSystem: operatingSystems[0],
        ...changes,
      };
    }

    if (fieldName === 'selectedRegion') {
      const operatingSystems = groupPermissions
        .regionMap[state.selectedAccount][event.target.value];
      changes = {
        operatingSystems,
        operatingSystem: operatingSystems[0],
        ...changes,
      };
    }

    updateState({
      ...changes,
    });
    validateInstanceName(fieldName === 'instanceName' ? event.target.value : state.instanceName);
  };

  const handleDateChange = (value, fieldName) => {
    updateState(
      { [fieldName]: value },
    );
    validateExpiry(value);
  };

  const handleRestoreClick = (request) => {
    const pastRequest = {
      selectedAccount: request.account,
      selectedRegion: request.region,
      ...pick(request, ['operatingSystem', 'instanceType']),
    };
    updateState({
      ...pastRequest,
    });
  };

  const handleInstanceUpdateClick = async (instance, instanceType) => {
    setCurrentInstances(currentInstances.map(
      (item) => (item.stackset_id === instance.stackset_id
        ? { ...item, instance_status: 'updating' } : item),
    ));

    try {
      await appApi.updateInstance({ instanceId: instance.stackset_id, instanceType });

      enqueueSnackbar('Instance submitted for update.', { variant: 'success' });
      setCurrentInstances(currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, instanceType, instance_status: 'updating' } : item),
      ));
      checkForInstanceUpdates();
    } catch (response) {
      enqueueSnackbar(`Could not update instance: ${response.response.data.error || response.message}`, { variant: 'error' });
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
      ...pick(state, ['operatingSystem', 'instanceType', 'daysToExpiry', 'expiry', 'instanceName', 'email', 'username']),
    };
    params.expiry = params.expiry.toISOString();
    params.account = state.selectedAccount;
    params.region = state.selectedRegion;
    params.group = selectedGroup;
    saveConfiguration(params);

    try {
      const response = await appApi.createInstance(params);

      addPendingInstance(
        {
          stackset_id: Date.now(),
          email: response.data.email,
          username: response.data.username,
          account_id: params.account,
          ...params,
        },
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
    expiry,
    selectedRegion, instanceType, operatingSystem,
    previousConfigs, provisionLoading,
    instanceName, formErrors, username,
    email, nonFormError, formLoading, selectedAccount,
  } = state;

  return (
    <Container>
      <TopAppBar
        onReload={handleReload}
        selectedGroup={selectedGroup}
        setSelectedGroup={setSelectedGroup}
      />

      <Box my={6}>
        <Typography variant="h5">Currently running instances</Typography>
        <InstancesTable
          is_superuser={is_superuser}
          instances={currentInstances}
          onDeleteClick={handleDeleteClick}
          onExtendClick={handleExtendClick}
          onStartClick={handleStartClick}
          onStopClick={handleStopClick}
          onInstanceUpdateClick={handleInstanceUpdateClick}
        />
      </Box>

      <Box my={6}>
        <Typography variant="h5" mb={3}>Provision a new instance</Typography>
        <InstanceForm
          is_superuser={is_superuser}
          regionMap={groupPermissions.regionMap}
          selectedRegion={selectedRegion}
          selectedAccount={selectedAccount}
          selectedInstanceType={instanceType}
          instanceTypes={groupPermissions.instanceTypes}
          selectedOperatingSystem={operatingSystem}
          expiry={expiry}
          maxExpiry={groupPermissions.maxExpiry}
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
        <Typography variant="h5">Most recently used 10 configurations</Typography>
        <ConfigsTable configs={previousConfigs} onRestoreClick={handleRestoreClick} />
      </Box>

    </Container>
  );
};

export default Dashboard;
