import React, { useState } from 'react';

import {
  Delete as DeleteIcon,
  PauseCircleOutline as PauseCircleOutlineIcon,
  PlayCircleOutline as PlayCircleOutlineIcon,
  CloudUpload as CloudUploadIcon,
  Snooze as SnoozeIcon,
} from '@mui/icons-material';
import {
  Button,
  Paper,
  TableContainer,
  LinearProgress,
  CircularProgress,
  Tooltip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';
import { DataGrid, GridActionsCellItem, GridToolbar } from '@mui/x-data-grid';
import { enqueueSnackbar } from 'notistack';

import { debounce } from 'lodash';
import SelectField from './SelectField';
import { formatDate, getLabel, getUserData } from '../utils';
import Config from '../config';

const GridActionsCellItemWrapper = (params) => {
  const {
    icon, label, color, onClick, disabled,
  } = params;

  const debouncedHandler = debounce(onClick, 500, { leading: true });

  return (
    <GridActionsCellItem
      icon={<Tooltip title={label}>{icon}</Tooltip>}
      label={label}
      color={color}
      disabled={disabled}
      onClick={debouncedHandler}
    />
  );
};

export default function InstancesTable(props) {
  const {
    is_superuser, instances, onDeleteClick,
    onExtendClick, onStartClick, onStopClick, onInstanceUpdateClick,
  } = props;
  const { username } = getUserData();

  // Calculated values
  const isLoading = instances === undefined;

  // Event handling functions
  const downloadRDPFile = (instance_address) => {
    const fileBody = [
      'auto connect:i:1\n',
      `full address:s:${instance_address}\n`,
      `username:s:${username}\n`,
    ];
    const element = document.createElement('a');
    const file = new Blob(fileBody,
      { type: 'text/plain;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = `connect-${instance_address}.rdp`;
    document.body.appendChild(element);
    element.click();
  };

  function copySSHCommandToClipboard(ipAddress) {
    navigator.clipboard.writeText(`ssh ${username}@${ipAddress}`);
    enqueueSnackbar('Connection command copied to clipboard.', { variant: 'success' });
  }

  const handleConnectClick = (instance) => {
    if (instance.connection_protocol === 'ssh') {
      copySSHCommandToClipboard(instance.private_ip);
    } else {
      downloadRDPFile(instance.private_ip);
    }
  };

  const [open, setOpen] = useState(false);
  const [dialogData, setDialogData] = useState({ instance: null, instanceType: '' });

  const handleClickOpen = (instance, instanceType) => {
    setDialogData({ instance, instanceType });
    setOpen(true);
  };

  const handleClose = () => {
    setDialogData({ instance: null, instanceType: '' });
    setOpen(false);
  };

  const handleAccept = () => {
    onInstanceUpdateClick(dialogData.instance, dialogData.instanceType);
    handleClose();
  };

  const columns = [
    ...(is_superuser ? [{ field: 'username', headerName: 'Owner' }] : []),
    {
      field: 'account',
      headerName: 'Account',
      valueFormatter: ({ value: account_id }) => getLabel('accountLabels', account_id),
    },
    {
      field: 'region',
      headerName: 'Region',
      minWidth: 150,
      valueFormatter: ({ value: region }) => getLabel('regionLabels', region),
    },
    {
      field: 'group',
      headerName: 'Group',
      minWidth: 100,
      valueFormatter: ({ value: group }) => getLabel('groupLabels', group),
    },
    {
      field: 'instance_type',
      headerName: 'Instance Type',
      minWidth: 220,
      flex: 1,
      renderCell: ({ row: instance, value }) => (
        <SelectField
          fieldName="instanceType"
          values={instance.available_instance_types}
          valueLabels={Config.instanceLabels}
          selected={value}
          disabled={instance.instance_status !== 'running' && instance.instance_status !== 'stopped'}
          onFieldChange={(event) => handleClickOpen(instance, event.target.value)}
        />
      ),
    },
    { field: 'operating_system', headerName: 'Operating System', width: 150 },
    {
      field: 'private_ip', headerName: 'IP', width: 130,
    },
    { field: 'instance_name', headerName: 'Name' },
    {
      field: 'instance_status', headerName: 'Status', renderCell: ({ value }) => (['stopped', 'running'].includes(value) ? value : <CircularProgress />), width: 80,
    },
    {
      field: 'expiry', headerName: 'Expires At', minWidth: 150, valueFormatter: ({ value: expiry }) => formatDate(expiry),
    },
    {
      field: 'actions',
      type: 'actions',
      minWidth: 160,
      flex: 0.6,
      getActions: ({ row }) => [
        ...(row.instance_status === 'running' ? [
          <GridActionsCellItemWrapper
            icon={<CloudUploadIcon />}
            label="Connect"
            color="info"
            onClick={() => handleConnectClick(row)}
          />,
          <GridActionsCellItemWrapper
            icon={<PauseCircleOutlineIcon />}
            label="Stop"
            color="secondary"
            disabled={!!row.handlingStop}
            onClick={() => onStopClick(row)}
          />] : []),
        ...(row.instance_status === 'stopped' ? [
          <GridActionsCellItemWrapper
            icon={<PlayCircleOutlineIcon />}
            label="Start"
            color="primary"
            disabled={!!row.handlingStart}
            onClick={() => onStartClick(row)}
          />] : []),
        ...(['stopped', 'running'].includes(row.instance_status) ? [
          <GridActionsCellItemWrapper
            icon={<SnoozeIcon />}
            label="Extend"
            color="primary"
            disabled={!row.can_extend || !!row.handlingExtend}
            onClick={() => onExtendClick(row)}
          />,
          <GridActionsCellItemWrapper
            icon={<DeleteIcon />}
            label="Delete"
            color="error"
            disabled={!!row.handlingDelete}
            onClick={() => onDeleteClick(row)}
          />] : []),
      ],
    },
  ];

  return (
    <>
      <Dialog
        open={open}
        onClose={handleClose}
      >
        <DialogTitle id="alert-dialog-title">Update instance type?</DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            Updating the instance type will cause the instance to be temporary removed
            from service, terminating any operations running on the instance and reseting
            all connections.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} color="primary">
            Cancel
          </Button>
          <Button onClick={handleAccept} color="primary" autoFocus>
            Confirm
          </Button>
        </DialogActions>
      </Dialog>

      <TableContainer component={Paper}>
        <DataGrid
          rows={instances || []}
          columns={columns}
          slots={{ toolbar: GridToolbar }}
          getRowId={(instance) => instance.stackset_id}
          rowModesModel={{}}
          disableRowSelectionOnClick
          disableColumnSelector
          disableDensitySelector
          // disableColumnFilter
          slotProps={{
            toolbar: {
              csvOptions: { disableToolbarButton: true },
              printOptions: { disableToolbarButton: true },
              showQuickFilter: true,
              quickFilterProps: { debounceMs: 500 },
            },
          }}
          initialState={{
            pagination: { paginationModel: { pageSize: 10 } },
          }}
          pageSizeOptions={[10, 25, 50]}
        />
        {isLoading ? <LinearProgress /> : '' }
      </TableContainer>

    </>
  );
}
