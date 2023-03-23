/* eslint-disable max-len */
import queryString from 'query-string';

const domain = `${window.location.protocol}//${window.location.host}`;
const redirectUrl = `${domain}/auth-callback`;
const apiHost = process.env.REACT_APP_API_HOST;
const cognitoHost = process.env.REACT_APP_COGNITO_HOST;
const cognitoClientId = process.env.REACT_APP_COGNITO_CLIENT_ID;
const logoutURL = process.env.REACT_APP_LOGOUT_URL;

const Config = {
  domain,
  api: {
    root: apiHost,
    param: `${apiHost}/param`,
    instance: `${apiHost}/instance`,
  },
  auth: {
    cognitoClientId,
    redirectUrl,
    logoutURL: `${cognitoHost}/logout?client_id=${cognitoClientId}&logout_uri=${logoutURL}`,
    // The Login URL taking the user to Cognito, where they can choose their authentication method.
    // SPLoginUrl: `${cognitoHost}/login?response_type=token&client_id=${cognitoClientId}&redirect_uri=${redirectUrl}&scope=openid+profile`,
    // Short circuting the cognito authentication selection to use the Cognito-provided OAuth with a SAML identity provider
    // The url is still missing an oauth PKCE verifier and state params, added by the application
    getLoginUrl: (identityProvider, authState, codeChallenge) => `${cognitoHost}/oauth2/authorize?${queryString.stringify({
      response_type: 'code',
      client_id: cognitoClientId,
      redirect_uri: redirectUrl,
      scope: 'openid profile',
      code_challenge_method: 'S256',
      identity_provider: identityProvider,
      state: authState,
      code_challenge: codeChallenge,
    })}`,
    tokenEndpointUrl: `${cognitoHost}/oauth2/token`,
  },
};

export default Config;
