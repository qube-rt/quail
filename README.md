
## Quail

Quail gives your users the tools to provision the compute instances they 
need without involving your operations staff. It comes with a user interface 
where your team can select configure their EC2 instance and provision it with 
a click of a button in any supported region or account. And you don't have to 
worry about cleaning them up - Quail handles that for you, too!

## Structure

The application is split into multiple modules:

* `backend` contains the API (lambda, step functions and api gateway) and the associated
  authentication methods (cognito)
* `frontend` contains the user interface code, which is published to ECR in 
  a nginx container
* `frontend-ecs-hosting` configures the hosting configuration for serving the UI
  on ECS, and the associated ELB and Route53 config
* `utilities-global` contains global helpers, e.g. IAM config that doesn't need to be managed
  by the application
* `utilities-regional` contains regional helpers, e.g. VPC config for the instances, that 
  doesn't need to be managed by the application.

A sample application using the modules is available in the `demo` folder.

### Setting up

You'll need an AWS account, AWS CLI installed and AWS credentials configured 
locally (using `aws configure`) in order to run the project.

SES is used to send email notifications with status updates or to notify about 
failures. The region where the project is deployed will need to have a domain 
or an email address validated in SES, and the terraform `notification-email` 
variable needs to be configured to use the desired email. You'll need to 
[disable SES sandbox](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/request-production-access.html) 
mode in order to be able to send emails to addresses outside of the
SES verified email list.

Terraform (>=0.12) is used to provision the resources for the project. If you're using 
non-default aws cli user profile, provide the details to terraform with 
`terraform init -backend-config="profile=<YOUR_PROFILE_NAME>"`

You can receive failure notifications to an SNS topic already used in your organization 
if you provide its arn in the `external-sns-failure-topic-arn` terraform variable.
Otherwise, leaving the variable blank, will create a new topic. Lambda failures
or provisioning failures will send notifications to the topic. The

## AWS SSO Configuration

Terraform does not support SSO SAML applications as a resource, as such those
have to be configured manually through the console. Cognito does not offer a  
metadata file to include in the configuration, the file can be replaced with two attributes though: 
the ServiceProvider application 
Assertion Consumer Service (ACS) url and the SAML audience. The instructions on how to 
obtain them form the pool details can be found [here](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-integrating-3rd-party-saml-providers.html). They're included
below for easy reference:
 
* The ACS URL takes the form of `https://<yourDomainPrefix>.auth.<region>.amazoncognito.com/saml2/idpresponse`
* The audience takes the format of `urn:amazon:cognito:sp:<yourUserPoolID>`

Cognito [does not support IdP-initiated SAML login](https://forums.aws.amazon.com/thread.jspa?threadID=269955), but this can be worked around by specifying the SSO SAML app's start url. 
A url of the form `https://<cognito-domain>.auth.<region>.amazoncognito.com/oauth2/authorize?identity_provider=<cognito saml identity provider>&redirect_uri=<redirect uri>/&response_type=TOKEN&client_id=<client id>&scope=openid` will redirect the user directly to the identity provider
login page, and if the user is authenticated, redirect them back to the `redirect_uri`, replicating 
the behaviour of an IdP-initiated login, despite being an SP-initated login.

To complete the configuration on SSO side an attribute mapping of `Subject` to `${user:subject}` 
needs to be added. Following that the `sso-app-metadata-url` terraform variable should be updated
to use metadata url provided by the SSO SAML application.

Users/groups have to be granted access to the SAML applications via the SSO
console as well.

## Python unit tests



### Limitations

##### Step Functions logging

In 02.2020, CloudWatch log support 
[has been added](https://aws.amazon.com/about-aws/whats-new/2020/02/aws-step-functions-supports-cloudwatch-logs-standard-workflows/) to Step Functions. Unfortunately, latest terraform version (0.13.5) does not support that functionality. Adding the support is a [requested feature](https://github.com/terraform-providers/terraform-provider-aws/issues/12192), 
but work on it hasn't begun at the current time.

The template do create a log group for the Step Function state machine, along 
with granting the state machine the required permissions, however until the 
above feature is implemented, the log group has to be associated with the step 
machine manually.  
 