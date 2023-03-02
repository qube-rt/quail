import axios from 'axios';
import queryString from 'query-string';

import Config from './config';
import {
  setAuthToken, getAuthToken, getRefreshToken, handleLogout, removeAuthToken,
} from './utils';

const axiosInstance = axios.create({
  baseURL: Config.api.root,
  headers: { 'Content-Type': 'application/json' },
});

axiosInstance.interceptors.request.use(
  (config) => {
    const idToken = getAuthToken();
    if (idToken) {
      // eslint-disable-next-line no-param-reassign
      config.headers.Authorization = `Bearer ${idToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    const originalRequest = error.config;
    const errorResponse = error.response;

    // In case of 401 response, try using the refresh token
    if (errorResponse && errorResponse.status === 401) {
      // Remove old id token
      removeAuthToken();

      // Fetch a new id token using the refresh token
      return axiosInstance.post(Config.auth.tokenEndpointUrl, queryString.stringify({
        grant_type: 'refresh_token',
        client_id: Config.auth.cognitoClientId,
        refresh_token: getRefreshToken(),
      }), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      }).then((response) => {
        const { id_token: idToken } = response.data;

        // Update the token globally
        setAuthToken(idToken);

        // Retry the failed request
        return axiosInstance(originalRequest);
      }).catch(() => {
        // eslint-disable-next-line no-console
        console.error('Auth failed, redirecting to logout.');
        handleLogout();
      });
    }
    return Promise.reject(error.response);
  },
);

export default axiosInstance;
