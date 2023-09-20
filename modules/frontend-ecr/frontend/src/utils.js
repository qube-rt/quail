import { useOktaAuth } from '@okta/okta-react';
import Config from './config';

function saveConfigurations(configurations) {
  localStorage.setItem('previous_configs', JSON.stringify(configurations));
}

function getConfigurations() {
  return JSON.parse(localStorage.getItem('previous_configs')) || [];
}

function formatDate(date) {
  return new Date(date).toLocaleTimeString(navigator.languages, {
    year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

function getLabel(type, key) {
  return key in Config[type] ? Config[type][key] : key;
}

const getUserData = () => {
  const { authState } = useOktaAuth();
  const token = authState.idToken;

  return {
    username: token?.claims?.name,
    email: token?.claims?.email,
    groups: token?.claims?.groups.join(', '),
    is_superuser: !!token?.claims?.groups.includes(Config.adminGroupName),
  };
};

export {
  getConfigurations,
  saveConfigurations,
  formatDate,
  getLabel,
  getUserData,
};
