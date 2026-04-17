@setup @aws @azure @full @debug
# REPORTING ANNOTATIONS
@allure.label.parentSuite:{context.properties.test_results.engine_bom_version}
@allure.label.suite:{context.properties.stack_name}
@allure.label.subSuite:SETUP

Feature: 440-github-oauth-setup - Automate the creation of GitHub OAuth apps for deployments
  As an:     AI Unlimited user
  I want to: Automate the GitHub OAuth app creation process
  So I can:  Use the credentials in AI Unlimited UI

  Scenario: Create a GitHub OAuth app for the deployment
    Given I am signed in to GitHub using my email and password
    And I have a valid stack definition JSON file named context.properties.stack_name

    When I fill the GitHub OAuth form with:
      | field                      | value                                                                                 |
      | Application Name           | context.properties.stack_name                                                         |
      | Homepage URL               | context.properties.stack.Tags.AiUnlimitedWorkspacesURL + ":3000"                      |
      | Authorization Callback URL | context.properties.stack.Tags.AiUnlimitedWorkspacesURL + ":3000/auth/github/callback" |
    And I retrieve the generated OAuth credentials
    And I update the deployment JSON file with the credentials
