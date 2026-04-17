@teardown @aws @full
# REPORTING ANNOTATIONS
@allure.label.parentSuite:{context.properties.test_results.engine_bom_version}
@allure.label.suite:{context.properties.stack_name}
@allure.label.subSuite:TEARDOWN

Feature: 950-aws-stack-delete - Delete the previously-deployed AWS stack.
As an:     AI Unlimited user with access to AWS resources
I want to: Delete a deployed AWS stack once testing has completed
So I can:  Free resources for additional test stacks
.
# aws-stack-delete.feature
#
# Description: Delete the previously-deployed AWS stack.

  Scenario: Delete the deployed stacks.
    # Have to delete JUP stack resources first...        
    When I delete the stack "context.properties.stack_name + '-jup'"
    Then I verify the stack "context.properties.stack_name + '-jup'" no longer exists
    When I delete the stack "context.properties.stack_name + '-wks'"
    Then I verify the stack "context.properties.stack_name + '-wks'" no longer exists
