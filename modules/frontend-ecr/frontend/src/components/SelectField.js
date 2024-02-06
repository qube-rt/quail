import React from 'react';

import {
  InputLabel, MenuItem, FormControl, Select, FormHelperText,
} from '@mui/material';

export default function SelectField(props) {
  const {
    label, fieldName, values, selected, onFieldChange, valueLabels, disabled, helperText, classes,
  } = props;

  const formClasses = { ...classes };

  const compare = (left, right) => {
    if (valueLabels) {
      return (valueLabels[left] || left).localeCompare(valueLabels[right] || right);
    }
    return left.localeCompare(right);
  };

  return (
    <FormControl variant="standard" className={formClasses.formControl}>
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
        {values.sort(compare).map((item, index) => (
          <MenuItem key={index} value={item}>
            {valueLabels && item in valueLabels ? valueLabels[item] : item }
          </MenuItem>
        ))}
      </Select>
      {helperText ? <FormHelperText>{helperText}</FormHelperText> : ''}
    </FormControl>
  );
}
