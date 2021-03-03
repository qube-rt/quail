# QUAIL - The **QU**be **A**ws **I**nstance **L**easer

![Quail Logo](/img/logo.png?raw=true)

Quail gives your users the tools to provision the compute instances they 
need without involving your operations staff. It comes with a user interface 
where your team can select configure their EC2 instance and provision it with 
a click of a button in any supported region or account. And you don't have to 
worry about cleaning them up - Quail handles that for you, too!

## Features

A basic list of features supported includes:

  * Automated provisioning and clean-up of EC2 instances
    * Instance expiration time is specified at launch, and can be configured with a maximum lifetime
  * Users have the ability to 'emergency-extend' the life of an instance
  * Maximum number of instances per user is configurable per-team
  * Multiple operating system support, with unique AMIs, Security Groups and IAM roles configured per-team
  * Centralised authentication via Amazon Cognito
  * Terraform based, modular deployment - to fit in with even the most esoteric of AWS environments!

## Screenshot

![Quail interface screenshot](/img/screenshot.png?raw=true "Everyone loves a good screenshot, right?")

## How does it work?

Quail consists of a front end web application written in React, leveraging AWS
API Gateway and Lambda functions to orchestrate CloudFormation Stacks and
StackSets in order to provision temporary EC2 instances for logged-in users.
Authentication is handled via Cognito (and so allows authentication via Social
platforms as well as SAML, OpenIDConnect, etc.).

Application configuration is stored in DynamoDB tables, which provides the
permitted instance types, AMI IDs, Security Groups and IAM permissions that are
assigned. Quail uses the concept of 'teams' to differentiate configurations and
available provisioning templates.

When a user provisions a new instance, the relevant CloudFormation template is
provisioned - the demo application currently only covers provisioning an EC2
instance, but these templates are free-form so you can add other resources
should they be required. Refer to the [Demo App configuration](demo/main.tf)
for more information.

## Deployment

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
or provisioning failures will send notifications to the topic.

For anything other than test deployments, you will likely want to fork this
repository, and create your own variant of the `demo` application, to fit your
environment.

## Repository Structure

The application is split into multiple modules:

* `backend` contains the API (Lambda, Step Functions and API Gateway) and the associated
  authentication methods (Cognito)
* `frontend` contains the user interface code, which is published to ECR in 
  a nginx container
* `frontend-ecs-hosting` configures the hosting configuration for serving the UI
  on ECS, and the associated ELB and Route53 config
* `utilities-global` contains global helpers, e.g. IAM config that doesn't need to be managed
  by the application
* `utilities-regional` contains regional helpers, e.g. VPC config for the instances, that 
  doesn't need to be managed by the application.

A sample application using the modules is available in the `demo` folder.

## AWS SSO Configuration with SAML

Terraform does not support SSO SAML applications as a resource, as such those
have to be configured manually through the console. Cognito does not offer a
metadata file to include in the configuration, the file can be replaced with
two attributes though: the ServiceProvider application Assertion Consumer
Service (ACS) url and the SAML audience. The instructions on how to obtain them
form the pool details can be found
[here](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-integrating-3rd-party-saml-providers.html).
They're included below for easy reference:
 
* The ACS URL takes the form of `https://<yourDomainPrefix>.auth.<region>.amazoncognito.com/saml2/idpresponse`
* The audience takes the format of `urn:amazon:cognito:sp:<yourUserPoolID>`

Cognito [does not support IdP-initiated SAML
login](https://forums.aws.amazon.com/thread.jspa?threadID=269955), but this can
be worked around by specifying the SSO SAML app's start url.  A url of the form
`https://<cognito-domain>.auth.<region>.amazoncognito.com/oauth2/authorize?identity_provider=<cognito
saml identity provider>&redirect_uri=<redirect
uri>/&response_type=TOKEN&client_id=<client id>&scope=openid` will redirect the
user directly to the identity provider login page, and if the user is
authenticated, redirect them back to the `redirect_uri`, replicating the
behaviour of an IdP-initiated login, despite being an SP-initated login.

To complete the configuration on SSO side an attribute mapping of `Subject` to
`${user:subject}` needs to be added. Following that the `sso-app-metadata-url`
terraform variable should be updated to use metadata url provided by the SSO
SAML application.

Users/groups have to be granted access to the SAML applications via the SSO
console as well.

## Limitations

##### Step Functions logging

In 02.2020, CloudWatch log support 
[has been added](https://aws.amazon.com/about-aws/whats-new/2020/02/aws-step-functions-supports-cloudwatch-logs-standard-workflows/) to Step Functions. Unfortunately, latest terraform version (0.13.5) does not support that functionality. Adding the support is a [requested feature](https://github.com/terraform-providers/terraform-provider-aws/issues/12192), 
but work on it hasn't begun at the current time.

The template do create a log group for the Step Function state machine, along 
with granting the state machine the required permissions, however until the 
above feature is implemented, the log group has to be associated with the step 
machine manually.  

## Contributing

Contributions to this repository are welcome, via the usual method of GitHub Issues and Pull Requests.

## License

Copyright &copy; 2021 [Qube Research and Technologies](https://www.qube-rt.com/ "Qube Research and Technologies homepage")

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
these files except in compliance with the License. You may obtain a copy of the
License at: http://www.apache.org/licenses/LICENSE-2.0, or from the LICENSE
file contained in this repository.

Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
