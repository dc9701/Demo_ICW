@setup @ui @aws @azure @full @debug @aiu
# REPORTING ANNOTATIONS
@allure.label.parentSuite:{context.properties.test_results.engine_bom_version}
@allure.label.suite:{context.properties.stack_name}
@allure.label.subSuite:SETUP

Feature:  450-aiu-setup - First-time configuration of AI Unlimited settings for a stack w/ GitHub integration.
    As an:     AI Unlimited user on a given stack
    I want to: Set up my Git integration, cloud setup & application settings
    So I can:  Use my AI Unlimited project successfully
    .
    # aiu-setup.feature
    #
    # Description: First-time configuration of AI Unlimited settings for a stack w/ GitHub integration.
    #
    # 1. Sign in and open Workspaces > Settings.
    #
    # 2. Set the appropriate values in the Settings pages below:
    #   a. Application settings (accept defaults)
    #   b. Git integration
    #   c. Cloud setup
    #
    # 3. At end of WKS configuration, save the new API_KEYS, then sign out of GitHub.
    #
    # 4. First-time startup of Jupyter server - simply opens the Jupyter URL to 'kick-start' the kernel.
    #
    # JIRAs:
    #   REGULUS-1180 - Configure workspace w/ pre-existing Oauth

    Scenario: 1. Sign in and open Settings.
        Given I am signed in to AI Unlimited on stack context.properties.stack_name

    Scenario: 2a. Accept default values for Settings > Application Settings page.
        When I wait 5 seconds
        And I set the following element values:
            | field | value |
            | Page.Aiu.settings.application.log_level() | INFO |
        When I wait 5 seconds
        And I click Page.Aiu.settings.next()

    Scenario: 2b. Set values of key fields for Settings > Git Integration page.
        When I wait 2 seconds
        And I set the following element values:
            | field | value |
            | Page.Aiu.settings.github.client_id() | context.properties.stack.Tags.GitHubClientID |
            | Page.Aiu.settings.github.client_secret() | context.properties.stack.Tags.GitHubClientSecret |

    Scenario: 2c. Set values of key fields for Settings > Cloud Setup page.
        When I wait 5 seconds
        And I authenticate with GitHub
        And I wait 2 seconds

    Scenario: 3a. At end of configuration, save the new API_KEYS.
        And I click Page.Aiu.settings.next()
        When I select the appropriate cloud service
        And I click Page.Aiu.settings.next()
        And I wait 10 seconds
        And I save the following element values:
            | field | variable |
            | Page.Aiu.your_profile.api_keys() | API_KEYS |
        And I save the following stack tags:
            | tag | value |
            | ApiKeys | context.properties.test_results.API_KEYS |

    Scenario: 4. Open Jupyter UI endpoint to 'kick-start' the Jupyter server.
        When I open the AI UNLIMITED JUPYTER page
        And I wait 10 seconds
