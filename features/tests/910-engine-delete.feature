@teardown @aws @azure @full
# REPORTING ANNOTATIONS
@allure.label.parentSuite:{context.properties.test_results.engine_bom_version}
@allure.label.suite:{context.properties.stack_name}
@allure.label.subSuite:TEARDOWN

Feature:  910-engine-delete - Deletes a previously-deployed project engine.
    As an:     AI Unlimited user connected to Jupyter on a given stack
    I want to: Delete a previously-deployed engine (aka, CE cluster) for my project
    So I can:  Re-run the engine deployment tests in the future
    .
    # engine-delete.feature
    #
    # Description: Deletes a previously-deployed project engine and removes engine info from the stack definition file.
    #
    #   - Suspend the engine, and remove the artifacts required to deploy it so the test may be run repeatedly.
    #
    # JIRAs:
    #   REGULUS-1173 - Autotests for Jupyter CE cluster deployment (AWS)

    Scenario: 1. Disconnect...
        Given I am connected to Jupyter on stack context.properties.stack_name
        When I run '%disconnect {context.properties.connection}'

    Scenario: 2. Suspend the engine...
        When I run '%project_engine_suspend project={context.properties.stack_name}'

    Scenario: 3. Remove the project auth object...
        When I run '%project_auth_delete name={context.properties.stack_name}, project={context.properties.stack_name}'

    Scenario: 4. Then delete the project so the test may be run anew.
        When I run '%project_delete project={context.properties.stack_name}'
