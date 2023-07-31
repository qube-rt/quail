import React from 'react';

import { makeStyles } from '@mui/styles';
import { Restore as RestoreIcon } from '@mui/icons-material';
import {
  Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton,
} from '@mui/material';

import { formatDate, getLabel } from '../utils';
import Config from '../config';

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
  const { configs, onRestoreClick } = props;

  return (
    <TableContainer component={Paper}>
      <Table className={classes.table} size="small">
        <TableHead>
          <TableRow>
            <TableCell className={classes.tableHeaderCell}>Account</TableCell>
            <TableCell className={classes.tableHeaderCell}>Region</TableCell>
            <TableCell className={classes.tableHeaderCell}>Instance Type</TableCell>
            <TableCell className={classes.tableHeaderCell}>Operating System</TableCell>
            <TableCell className={classes.tableHeaderCell}>Expires at</TableCell>
            <TableCell className={classes.tableHeaderCell} />
          </TableRow>
        </TableHead>
        <TableBody>
          {configs.map((config, index) => (
            <TableRow
              key={index}
              className={classes.tableRow}
              onClick={() => onRestoreClick(config)}
            >
              <TableCell className={classes.tableCell}>
                {Config.accountLabels[config.account] || config.account}
              </TableCell>
              <TableCell className={classes.tableCell}>
                { getLabel('regions', config.region) }
              </TableCell>
              <TableCell className={classes.tableCell}>
                { getLabel('instanceTypes', config.instanceType) }
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
