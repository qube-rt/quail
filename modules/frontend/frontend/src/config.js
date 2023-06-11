const domain = `${window.location.protocol}//${window.location.host}`;
const apiHost = process.env.REACT_APP_API_HOST;

// const CLIENT_ID = '0oa9w825dhkMgNA1Q5d7';
// const ISSUER = 'https://dev-36256492.okta.com/oauth2/aus9w7yu8qX5yboZX5d7';
const CLIENT_ID = process.env.REACT_APP_JWT_CLIENT_ID;
const ISSUER = process.env.REACT_APP_JWT_ISSUER;
const OKTA_TESTING_DISABLEHTTPSCHECK = window.location.origin.includes('localhost');
const REDIRECT_URI = `${window.location.origin}/login/callback`;

const Config = {
  domain,
  api: {
    root: apiHost,
  },
  oidc: {
    clientId: CLIENT_ID,
    issuer: ISSUER,
    redirectUri: REDIRECT_URI,
    scopes: ['openid', 'profile', 'groups', 'email'],
    pkce: true,
    disableHttpsCheck: OKTA_TESTING_DISABLEHTTPSCHECK,
  },
};

export default Config;
