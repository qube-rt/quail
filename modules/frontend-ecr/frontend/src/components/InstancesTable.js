import React from 'react';

import { makeStyles } from '@mui/styles';
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  CircularProgress,
  Tooltip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from '@mui/material';
import { enqueueSnackbar } from 'notistack';

import DebouncedButton from './DebouncedButton';
import SelectField from './SelectField';
import { getLabel, formatDate, getUserData } from '../utils';
import labels from '../labels';

const useStyles = makeStyles((theme) => ({
  table: {
    minWidth: 650,
  },
  tableHeaderCell: {
    backgroundColor: theme.palette.grey[400],
    color: theme.palette.common.black,
  },
  tableRow: {
    '&:nth-of-type(odd)': {
      backgroundColor: theme.palette.action.hover,
    },
  },
  buttonWrapper: {
    display: 'flex',
    alignItems: 'center',
  },
  button: {
    margin: theme.spacing(0.25),
  },
}));

export default function InstancesTable(props) {
  const classes = useStyles();
  const {
    is_superuser, instances, instanceTypes, onDeleteClick,
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
    if (instance.connectionProtocol === 'ssh') {
      copySSHCommandToClipboard(instance.private_ip);
    } else {
      downloadRDPFile(instance.private_ip);
    }
  };

  const [open, setOpen] = React.useState(false);
  const [dialogData, setDialogData] = React.useState({ instance: null, instanceType: '' });

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
        <Table className={classes.table} size="small">
          <TableHead>
            <TableRow>
              { is_superuser ? (
                <>
                  <TableCell className={classes.tableHeaderCell}>Owner</TableCell>
                </>
              ) : <></> }
              <TableCell className={classes.tableHeaderCell}>Account</TableCell>
              <TableCell className={classes.tableHeaderCell}>Region</TableCell>
              <TableCell className={classes.tableHeaderCell}>Instance Type</TableCell>
              <TableCell className={classes.tableHeaderCell}>Operating System</TableCell>
              <TableCell className={classes.tableHeaderCell}>IP</TableCell>
              <TableCell className={classes.tableHeaderCell}>Name</TableCell>
              <TableCell className={classes.tableHeaderCell}>Status</TableCell>
              <TableCell className={classes.tableHeaderCell}>Expires at</TableCell>
              <TableCell className={classes.tableHeaderCell} />
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? <></> : instances.map((instance, index) => (
              <TableRow className={classes.tableRow} key={index}>
                { is_superuser ? (
                  <>
                    <TableCell className={classes.tableCell}>
                      <Tooltip
                        title={instance.email}
                        PopperProps={{ keepMounted: true }}
                      >
                        <div>{instance.username}</div>
                      </Tooltip>
                    </TableCell>
                  </>
                ) : <></> }
                <TableCell className={classes.tableCell}>{instance.account_id}</TableCell>
                <TableCell className={classes.tableCell}>
                  { getLabel('regions', instance.region) }
                </TableCell>
                <TableCell className={classes.tableCell}>
                  <SelectField
                    fieldName="instanceType"
                    values={instanceTypes}
                    valueLabels={labels.instanceTypes}
                    selected={instance.instanceType}
                    disabled={instance.state !== 'running' && instance.state !== 'stopped'}
                    onFieldChange={(event) => handleClickOpen(instance, event.target.value)}
                  />
                </TableCell>
                <TableCell className={classes.tableCell}>{instance.operatingSystemName}</TableCell>
                <TableCell className={classes.tableCell}>{instance.private_ip}</TableCell>
                <TableCell className={classes.tableCell}>{instance.instanceName}</TableCell>
                <TableCell className={classes.tableCell}>
                  {
                  instance.state === 'stopped' || instance.state === 'running'
                    ? instance.state : <CircularProgress />
                }
                </TableCell>
                <TableCell className={classes.tableCell}>{formatDate(instance.expiry)}</TableCell>
                <TableCell className={classes.tableCell}>
                  <div className={classes.buttonWrapper}>
                    { instance.state === 'running' ? (
                      <>
                        <Button
                          variant="contained"
                          color="primary"
                          className={classes.button}
                          startIcon={<CloudUploadIcon />}
                          onClick={() => handleConnectClick(instance)}
                        >
                          Connect
                        </Button>
                        <DebouncedButton
                          variant="contained"
                          color="primary"
                          engaged={!!instance.handlingStop}
                          startIcon={<PauseCircleOutlineIcon />}
                          onClick={(e) => onStopClick(e, instance)}
                        >
                          Stop
                        </DebouncedButton>
                      </>
                    ) : ''}

                    { instance.state === 'stopped' ? (
                      <DebouncedButton
                        variant="contained"
                        color="secondary"
                        engaged={!!instance.handlingStart}
                        startIcon={<PlayCircleOutlineIcon />}
                        onClick={(e) => onStartClick(e, instance)}
                      >
                        Start
                      </DebouncedButton>
                    ) : ''}

                    { instance.state === 'stopped' || instance.state === 'running' ? (
                      <>
                        <DebouncedButton
                          variant="contained"
                          color="primary"
                          engaged={!!instance.handlingExtend}
                          disabled={!instance.can_extend}
                          startIcon={<SnoozeIcon />}
                          onClick={(e) => onExtendClick(e, instance)}
                        >
                          Extend
                        </DebouncedButton>
                        <DebouncedButton
                          variant="contained"
                          color="secondary"
                          engaged={!!instance.handlingDelete}
                          startIcon={<DeleteIcon />}
                          onClick={(e) => onDeleteClick(e, instance)}
                        >
                          Delete
                        </DebouncedButton>
                      </>
                    ) : ''}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {isLoading ? <LinearProgress /> : '' }
      </TableContainer>
    </>
  );
}
