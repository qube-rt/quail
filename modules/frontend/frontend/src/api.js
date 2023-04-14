import baseAxios from 'axios';
import queryString from 'query-string';

import Config from './config';
import appAxios from './axios';

const getCognitoToken = async ({
  receivedCode, codeVerifier,
}) => baseAxios.post(Config.auth.tokenEndpointUrl, queryString.stringify({
  grant_type: 'authorization_code',
  client_id: Config.auth.cognitoClientId,
  redirect_uri: Config.auth.redirectUrl,
  code: receivedCode,
  code_challenge_method: 'S256',
  code_verifier: codeVerifier,
}), {
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
});

const getParams = async () => appAxios.get('param');

const getInstances = async () => appAxios.get('instance');

const deleteInstance = async ({ instanceId }) => appAxios.delete(`instance/${instanceId}`);

const extendInstance = async ({ instanceId }) => appAxios.post(`instance/${instanceId}/extend`);

const startInstance = async ({ instanceId }) => appAxios.post(`instance/${instanceId}/start`);

const stopInstance = async ({ instanceId }) => appAxios.post(`instance/${instanceId}/stop`);

const updateInstance = async ({ instanceId, instanceType }) => appAxios.patch(`instance/${instanceId}`, { instanceType });

const createInstance = async (payload) => appAxios.post('instance', payload);

const API = {
  getCognitoToken,
  getParams,
  getInstances,
  deleteInstance,
  extendInstance,
  startInstance,
  stopInstance,
  updateInstance,
  createInstance,
};

export default API;
