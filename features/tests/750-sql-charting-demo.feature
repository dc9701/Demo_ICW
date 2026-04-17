@uat @aws @azure @full @mkt @sql
# REPORTING ANNOTATIONS
@allure.label.parentSuite:{context.properties.test_results.engine_bom_version}
@allure.label.suite:{context.properties.stack_name}
@allure.label.subSuite:SQL

Feature:  750-sql-charting-demo - Run selected parts of ChartingDemo.ipynb:  Charting and Data Visualization Demo.
    As an:     AI Unlimited user connected to Jupyter on a given stack
    I want to: Run SQL queries in the ChartingDemo notebook
    So I can:  Confirm the project engine DB is performing properly
    .
    # sql-charting-demo.feature
    #
    # Description: Run selected parts of ChartingDemo.ipynb:  Charting and Data Visualization Demo.
    #
    # 1. Setup:
    #   a. Open the specified stack's Jupyter server at context.properties.stack.Tags.AiUnlimitedJupyterURL.
    #   b. Connect to the 'teradatasql' kernel to interact with the AI Unlimited Jupyter server.
    #   c. Open the sql/ChartingDemo.ipynb notbook.
    #
    # 2. SQL Examples:
    #   a. SalesCenter queries.
    #   b. SalesDemo queries.
    #   c. Stock queries.
    #
    # 3. Cleanup the database so the test can run repeatedly.
    #
    # JIRAs:
    #   REGULUS-1298 - Run ChartingDemo notebook (selected queries) on deployed engine

    Scenario: 1. SETUP: Open the project Jupyter notebook and connect to the project engine.
        Given I am connected to Jupyter on stack context.properties.stack_name
        When I open the sql/ChartingDemo notebook
        And I run '%connect {context.properties.connection}'

    Scenario: 2a. SalesCenter queries.
        # TODO: Use notebook command when REGULUS-1305 is fixed
        # When I run the 'CREATE MULTISET TABLE SalesCenter' step
        When I run
            """
            CREATE MULTISET TABLE SalesCenter,
                NO BEFORE JOURNAL,
                NO AFTER JOURNAL,
                CHECKSUM = DEFAULT,
                DEFAULT MERGEBLOCKRATIO
                (Sales_Center_id INTEGER NOT NULL,
                Sales_Center_Name VARCHAR(255) CHARACTER SET LATIN NOT CASESPECIFIC)
            NO PRIMARY INDEX;
            """
        # TODO: Use notebook command when REGULUS-1305 is fixed
        And I run '%dataload DATABASE={context.properties.stack_name}, TABLE=SalesCenter, FILEPATH=sql/data/salescenter.csv'
        And I run the 'SELECT * FROM SalesCenter' step
        Then I verify the output contains '"9999","Redding"'

    Scenario: 3. CLEANUP: Cleanup the database so the test can run repeatedly.
        When I run 'DROP TABLE SalesCenter'
