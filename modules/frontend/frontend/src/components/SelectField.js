import React from 'react';

import InputLabel from '@material-ui/core/InputLabel';
import MenuItem from '@material-ui/core/MenuItem';
import FormControl from '@material-ui/core/FormControl';
import Select from '@material-ui/core/Select';
import FormHelperText from '@material-ui/core/FormHelperText';

export default function SelectField(props) {
  const {
    label, fieldName, values, selected, onFieldChange, valueLabels, disabled, helperText, classes,
  } = props;

  const formClasses = { ...classes };

  return (
    <FormControl className={formClasses.formControl}>
      {label ? <InputLabel id={`${fieldName}-label`}>{label}</InputLabel> : ''}
      <Select
        labelId={`${fieldName}-label`}
        id={`${fieldName}-select`}
        value={selected || ''}
        disabled={disabled}
        onChange={(e) => onFieldChange(e, fieldName)}
        autoWidth
        fullWidth
      >
        {values.map((item, index) => (
          <MenuItem key={index} value={item}>
            {valueLabels && item in valueLabels ? valueLabels[item] : item }
          </MenuItem>
        ))}
      </Select>
      {helperText ? <FormHelperText>{helperText}</FormHelperText> : ''}
    </FormControl>
  );
}
