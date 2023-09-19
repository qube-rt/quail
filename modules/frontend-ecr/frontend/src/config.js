const domain = `${window.location.protocol}//${window.location.host}`;
const apiHost = process.env.REACT_APP_API_HOST;

const CLIENT_ID = process.env.REACT_APP_JWT_CLIENT_ID;
const ISSUER = process.env.REACT_APP_JWT_ISSUER;
const OKTA_TESTING_DISABLEHTTPSCHECK = window.location.origin.includes('localhost');
const REDIRECT_URI = `${window.location.origin}/login/callback`;
const REGION_LABELS = JSON.parse(process.env.REACT_APP_REGION_LABELS);
const ACCOUNT_LABELS = JSON.parse(process.env.REACT_APP_ACCOUNT_LABELS);
const INSTANCE_LABELS = JSON.parse(process.env.REACT_APP_INSTANCE_LABELS);
const ADMIN_GROUP_NAME = process.env.REACT_APP_ADMIN_GROUP_NAME;

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
  regionLabels: REGION_LABELS,
  accountLabels: ACCOUNT_LABELS,
  instanceLabels: INSTANCE_LABELS,
  adminGroupName: ADMIN_GROUP_NAME,
};

export default Config;
