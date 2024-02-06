import { useOktaAuth } from '@okta/okta-react';
import Config from './config';

function getConfigurations() {
  return JSON.parse(localStorage.getItem('previous_configs')) || [];
}

function saveConfigurations(newConfig) {
  const configurations = [
    newConfig,
    ...getConfigurations(),
  ].slice(0, 20);

  localStorage.setItem('previous_configs', JSON.stringify(configurations));
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
    groups: token?.claims?.groups.sort() || [],
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
