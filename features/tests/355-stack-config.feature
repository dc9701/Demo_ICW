@aws @full
# REPORTING ANNOTATIONS
@allure.label.parentSuite:{context.properties.test_results.engine_bom_version}
@allure.label.suite:{context.properties.stack_name}
@allure.label.subSuite:CONFIG

Feature: 355-stack-config - Deploy stacks of various InstanceTypes on AWS & Azure (WKS & JUP), then delete them.
As an:     AI Unlimited user with access to AWS and/or Azure resources
I want to: Deploy stack of various InstanceTypes (both Workspaces & Jupyter)
So I can:  Verify stack deployment works for a range of InstanceTypes
.
# stack-config.feature
#
# Description: Deploy stacks of various InstanceTypes on AWS & Azure (WKS & JUP), then delete them.

    Scenario Outline: 1. Deploy AWS stack (<instance_type>), verify deployment, then delete it.
        When I deploy a new stack with:
            | parameter                    | value |
            | name                         | aiu-test-aws-uswest2-full-<name> |
            | templates                    | https://s3.us-west-2.amazonaws.com/ai.unlimited.deployment.staging.us-west-2/unlimited-manager.yaml |
            | AiUnlimitedName              | context.properties.stack_name |
            | InstanceType                 | <instance_type> |
            | AvailablityZone              | us-west-2a |

        # Deployment may take 10 minutes or so...
        Then I verify the stack "context.properties.stack_name + '-wks'" is successfully created
        And I verify the stack "context.properties.stack_name + '-jup'" is successfully created

        Examples:
            | name    | instance_type |
            | small   | t3.small |
            | medium  | t3.medium |
            | large   | t3.large |
            # These larger stack deployments timeout after ~1200 secs (20 mins).
            # | xlarge  | m4.xlarge |
            # | 2xlarge | c4.2xlarge |
            # | 4xlarge | r3.4xlarge |
            # | 8xlarge | i2.8xlarge |
            
    Scenario Outline: 2. Delete the deployed stacks.
        # Have to delete JUP stack resources first...        
        When I delete the stack "context.properties.stack_name + '-<name>-jup'"
        Then I verify the stack "context.properties.stack_name + '-<name>-jup'" no longer exists
        When I delete the stack "context.properties.stack_name + '-<name>-wks'"
        Then I verify the stack "context.properties.stack_name + '-<name>-wks'" no longer exists

        Examples:
            | name    | instance_type |
            | small   | t3.small |
            | medium  | t3.medium |
            | large   | t3.large |
            # These larger stack deployments timeout after ~1200 secs (20 mins).
            # | xlarge  | m4.xlarge |
            # | 2xlarge | c4.2xlarge |
            # | 4xlarge | r3.4xlarge |
            # | 8xlarge | i2.8xlarge |
