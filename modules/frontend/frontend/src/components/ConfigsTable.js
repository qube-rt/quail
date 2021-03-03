import React from 'react';

import { makeStyles } from '@material-ui/core/styles';
import RestoreIcon from '@material-ui/icons/Restore';
import Paper from '@material-ui/core/Paper';
import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableContainer from '@material-ui/core/TableContainer';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import IconButton from '@material-ui/core/IconButton';

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
  const { configs, onRestoreClick } = props;

  return (
    <TableContainer component={Paper}>
      <Table className={classes.table} size="small">
        <TableHead>
          <TableRow>
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
              onClick={(e) => onRestoreClick(e, config)}
            >
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
                  onClick={(e) => onRestoreClick(e, config)}
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
