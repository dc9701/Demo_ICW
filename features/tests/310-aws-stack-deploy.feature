@setup @aws @full
# REPORTING ANNOTATIONS
@allure.label.parentSuite:{context.properties.test_results.engine_bom_version}
@allure.label.suite:{context.properties.stack_name}
@allure.label.subSuite:SETUP

Feature: 310-aws-stack-deploy - Deploy a CloudFormation stack on AWS, capture outputs, then verify the stack deployed successfully.
As an:     AI Unlimited user with access to AWS resources
I want to: Deploy a CloudFromation stack using AWS SDK
So I can:  Verify the deployment and use the resources in later testing
.
# aws-stack-deploy.feature
#
# Description: Deploy a CloudFormation stack on AWS (WKS & JUP), then verify the stack(s) deployed successfully.

    Scenario: Deploy CloudFormation template, verify deployment, and capture outputs
        When I deploy a new stack with:
            | parameter                    | value |
            | name                         | context.properties.stack_name |
            | templates                    | https://s3.us-west-2.amazonaws.com/ai.unlimited.deployment.staging.us-west-2/unlimited-manager.yaml |
            | AiUnlimitedName              | context.properties.stack_name |
            | AiUnlimitedVersion           | v0.3.12 |
            | AiUnlimitedUiVersion         | v0.1.9 |
            | InstanceType                 | t3.medium |
            | AvailabilityZone             | us-west-2a |

        Then I verify the stack "context.properties.stack_name + '-wks'" is successfully created
        And I verify the stack "context.properties.stack_name + '-jup'" is successfully created
        
        # Give Jupyter kernel time to come up before proceeding with next @setup test.
        When I wait 180 seconds
