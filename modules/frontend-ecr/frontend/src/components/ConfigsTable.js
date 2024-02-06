import React from 'react';

import { makeStyles } from '@mui/styles';
import { Restore as RestoreIcon } from '@mui/icons-material';
import {
  Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton,
} from '@mui/material';

import { formatDate, getLabel } from '../utils';

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
    cursor: 'pointer',
  },
}));

export default function ConfigsTable(props) {
  const classes = useStyles();
  const { configs, onRestoreClick, userGroups } = props;

  const availableConfigs = configs.filter((config) => userGroups.includes(config.group))
    .slice(0, 10);

  return (
    <TableContainer component={Paper}>
      <Table className={classes.table} size="small">
        <TableHead>
          <TableRow>
            <TableCell className={classes.tableHeaderCell}>Account</TableCell>
            <TableCell className={classes.tableHeaderCell}>Region</TableCell>
            <TableCell className={classes.tableHeaderCell}>Group</TableCell>
            <TableCell className={classes.tableHeaderCell}>Instance Type</TableCell>
            <TableCell className={classes.tableHeaderCell}>Operating System</TableCell>
            <TableCell className={classes.tableHeaderCell}>Expires at</TableCell>
            <TableCell className={classes.tableHeaderCell} />
          </TableRow>
        </TableHead>
        <TableBody>
          {availableConfigs.map((config, index) => (
            <TableRow
              key={index}
              className={classes.tableRow}
              onClick={() => onRestoreClick(config)}
            >
              <TableCell className={classes.tableCell}>
                { getLabel('accountLabels', config.account) }
              </TableCell>
              <TableCell className={classes.tableCell}>
                { getLabel('regionLabels', config.region) }
              </TableCell>
              <TableCell className={classes.tableCell}>
                { getLabel('groupLabels', config.group) }
              </TableCell>
              <TableCell className={classes.tableCell}>
                { getLabel('instanceLabels', config.instanceType) }
              </TableCell>
              <TableCell className={classes.tableCell}>{config.operatingSystem}</TableCell>
              <TableCell className={classes.tableCell}>{formatDate(config.expiry)}</TableCell>
              <TableCell className={classes.tableCell} align="center">
                <IconButton
                  variant="contained"
                  color="primary"
                  className={classes.button}
                  onClick={() => onRestoreClick(config)}
                >
                  <RestoreIcon fontSize="inherit" />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
