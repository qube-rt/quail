import { axiosInstance } from './Axios';

const getParams = async () => axiosInstance.get('param');

const getInstances = async () => axiosInstance.get('instance');

const deleteInstance = async ({ instanceId }) => axiosInstance.delete(`instance/${instanceId}`);

const extendInstance = async ({ instanceId }) => axiosInstance.post(`instance/${instanceId}/extend`);

const startInstance = async ({ instanceId }) => axiosInstance.post(`instance/${instanceId}/start`);

const stopInstance = async ({ instanceId }) => axiosInstance.post(`instance/${instanceId}/stop`);

const updateInstance = async ({ instanceId, instanceType }) => axiosInstance.patch(`instance/${instanceId}`, { instanceType });

const createInstance = async (payload) => axiosInstance.post('instance', payload);

const API = {
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
