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
  * Centralised authentication via Okta
  * Terraform based, modular deployment - to fit in with even the most esoteric of AWS environments!

## Screenshot

![Quail interface screenshot](/img/screenshot.png?raw=true "Everyone loves a good screenshot, right?")

## How does it work?

Quail consists of a front end web application written in React, leveraging AWS
API Gateway and Lambda functions to orchestrate CloudFormation Stacks and
StackSets in order to provision temporary EC2 instances for logged-in users.
Authentication is handled via Okta (and so allows authentication via Social
platforms as well as SAML, OpenIDConnect, etc.).

Application configuration is stored in DynamoDB tables, which provides the
permitted instance types, AMI IDs, Security Groups and IAM permissions that are
assigned. Quail uses the concept of 'teams' to differentiate configurations and
available provisioning templates.

When a user provisions a new instance, the relevant CloudFormation template is
provisioned - the example application currently only covers provisioning an EC2
instance, but these templates are free-form so you can add other resources
should they be required. Refer to the [Example App configuration](##example-app-deployment)
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

Terraform (>=1.3) is used to provision the resources for the project. If you're using a
non-default aws cli user profile, provide the details to terraform with 
`terraform init -backend-config="profile=<YOUR_PROFILE_NAME>"`

You can receive failure notifications to an SNS topic already used in your organization 
if you provide its arn in the `external-sns-failure-topic-arn` terraform variable.
Otherwise, leaving the variable blank, will create a new topic. Lambda failures
or provisioning failures will send notifications to the topic.

[Okta](https://developer.okta.com/) is used for authentication. You can sign up for a
developer account and you'll need to create an API key for terraform to use.

For anything other than test deployments, you will likely want to fork this
repository, and create your own variant of the `example-app` application, to fit your
environment.

## Repository Structure

The application is split into multiple modules:

* `backend-ecr` contains the backend source code, builds a docker image and pushed it to ECR
* `backend` contains the API (Lambda, Step Functions and API Gateway)
* `frontend-ecr` contains the frontend application, builds it in a multi-stage docker image
  and publishes a nginx container to ECR
* `frontend-ecs-hosting` configures the hosting configuration for serving the UI
  on ECS, and the associated ELB and Route53 config
* `utilities-account` contains per-account helpers, e.g. IAM config that doesn't need
  to be managed by the application
* `utilities-regional` contains regional helpers, e.g. VPC config for the instances, that 
  doesn't need to be managed by the application.
* `okta-app` contains the configuration of an Okta Oauth application.
* `okta-data` creates several uses and groups that can be used to test the app.

A sample application using the modules is available in the `example-app` folder.

## Example App Deployment

The example app has been set up to decouple application deployment from infrastructure/
configuration deployment. It consits of three modules - `backend-images`,
`frontend-image` and `infrastructure`.

Due to dependencies between the componenets, the following steps should be followed
in order to complete the initial deployment.

1. Deploy the resources from the `backend-image` directory.
1. Use the outputs from the `backend-image` deployment as input to `infrastructure`
1. Set `skip-resources-first-deployment` to `true` in the `infrastructure` variable file.
1. Deploy the `infrastructure` dir.
1. Use the outputs from the `infrastructure` deployment as input to `frontend-image`
1. Deploy the `frontend-image` directory.
1. Use the outputs from the `frontend-image` deployment as input to `infrastructure`
1. Set `skip-resources-first-deployment` to `false` in the `infrastructure` variable file.
1. Deploy the infrastructure directory again.

## Limitations

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
