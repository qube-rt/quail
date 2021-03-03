import Config from './config';
import labels from './labels';

function getAuthToken() {
  return localStorage.getItem('id_token');
}

function getRefreshToken() {
  return localStorage.getItem('refresh_token');
}

function setAuthToken(token) {
  localStorage.setItem('id_token', token);
}

function removeAuthToken() {
  localStorage.removeItem('id_token');
}

function saveTokens(idToken, refreshToken) {
  localStorage.setItem('id_token', idToken);
  localStorage.setItem('refresh_token', refreshToken);
}

function clearAuthData() {
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('code_verifier');
  localStorage.removeItem('id_token');
  localStorage.removeItem('auth_state');
}

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

function handleLogout() {
  clearAuthData();
  window.location = Config.auth.logoutURL;
}

function handleLogin(idToken, refreshToken) {
  clearAuthData();
  saveTokens(idToken, refreshToken);
  // Redirect to home
}

function parseJWT(token) {
  // https://stackoverflow.com/questions/38552003/how-to-decode-jwt-token-in-javascript-without-using-a-library
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  const jsonPayload = decodeURIComponent(atob(base64).split('').map((c) => `%${(`00${c.charCodeAt(0).toString(16)}`).slice(-2)}`).join(''));

  return JSON.parse(jsonPayload);
}

function getUsernameFromJWT() {
  const token = getAuthToken();
  const nickname = token ? parseJWT(token).nickname : '';

  return nickname;
}

function getEmailFromJWT() {
  const token = getAuthToken();
  const email = token ? parseJWT(token).email : '';

  return email;
}

function getSuperuserFlagFromJWT() {
  const token = getAuthToken();
  const isSuperuser = token ? parseJWT(token)['custom:is_superuser'] === '1' : false;

  return isSuperuser;
}

function getGroupFromJWT() {
  const token = getAuthToken();
  const group = token ? parseJWT(token).profile : '';

  return group;
}

// Authentication Code Auth Flow functions
function dec2hex(dec) {
  return (`0${dec.toString(16)}`).substr(-2);
}

function generateRandomString() {
  const array = new Uint32Array(56 / 2);
  window.crypto.getRandomValues(array);
  return Array.from(array, dec2hex).join('');
}

function sha256(plain) { // returns promise ArrayBuffer
  const encoder = new TextEncoder();
  const data = encoder.encode(plain);
  return window.crypto.subtle.digest('SHA-256', data);
}

function base64urlencode(a) {
  let str = '';
  const bytes = new Uint8Array(a);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i += 1) {
    str += String.fromCharCode(bytes[i]);
  }
  return btoa(str)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

async function getChallengeFromVerifier(v) {
  const hashed = await sha256(v);
  const base64encoded = base64urlencode(hashed);
  return base64encoded;
}

function getCodeVerifier() {
  let verifier = localStorage.getItem('code_verifier');
  if (verifier === null) {
    verifier = generateRandomString();
    localStorage.setItem('code_verifier', verifier);
  }
  return verifier;
}

async function getCodeChallenge() {
  const verifier = getCodeVerifier();
  const challenge = await getChallengeFromVerifier(verifier);
  return challenge;
}

function getAuthState() {
  let state = localStorage.getItem('auth_state');
  if (state === null) {
    state = generateRandomString();
    localStorage.setItem('auth_state', state);
  }
  return state;
}

export {
  getAuthToken,
  getRefreshToken,
  setAuthToken,
  clearAuthData,
  getConfigurations,
  saveConfigurations,
  formatDate,
  handleLogout,
  handleLogin,
  getUsernameFromJWT,
  getEmailFromJWT,
  getSuperuserFlagFromJWT,
  getGroupFromJWT,
  getLabel,
  getCodeVerifier,
  getCodeChallenge,
  getAuthState,
  removeAuthToken,
};
