@uat @aws @azure @full
# REPORTING ANNOTATIONS
@allure.label.parentSuite:{context.properties.test_results.engine_bom_version}
@allure.label.suite:{context.properties.stack_name}
@allure.label.subSuite:CONFIG

Feature:  555-engine-config - Deploys engines of specified size, verifies connection and captures DB stats, then destroys them.
    As an:     AI Unlimited user connected to Jupyter on a given stack
    I want to: Deploy a new engine of a given configuration
    So I can:  Verify various engine configs deploy successfully
    .
    # engine-config.feature
    #
    # Description: Deploys a new project engine of specified config and captures DB stats, then destroys it.
    #
    # 1. Connect:
    #   a. Open the specified stack's Jupyter server at context.properties.stack.Tags.AiUnlimitedJupyterURL.
    #   b. Connect to the 'teradatasql' kernel to interact with the AI Unlimited Jupyter server.
    #   c. Open the GetStarted.ipynb notbook, which has the suggested %project_engine_deploy playbook.
    #
    # 2. Setup:
    #   a. Run the necessary notebook code to create the project(s).
    #   b. Likewise, create the authorization object(s).
    #
    # 3. Deploy Engine(s):
    #   a. Run the necessary notebook code cell with the appropriate parameters to deploy the project engine.
    #   b. Upon successful engine deployment, capture engine parameters, times and engine version as results.
    #   c. Also capture the deployment time and engine version result.
    #
    # 4. Destroy Engine(s):
    #   a. Disconnect...
    #   b. Suspend the engine...
    #   c. Remove the project auth object...
    #   d. Then delete the project so the test may be run anew.
    #
    # JIRAs:
    #   REGULUS-1303 - Create engine-config tests of various sizes to compare deploy_time, etc

    Scenario: 1. CONNECT: Open the project Jupyter notebook and connect to the workspace.
        Given I am connected to Jupyter on stack context.properties.stack_name
        When I open the GetStarted notebook
        And I run the 'workspaces_config' step with:
            | field   | value |
            | host    | http://{context.properties.stack.Parameters.AiUnlimitedServerBaseUrl}:3282 |
            | apikey  | context.properties.stack.Tags.ApiKeys |
            | withtls | F |
		Then I verify the output contains 'Workspace service configured'

    Scenario Outline: 2a. SETUP: Create the <project> project.
        When I run the 'project_create' step with:
            | field   | value |
            | project | <project> |
            | env     | context.properties.cloud |
		Then I verify the output contains 'Project .* created'

        Examples:
            | project              |
            | 'aiu-test-small-01'  |
            | 'aiu-test-medium-02' |
            # DCC | 'aiu-test-small-02'  |
            # DCC | 'aiu-test-medium-04' |
            # DCC | 'aiu-test-large-04'  |
            # DCC | 'aiu-test-large-08'  |
            # DCC | 'aiu-test-xlarge-08' |
            # DCC | 'aiu-test-large-32'  |

    Scenario Outline: 2b. SETUP: Create the <project> authorization.
        When I run the 'project_auth_create' step with:
            | field   | value |
            | name    | <project> |
            | project | <project> |
            | key     | context.properties.aws_access_key_id |
            | secret  | context.properties.aws_secret_access_key |
            | region  | context.properties.region_name |
		Then I verify the output contains 'Authorization .* created'

        Examples:
            | project              |
            | 'aiu-test-small-01'  |
            | 'aiu-test-medium-02' |
            # DCC | 'aiu-test-small-02'  |
            # DCC | 'aiu-test-medium-04' |
            # DCC | 'aiu-test-large-04'  |
            # DCC | 'aiu-test-large-08'  |
            # DCC | 'aiu-test-xlarge-08' |
            # DCC | 'aiu-test-large-32'  |

    Scenario Outline: 3a. DEPLOY ENGINE(S): Deploy the <proj_engine> project engine.
        When I run the 'project_engine_deploy' step with:
            | field        | value |
            | project      | <proj_engine> |
            | size         | <size> |
            | node         | <nodes> |
            | imagelisting | private |
            # | dev          | <dev> |  # Skip using dev releases for UAT testing
            # | imageowner   | <imageowner> |

        # Engine deployment may take 10 minutes or so...
		Then I verify the output contains 'State: DEPLOYED'
        And I save the output matching 'provisioned.* Duration: (.*)\)' as result PROVISION_TIME
        And I save the output matching 'configured.* Duration: (.*)\)' as result CONFIGURE_TIME
        And I save the output matching 'DEPLOYED, Duration: (.*)\)' as result DEPLOY_TIME
        And I save the output matching '│ (\S+) │ \S+ │ \S+ │ \S+ │' as result PUBLIC_IP
        And I save the output matching '│ \S+ │ (\S+) │ \S+ │ \S+ │' as result PRIVATE_IP
        And I save the output matching '│ \S+ │ \S+ │ (\S+) │ \S+ │' as result USER
        And I save the output matching '│ \S+ │ \S+ │ \S+ │ (\S+) │' as result PASSWORD

        Examples:
            | proj_engine          | size       | nodes | dev | imageowner   |
            | 'aiu-test-small-01'  | small      | 1     | t   | 989207584854 |
            | 'aiu-test-medium-02' | medium     | 2     | t   | 989207584854 |
            # DCC | 'aiu-test-small-02'  | small      | 2     | t   | 989207584854 |
            # DCC | 'aiu-test-medium-04' | medium     | 4     | t   | 989207584854 |
            # DCC | 'aiu-test-large-04'  | large      | 4     | t   | 989207584854 |
            # DCC | 'aiu-test-large-08'  | large      | 8     | t   | 989207584854 |
            # DCC | 'aiu-test-xlarge-08' | extralarge | 8     | t   | 989207584854 |
            # DCC | 'aiu-test-large-32'  | large      | 32    | t   | 989207584854 |

    Scenario Outline: 3b. DEPLOY ENGINE(S): Connect to the '<project>_private' engine.
        When I run '%connect <project>_private'
		Then I verify the output contains 'activated for user'

        When I run
            """
            SELECT  InfoData AS Version
            FROM    DBC.DBCInfoV
            WHERE   InfoKey = 'VERSION';
            """
        Then I save the output matching '\d\d\..*\.\d\d' as result ENGINE_VERSION

        Examples:
            | project            |
            | aiu-test-small-01  |
            | aiu-test-medium-02 |
            # DCC | aiu-test-small-02  |
            # DCC | aiu-test-medium-04 |
            # DCC | aiu-test-large-04  |
            # DCC | aiu-test-large-08  |
            # DCC | aiu-test-xlarge-08 |
            # DCC | aiu-test-large-32  |

    Scenario Outline: 4a. Disconnect the <project>_private' engine...
        Given I am connected to Jupyter on stack context.properties.stack_name
        When I run '%disconnect <project>_private'

        Examples:
            | project            |
            | aiu-test-small-01  |
            | aiu-test-medium-02 |
            # DCC | aiu-test-small-02  |
            # DCC | aiu-test-medium-04 |
            # DCC | aiu-test-large-04  |
            # DCC | aiu-test-large-08  |
            # DCC | aiu-test-xlarge-08 |
            # DCC | aiu-test-large-32  |

    Scenario Outline: 4b. Suspend the <project> engine...
        When I run '%project_engine_suspend project=<project>'

        Examples:
            | project              |
            | 'aiu-test-small-01'  |
            | 'aiu-test-medium-02' |
            # DCC | 'aiu-test-small-02'  |
            # DCC | 'aiu-test-medium-04' |
            # DCC | 'aiu-test-large-04'  |
            # DCC | 'aiu-test-large-08'  |
            # DCC | 'aiu-test-xlarge-08' |
            # DCC | 'aiu-test-large-32'  |

    Scenario Outline: 4c. Remove the <project> authorization...
        When I run '%project_auth_delete name=<project>, project=<project>'

        Examples:
            | project              |
            | 'aiu-test-small-01'  |
            | 'aiu-test-medium-02' |
            # DCC | 'aiu-test-small-02'  |
            # DCC | 'aiu-test-medium-04' |
            # DCC | 'aiu-test-large-04'  |
            # DCC | 'aiu-test-large-08'  |
            # DCC | 'aiu-test-xlarge-08' |
            # DCC | 'aiu-test-large-32'  |

    Scenario Outline: 4d. Delete the <project> project.
        When I run '%project_delete project=<project>'

        Examples:
            | project              |
            | 'aiu-test-small-01'  |
            | 'aiu-test-medium-02' |
            # DCC | 'aiu-test-small-02'  |
            # DCC | 'aiu-test-medium-04' |
            # DCC | 'aiu-test-large-04'  |
            # DCC | 'aiu-test-large-08'  |
            # DCC | 'aiu-test-xlarge-08' |
            # DCC | 'aiu-test-large-32'  |
