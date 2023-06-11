import { useOktaAuth } from '@okta/okta-react';
import labels from './labels';

function saveConfigurations(configurations) {
  localStorage.setItem('previous_configs', JSON.stringify(configurations));
}

function getConfigurations() {
  return JSON.parse(localStorage.getItem('previous_configs')) || [];
}

function formatDate(date) {
  return new Date(date).toLocaleString();
}

function getLabel(type, key) {
  return key in labels[type] ? labels[type][key] : key;
}

const getUserData = () => {
  const { authState } = useOktaAuth();
  const token = authState.idToken;

  return {
    username: token?.claims?.name,
    email: token?.claims?.email,
    groups: token?.claims?.groups.join(', '),
    is_superuser: !!token?.claims?.groups.includes('quail-admins'),
  };
};

export {
  getConfigurations,
  saveConfigurations,
  formatDate,
  getLabel,
  getUserData,
};
