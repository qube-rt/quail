import React from 'react';

import pick from 'lodash/pick';
import { Container, Box } from '@mui/material';
import moment from 'moment';
import { withSnackbar } from 'notistack';

import appApi from './api';
import TopAppBar from './components/TopAppBar';
import InstanceForm from './components/InstanceForm';
import InstancesTable from './components/InstancesTable';
import ConfigsTable from './components/ConfigsTable';
import {
  saveConfigurations,
  getConfigurations,
  handleLogout,
  getSuperuserFlagFromJWT,
  getEmailFromJWT,
  getUsernameFromJWT,
} from './utils';

class Dashboard extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      regionToOS: undefined,

      regions: undefined,
      instanceTypes: undefined,
      operatingSystems: undefined,
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

      is_superuser: getSuperuserFlagFromJWT(),

      previousConfigs: getConfigurations(),
    };

    this.handleDateChange = this.handleDateChange.bind(this);
    this.handleFieldChange = this.handleFieldChange.bind(this);
    this.handleProvisionClick = this.handleProvisionClick.bind(this);
    this.handleReload = this.handleReload.bind(this);

    this.handleExtendClick = this.handleExtendClick.bind(this);
    this.handleStopClick = this.handleStopClick.bind(this);
    this.handleStartClick = this.handleStartClick.bind(this);
    this.handleRestoreClick = this.handleRestoreClick.bind(this);
    this.handleDeleteClick = this.handleDeleteClick.bind(this);
    this.handleInstanceUpdateClick = this.handleInstanceUpdateClick.bind(this);
  }

  componentDidMount() {
    this.handleReload();
  }

  componentWillUnmount() {
    this.handleUnmount();
  }

  handleUnmount() {
    const { pollInterval } = this.state;
    clearInterval(pollInterval);
  }

  handleReload() {
    this.handleUnmount();
    const { enqueueSnackbar } = this.props;

    this.setState({
      regions: undefined,
      instanceTypes: undefined,
      operatingSystems: undefined,
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
    this.resetForm();

    // Fetch the params the user has permissions for
    appApi.getParams()
      .then(({ data }) => {
        const { region_map, instance_types, max_days_to_expiry } = data;

        // Create a default expiry date, 25 hours in the future
        const startTime = moment().startOf('hour');
        const expiry = moment(startTime).add(25, 'hours');
        const maxExpiry = moment(startTime).add(parseInt(max_days_to_expiry, 10), 'days');

        const selectedRegion = Object.keys(region_map)[0];
        this.setState({
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
        this.checkForInstanceUpdates();
      })
      .catch((response) => {
        this.setState({
          regions: [],
          instanceTypes: [],
          operatingSystems: [],
          maxExpiry: '',
          nonFormError: 'Could not fetch user permissions',
        });
        enqueueSnackbar(`Error fetching permissions: ${response.data.message}`, { variant: 'error' });
      })
      .then(() => {
        this.setState({ formLoading: false });
      });

    appApi.getInstances()
      .then(({ data: { instances } }) => {
        this.setState({
          currentInstances: instances.sort((a, b) => new Date(a.expiry) - new Date(b.expiry)),
        });
      });
  }

  handleDeleteClick(event, instance) {
    const { enqueueSnackbar } = this.props;
    this.setState((state) => ({
      currentInstances: state.currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { handlingDelete: true, ...item } : item),
      ),
    }));

    appApi.deleteInstance({ instanceId: instance.stackset_id })
      .then(() => {
        enqueueSnackbar('Instance submitted for deprovisioning.', { variant: 'success' });
        this.setState((state) => ({
          currentInstances: state.currentInstances.filter(
            (item) => item.stackset_id !== instance.stackset_id,
          ),
        }));
      });
  }

  handleExtendClick(event, instance) {
    const { enqueueSnackbar } = this.props;
    this.setState((state) => ({
      currentInstances: state.currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, handlingExtend: true } : item),
      ),
    }));

    appApi.extendInstance({ instanceId: instance.stackset_id })
      .then((response) => {
        enqueueSnackbar('Instance extended.', { variant: 'success' });
        this.setState((state) => ({
          currentInstances: state.currentInstances.map(
            (item) => (item.stackset_id === instance.stackset_id
              ? { ...item, expiry: response.data.expiry, can_extend: response.data.can_extend }
              : item
            ),
          ),
        }));
      })
      .catch((response) => {
        enqueueSnackbar(`Could not extend: ${response.data.message}`, { variant: 'error' });
      })
      .then(() => this.setState((state) => ({
        currentInstances: state.currentInstances.map(
          (item) => (item.stackset_id === instance.stackset_id
            ? { ...item, handlingExtend: false } : item),
        ),
      })));
  }

  handleStartClick(event, instance) {
    const { enqueueSnackbar } = this.props;
    this.setState((state) => ({
      currentInstances: state.currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, handlingStart: true } : item),
      ),
    }));

    appApi.startInstance({ instanceId: instance.stackset_id })
      .then(() => {
        enqueueSnackbar('Instance started.', { variant: 'success' });
        this.setState((state) => ({
          currentInstances: state.currentInstances.map(
            (item) => (item.stackset_id === instance.stackset_id
              ? { ...item, state: 'pending' } : item),
          ),
        }));
        this.checkForInstanceUpdates();
      })
      .catch((response) => {
        enqueueSnackbar(`Could not start instance: ${response.data.message}`, { variant: 'error' });
      })
      .then(() => this.setState((state) => ({
        currentInstances: state.currentInstances.map(
          (item) => (item.stackset_id === instance.stackset_id
            ? { ...item, handlingStart: false } : item),
        ),
      })));
  }

  handleStopClick(event, instance) {
    const { enqueueSnackbar } = this.props;
    this.setState((state) => ({
      currentInstances: state.currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, handlingStop: true } : item),
      ),
    }));

    appApi.stopInstance({ instanceId: instance.stackset_id })
      .then(() => {
        enqueueSnackbar('Instance stopped.', { variant: 'success' });
        this.setState((state) => ({
          currentInstances: state.currentInstances.map(
            (item) => (item.stackset_id === instance.stackset_id
              ? { ...item, state: 'stopping' } : item),
          ),
        }));
        this.checkForInstanceUpdates();
      })
      .catch((response) => {
        enqueueSnackbar(`Could not start instance: ${response.data.message}`, { variant: 'error' });
      })
      .then(() => this.setState((state) => ({
        currentInstances: state.currentInstances.map(
          (item) => (item.stackset_id === instance.stackset_id
            ? { ...item, handlingStop: false } : item),
        ),
      })));
  }

  handleFieldChange(event, fieldName) {
    if (fieldName === 'region') {
      this.setState((state) => ({ operatingSystems: state.regionToOS[event.target.value] }));
    }

    this.setState(
      { [fieldName]: event.target.value },
      () => (fieldName === 'instanceName' ? this.validateInstanceName() : undefined),
    );
  }

  handleDateChange(value, fieldName) {
    this.setState(
      { [fieldName]: value },
      this.validateExpiry,
    );
  }

  handleRestoreClick(event, request) {
    this.setState({
      ...pick(request, ['region', 'operatingSystem', 'instanceType', 'daysToExpiry']),
    });
  }

  handleInstanceUpdateClick(instance, instanceType) {
    const { enqueueSnackbar } = this.props;

    this.setState((state) => ({
      currentInstances: state.currentInstances.map(
        (item) => (item.stackset_id === instance.stackset_id
          ? { ...item, state: 'updating' } : item),
      ),
    }));
    appApi.updateInstance({ instanceId: instance.stackset_id, instanceType })
      .then(() => {
        enqueueSnackbar('Instance submitted for update.', { variant: 'success' });
        this.setState((state) => ({
          currentInstances: state.currentInstances.map(
            (item) => (item.stackset_id === instance.stackset_id
              ? { ...item, instanceType } : item),
          ),
        }));
        this.checkForInstanceUpdates();
      })
      .catch((response) => {
        enqueueSnackbar(`Could not update instance: ${response.data.message}`, { variant: 'error' });
      });
  }

  handleProvisionClick(event) {
    event.preventDefault();
    const { enqueueSnackbar } = this.props;

    const formErrors = this.validatedAll();
    if (formErrors.filter((error) => !!error).length !== 0) {
      enqueueSnackbar('Please fix form errors before submitting.', { variant: 'error' });
      return;
    }

    this.setState({ provisionLoading: true });

    const params = {
      ...pick(this.state, ['region', 'operatingSystem', 'instanceType', 'daysToExpiry', 'expiry', 'instanceName', 'email', 'username']),
    };
    params.expiry = params.expiry.toISOString();
    this.saveConfiguration(params);

    appApi.createInstance(params)
      .then((response) => {
        this.addPendingInstance(
          { email: response.data.email, username: response.data.username, ...params },
        );
        this.resetForm();
        enqueueSnackbar('Instance provisioning started.', { variant: 'success' });
        this.checkForInstanceUpdates();
      })
      .catch((response) => {
        this.setState((state) => (
          { formErrors: { ...state.formErrors, ...response.data.message } }));
        enqueueSnackbar('Could not provision the instance requested.', { variant: 'error' });
      })
      .then(() => this.setState({ provisionLoading: false }));
  }

  validateInstanceName() {
    const { instanceName } = this.state;

    let errorMsg = null;
    if (!instanceName) {
      errorMsg = 'Name must not be empty.';
    } else if (instanceName.length >= 255) {
      errorMsg = 'Name must not be longer than 255 characters.';
    }

    this.setState((state) => (
      { formErrors: { ...state.formErrors, instanceName: errorMsg } }));
    return errorMsg;
  }

  validateExpiry() {
    const { expiry } = this.state;
    const { enqueueSnackbar } = this.props;

    let errorMsg = null;
    if (expiry < new Date()) {
      errorMsg = 'Expiry date cannot be in the past.';
    } else if (expiry < moment().add(24, 'hours')) {
      enqueueSnackbar('The expiry time is less than 24 hours ahead.', { variant: 'warning' });
    }

    this.setState((state) => (
      { formErrors: { ...state.formErrors, expiry: errorMsg } }));
    return errorMsg;
  }

  validatedAll() {
    return [
      this.validateExpiry(),
      this.validateInstanceName(),
    ];
  }

  checkForInstanceUpdates() {
    const { pollInterval } = this.state;

    // Don't do anything if the timer is already running
    if (pollInterval !== undefined) {
      return;
    }

    const interval = setInterval(() => {
      appApi.getInstances()
        .then(({ data: { instances } }) => {
          const currentInstances = instances.sort(
            (a, b) => new Date(a.expiry) - new Date(b.expiry),
          );
          this.setState({ currentInstances });
          // If all instannces are ready, stop checking for updates
          if (currentInstances.filter((instance) => instance.state !== 'running').length === 0) {
            // eslint-disable-next-line no-shadow
            const { pollInterval } = this.state;
            clearInterval(pollInterval);
            this.setState({ pollInterval: undefined });
          }
        });
    }, 30000);
    this.setState({ pollInterval: interval });
  }

  resetForm() {
    this.setState({ instanceName: '', email: getEmailFromJWT(), username: getUsernameFromJWT() });
  }

  addPendingInstance(params) {
    this.setState((state) => ({
      currentInstances: [
        {
          ...pick(params, ['region', 'instanceType', 'expiry', 'email', 'username', 'instanceName']),
          operatingSystemName: params.operatingSystem,
        },
        ...state.currentInstances,
      ].sort((a, b) => new Date(a.expiry) - new Date(b.expiry)),
    }));
  }

  saveConfiguration(params) {
    this.setState((state) => ({
      previousConfigs: [
        { ...params, timestamp: new Date() },
        ...state.previousConfigs,
      ].slice(0, 10),
    // eslint-disable-next-line react/destructuring-assignment
    }), () => saveConfigurations(this.state.previousConfigs));
  }

  render() {
    const {
      regions, instanceTypes, operatingSystems, expiry,
      region, instanceType, operatingSystem, maxExpiry,
      currentInstances, previousConfigs, provisionLoading,
      instanceName, formErrors, is_superuser, username,
      email, nonFormError, formLoading,
    } = this.state;

    return (
      <Container>
        <TopAppBar
          onLogout={handleLogout}
          onReload={this.handleReload}
        />

        <Box my={6}>
          <h2>Currently running instances</h2>
          <InstancesTable
            is_superuser={is_superuser}
            instances={currentInstances}
            instanceTypes={instanceTypes}
            onDeleteClick={this.handleDeleteClick}
            onExtendClick={this.handleExtendClick}
            onStartClick={this.handleStartClick}
            onStopClick={this.handleStopClick}
            onInstanceUpdateClick={this.handleInstanceUpdateClick}
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
            onFieldChange={this.handleFieldChange}
            onDateChange={this.handleDateChange}
            onSubmit={this.handleProvisionClick}
            formLoading={formLoading}
            formErrors={formErrors}
            nonFormError={nonFormError}
            provisionLoading={provisionLoading}
          />
        </Box>

        <Box my={6}>
          <h2>Most recently used 10 configurations</h2>
          <ConfigsTable configs={previousConfigs} onRestoreClick={this.handleRestoreClick} />
        </Box>

      </Container>
    );
  }
}

export default withSnackbar(Dashboard);
