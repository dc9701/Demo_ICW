@ui @aws @azure @full 
# REPORTING ANNOTATIONS
@allure.label.parentSuite:{context.properties.test_results.engine_bom_version}
@allure.label.suite:{context.properties.stack_name}
@allure.label.subSuite:SETUP

Feature:  451-aiu-settings-check-aws-github - Verify AI Unlimited settings for a stack on AWS w/ GitHub integration.
    As an:     AI Unlimited user on a given stack
    I want to: Verify my Git integration, cloud setup & application settings
    So I can:  Use my AI Unlimited project successfully
    .
    # aiu-settings-check-github-aws.feature
    #
    # Description: Verify AI Unlimited settings for a stack on AWS w/ GitHub integration.
    #
    # 1. Sign in and verify you've landed on the main page.
    #
    # 2. Verify selected fields in the Settings pages below match the stack's values:
    #   a. Git integration
    #   b. Cloud setup
    #   c. Application settings
    #
    # JIRAs:
    #   REGULUS-1172 - Autotests for AI Unlimited (workspaces) configuration

    Scenario: 1. Sign in and verify we've landed on the main page.
        Given I am signed in to AI Unlimited on stack context.properties.stack_name
        # Drop-downs take a second to load...
        When I wait 1 seconds
        Then I verify the following elements exist:
            | field | value |
            | Page.Aiu.quick_links.create_run_your_first_project() | |
            | Page.Aiu.quick_links.explore_sample_usecases() | |
            | Page.Aiu.your_profile.api_keys() | |
            | Page.Aiu.your_profile.view_all() | |
            | Page.Aiu.your_projects.view_all() | |

    Scenario: 2a. Verify values of key fields for Settings > Application Settings page.
        When I open the Settings page
        Then I verify the following element values match:
            | field | value |
            | Page.Aiu.settings.application.log_level() | INFO |
            | Page.Aiu.settings.application.tls() | '' |

    Scenario: 2b. Verify values of key fields for Settings > Git Integration page.
        When I click Page.Aiu.settings.next()
        Then I verify the following element values match:
            | field | value |
            | Page.Aiu.settings.github.github_url() | https://github.com |
            | Page.Aiu.settings.github.homepage_url() | context.properties.stack.Tags.AiUnlimitedWorkspacesURL |
            | Page.Aiu.settings.github.callback_url() | {context.properties.stack.Tags.AiUnlimitedWorkspacesURL}:3000/auth/github/callback |
            | Page.Aiu.settings.github.client_id() | context.properties.stack.Tags.GitHubClientID |
            | Page.Aiu.settings.github.client_secret() | context.properties.stack.Tags.GitHubClientSecret |
            # Not finding... | Page.Aiu.settings.github.authorizing_organization() | context.properties.stack.Tags.GitHubAuthOrg |
            # Not finding... | Page.Aiu.settings.github.repository_organization() | context.properties.stack.Tags.GitHubRepoOrg |

    Scenario: 2c. Verify values of key fields for Settings > Cloud Setup (AWS) page.
        When I click Page.Aiu.settings.next()
        And I set the following element values:
            | field | value |
            | Page.Aiu.settings.aws.subnet() | context.properties.stack.Parameters.Subnet |
            | Page.Aiu.settings.aws.network_type() | context.properties.stack.Tage.NetworkType |
        When I wait 1 seconds
        Then I verify the following element values match:
            | field | value |
            # Not finding... | Page.Aiu.settings.aws.region() | context.properties.stack.Parameters.AvailabilityZone |
            | Page.Aiu.settings.aws.subnet() | context.properties.stack.Parameters.Subnet |
            # Not finding... | Page.Aiu.settings.aws.iam_role() | context.properties.stack.Parameters.IamRoleName |
            # Not finding... | Page.Aiu.settings.aws.resource_tags() | None |
            # Not finding... | Page.Aiu.settings.aws.cidrs() | context.properties.stack.Parameters.AccessCIDR |
            # Not finding... | Page.Aiu.settings.aws.prefix_list_names() | context.properties.stack.Parameters.PrefixList |
            # The UI Security Group Names is a concatenation of two AWS CloudFormation outputs, hence two comparisons:
            # Not finding... | Page.Aiu.settings.aws.security_group_names() | context.properties.stack.Parameters.LoadBalancerSecurityGroups |
            # Not finding... | Page.Aiu.settings.aws.security_group_names() | context.properties.stack.Parameters.InstanceSecurityGroups |
            # Not finding... | Page.Aiu.settings.aws.permissions_boundary_arns() | context.properties.stack.NotificationARNs |
            | Page.Aiu.settings.aws.network_type() | context.properties.stack.Tags.NetworkType |
