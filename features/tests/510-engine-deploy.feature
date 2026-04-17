@setup @aws @azure @full
# REPORTING ANNOTATIONS
@allure.label.parentSuite:{context.properties.test_results.engine_bom_version}
@allure.label.suite:{context.properties.stack_name}
@allure.label.subSuite:SETUP

Feature:  510-engine-deploy - Deploys a new project engine on the specified stack and displays DB engine version.
    As an:     AI Unlimited user connected to Jupyter on a given stack
    I want to: Deploy a new engine (aka, CE cluster) for my project
    So I can:  Connect and run SQL queries in later testing
    .
    # engine_deploy.feature
    #
    # Description: Deploys a new project engine on the specified stack, then adds engine info to stack def tags.
    #
    # 1. Setup:
    #   a. Open the specified stack's Jupyter server at context.properties.stack.Tags.AiUnlimitedJupyterURL.
    #   b. Connect to the 'teradatasql' kernel to interact with the AI Unlimited Jupyter server.
    #   c. Open the GetStarted.ipynb notbook, which has the suggested %project_engine_deploy playbook.
    #
    # 2. Deploy Engine:
    #   a. Run the necessary notebook code cells with the appropriate parameters to deploy the project engine.
    #   b. Upon successful engine deployment, capture engine parameters (e.g., EngineUser, EnginePassword) as results.
    #   c. Also capture the deployment time and engine version result.
    #
    # JIRAs:
    #   REGULUS-1173 - Autotests for Jupyter CE cluster deployment (AWS)

    Scenario: 1. SETUP: Open the project Jupyter notebook, connect to the workspace and create the project & authorization object.
        Given I am connected to Jupyter on stack context.properties.stack_name
        When I open the GetStarted notebook
        And I run the 'workspaces_config' step with:
            | field   | value |
            | host    | http://{context.properties.stack.Parameters.AiUnlimitedServerBaseUrl}:3282 |
            | apikey  | context.properties.stack.Tags.ApiKeys |
            | withtls | F |
		Then I verify the output contains 'Workspace service configured'

        When I run the 'project_create' step with:
            | field   | value |
            | project | context.properties.stack_name |
            | env     | context.properties.cloud |
		Then I verify the output contains 'Project .* created'

        When I run the 'project_auth_create' step with:
            | field   | value |
            | name    | context.properties.stack_name |
            | project | context.properties.stack_name |
            | key     | context.properties.aws_access_key_id |
            | secret  | context.properties.aws_secret_access_key |
		Then I verify the output contains 'Authorization .* created'

    Scenario: 2. DEPLOY ENGINE: Create authorization object and deploy the project engine.
        When I run the 'project_engine_deploy' step with:
            | field        | value |
            | project      | context.properties.stack_name |
            | size         | small |
            | node         | 2 |
            | imagelisting | private |
            # | dev          | <dev> |  # Skip using dev releases for UAT testing
            # | imageowner   | <imageowner> |

        # Engine deployment may take 10 minutes or so...
		Then I verify the output contains 'State: DEPLOYED'
        And I save the output matching 'provisioned.* Duration: (.*)\)' as result PROVISION_TIME
        And I save the output matching 'configured.* Duration: (.*)\)' as result CONFIGURE_TIME
        And I save the output matching 'DEPLOYED, Duration: (.*)\)' as result DEPLOY_TIME
        And I save the output matching '│ (\S+) +│ \S+ +│ \S+ │ \S+ │' as result PUBLIC_IP
        And I save the output matching '│ \S+ +│ (\S+) +│ \S+ │ \S+ │' as result PRIVATE_IP
        And I save the output matching '│ \S+ +│ \S+ +│ (\S+) │ \S+ │' as result USER
        And I save the output matching '│ \S+ +│ \S+ +│ \S+ │ (\S+) │' as result PASSWORD

        When I run '%connect {context.properties.connection}'
		Then I verify the output contains 'activated for user'

        # If succssful, persist Tags.ProjectUserName in stack definition file.
        When I save the following stack tags:
            | tag             | value |
            | ProjectUserName | context.properties.test_results.USER |

        # Capture engine version in test results.
        When I run
            """
            SELECT  InfoData AS Version
            FROM    DBC.DBCInfoV
            WHERE   InfoKey = 'VERSION';
            """
        Then I save the output matching '\d\d\..*\.\d\d' as result ENGINE_VERSION
