import axios from 'axios';

import { useOktaAuth } from '@okta/okta-react';
import { useEffect } from 'react';
import Config from './config';

const axiosInstance = axios.create({
  baseURL: Config.api.root,
  headers: { 'Content-Type': 'application/json' },
});

const AxiosInterceptor = ({ children }) => {
  const { oktaAuth } = useOktaAuth();
  const idToken = oktaAuth.getIdToken();

  useEffect(() => {
    const requestInterceptor = axiosInstance.interceptors.request.use(
      (config) => {
        if (idToken) {
          // eslint-disable-next-line no-param-reassign
          config.headers.Authorization = `Bearer ${idToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error),
    );

    return () => axiosInstance.interceptors.request.eject(requestInterceptor);
  }, [idToken]);

  return children;
};

export { axiosInstance, AxiosInterceptor };
