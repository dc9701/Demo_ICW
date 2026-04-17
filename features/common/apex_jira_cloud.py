"""Support for Jira interactions to create & update cards to show project progress."""
from json import loads as json_loads
from typing import Dict, List
from os import environ as os_environ
import requests
import logging
from sys import stdout
import time
import base64

from framework.apex_constants import (
    LOG_FORMAT, NAME_FIELD, FIELDS, STATUS_FIELD, CLIENT_ID, CLIENT_SECRET,
    ATLASSIAN_CLIENT_ID, ATLASSIAN_CLIENT_SECRET,
    JIRA_SERVER_ENV, ATLASSIAN_USERNAME, ATLASSIAN_PASSWORD, XRAY_ENDPOINT, XRAY_AUTH_ENDPOINT,
    IN_PROGRESS_TRANS_ID_CLOUD, DONE_TRANS_ID_CLOUD,
    STARTED_ON, FINISHED_ON, TEST_EXEC_KEY, CUSTOM_FIELDS, KEY_FIELD, EXECUTOR_FIELD, TEST_CASE_KEY_FIELD,
)
from framework.apex_jira_cloud_queries import (
    ADD_TEST_CASES_TO_TEST_PLAN_MUTATION, CREATE_TEST_EXECUTION_MUTATION,
    ADD_TEST_EXECUTION_TO_TEST_PLAN_MUTATION, GET_TEST_PLAN_QUERY, GET_MATCHING_TEST_PLANS_QUERY,
    GET_TEST_EXECUTION_FROM_TEST_PLAN_QUERY, GET_TEST_PLANS_BY_RELEASE_VERSION_QUERY, GET_TEST_RUN_BY_ID_QUERY,
    GET_TEST_CASE_QUERY, CREATE_TEST_CASE_MUTATION_NO_ASSIGNEE, UPDATE_TEST_RUN_DINAMIC,
    GET_EXECUTION_RECORDS_QUERY, GET_ASSIGNED_TEST_CASES_FOR_EXECUTION_QUERY, GET_ALL_RESULTS_FOR_PLAN_QUERY,
    GET_TEST_PLAN_ID_QUERY, GET_TEST_EXECUTION_ID_QUERY, ADD_TESTS_TO_TEST_EXECUTION_MUTATION,
    GET_TEST_EXECUTION_TESTS_QUERY, REMOVE_TESTS_FROM_TEST_EXECUTION_MUTATION, GET_EXECUTION_RESULTS_QUERY,
    GET_TEST_ID_FROM_TEST_KEY_QUERY, GET_TEST_RUN_ID_QUERY, UPDATE_TEST_RESULT_STATUS_MUTATION,
    ADD_TEST_ENVIRONMENT_TO_TEST_EXECUTION_MUTATION, CREATE_TEST_PLAN_MUTATION_DINAMIC, ADD_EVIDENCE_TEST_RUN
)

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport, TransportServerError
from gql.transport.exceptions import TransportQueryError
import json

TEST_RUN_BY_ID = 'getTestRunById'
EXECUTED_BY_ID = 'executedById'
TEST_EXECUTION = 'testExecution'
TEST_FIELD = 'test'
JIRA_FIELD = 'jira'
FIRST_ENTRY = 0
RESULT = "status"
SUMMARY = "summary"
TEST_RUN_ID = 'test_run_id'
TEST_KEY = "testKey"
MAX_RETRIES = 3
PAUSE_BETWEEN_TRIES = 2
JIRA_API_PATH = 'rest/api/3'
DATA_TYPE = 'application/json'
DEFAULT_HEADERS = {
    "Content-Type": DATA_TYPE,
    "Accept": DATA_TYPE
}

JIRA_SERVER_TEST_TYPE_FIELD_NAME_FIELD = 'customfield_17050'
GENERIC_TEST_TYPE = "Generic"
APEX_LABEL = "APEX"
JOB_FOLDER_ID = 'JOB FOLDER FIELD ID'
JOB_FOLDER_NAME = 'JOB FOLDER FIELD NAME'
JIRA_ISSUE_URL = '{jira_server}/browse/{issue_id}'
JIRA_TEST_EXECUTION_URL = '<h2><a href="{test_execution_link}">Group {group_id}: {test_execution_id}</a></h2>'
XRAY_BEARER_TOKEN = 'XRAY_BEARER_TOKEN'  # noqa: S105 - Not a password, only env var


class JiraException(requests.exceptions.HTTPError):
    """Exception in our connection to Jira."""


class JiraConnection:
    """Support creating test plan, test case, test run/test result in Jira/Zephyr Scale implementation."""

    def __init__(self, project):
        self.server = os_environ[JIRA_SERVER_ENV]
        self.jira_rest_url = f"{self.server}/{JIRA_API_PATH}"
        self.xray_graphql_endpoint = XRAY_ENDPOINT
        self.user = os_environ[ATLASSIAN_USERNAME]
        self.password = os_environ[ATLASSIAN_PASSWORD]
        self.client_id = os_environ[ATLASSIAN_CLIENT_ID]
        self.client_secret = os_environ[ATLASSIAN_CLIENT_SECRET]
        self.set_project(project)

        stdout_handler = logging.StreamHandler(stdout)
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=[stdout_handler])
        self.logger = logging.getLogger(__name__)
        self._xray_client = None

    def set_project(self, project):
        """Set the project to use for Jira interactions."""
        self.project = project.replace('"', "'")

    @property
    def xray_client(self):
        """Lazy-loaded creation of xray client."""
        if not self._xray_client:
            bearer = os_environ.get(XRAY_BEARER_TOKEN)
            if not bearer:
                authentication_value = {
                    CLIENT_ID: self.client_id,
                    CLIENT_SECRET: self.client_secret
                }
                bearer = self._send_to_jira(XRAY_AUTH_ENDPOINT, body=authentication_value, method=requests.post)
                os_environ[XRAY_BEARER_TOKEN] = str(bearer)
            headers = {"Authorization": f"Bearer {bearer}"}
            transport = AIOHTTPTransport(url=self.xray_graphql_endpoint, headers=headers)
            self._xray_client = Client(transport=transport, fetch_schema_from_transport=False, execute_timeout=120)
        return self._xray_client

    @staticmethod
    def _build_transition_body(status: str):
        """
        Build body of request to transition a Jira to the given status by ID.

        :param status: workflow status ID to transition to
        :return: Request body
        """
        return {
            'transition': {'id': status}
        }

    def create_test_plan(self, name: str, objective: str, job_folder_link: str, assignee: str, label: str = APEX_LABEL,
                         ) -> str:
        """
        Add a test plan to Jira Cloud project.

        Note: This call is typically followed by a call to assign the test cases to a test plan
        :param name: Name of the test plan
        :param objective: Objective of the test plan
        :param label: Label for the test plan so it is easier to find in Jira Cloud
        :param job_folder_link: Link to the Jenkins parent plan folder
        :param assignee: assignee of the test plan card
        :return: Key for the test plan
        """
        self.set_job_folder_field_ids()
        assigned_user = self._get_id_user_from_email(assignee)
        jira_json = {
            "fields": {
                "summary": name,
                "description": objective,
                "project": {
                    "key": self.project
                },
                "assignee": {
                    "accountId": assigned_user
                },
                os_environ[JOB_FOLDER_ID]: job_folder_link,
                "labels": [APEX_LABEL if label is None else label]
            }
        }
        parameters = {
            "jira": jira_json
        }
        result = self.execute_query(CREATE_TEST_PLAN_MUTATION_DINAMIC, parameters)
        return result['createTestPlan']['testPlan']['jira']['key']

    def add_test_cases_to_test_plan(self, test_plan_key: str, test_cases_keys: list):
        """
        Adds existing test cases to the test plan Jira issue.

        :param test_plan_key: Test Plan ID (e.g. "QTACT-5")
        :param test_cases_keys: list of strings that contain the Test Case IDs (e.g. "QTACT-4")
        """
        test_plan_key = test_plan_key.replace('"', "'")
        tests_case_ids = self._get_test_case_ids_from_keys(test_cases_keys)
        test_plan_id = str(self._get_test_plan_id_from_key(test_plan_key))
        mutation = ADD_TEST_CASES_TO_TEST_PLAN_MUTATION % (test_plan_id, json.dumps(tests_case_ids))
        return self.execute_query(mutation)

    def create_test_execution(self, name: str, description: str, assignee: str, environment: str = None) -> str:
        """
        Add a test plan to Jira project.

        Note: This call is typically followed by a call to assign the test cases to a test plan
        :param name: Name of the test plan
        :param description: Objective of the test plan
        :param assignee: assignee of the test plan card
        :return: Key for the test plan
        """
        assigned_user = self._get_id_user_from_email(assignee)
        mutation = CREATE_TEST_EXECUTION_MUTATION % (environment, name, description, self.project, assigned_user)
        result = self.execute_query(mutation)
        return result['createTestExecution']['testExecution']['jira']['key']

    def update_test_execution(self, execution_id, add_cases=None, remove_cases=None) -> None:
        """
        Adds existing test cases to the test plan Jira issue.

        :param remove_cases: Cases to remove from the execution; could be None or [].
        :param add_cases: Cases to add to the execution.
        :param execution_id: The execution to update.
        """
        xray_test_execution_id = self._get_test_execution_id_from_key(execution_id)
        if remove_cases:
            id_cases_to_remove = self._get_test_case_ids_from_keys(remove_cases)
            self._remove_tests_from_test_execution(xray_test_execution_id, id_cases_to_remove)
        if add_cases:
            id_cases_to_add = self._get_test_case_ids_from_keys(add_cases)
            self._add_tests_to_test_execution(xray_test_execution_id, id_cases_to_add)

    def update_execution_name(self, execution_key: str, new_execution_name: str):
        """
        Updates the Execution Name in case the execution name changed.

        :param execution_key: ID of the execution record to update
        :param new_execution_name: Replace execution "summary" with this new name.
        :return: None
        """
        end_point = f"{self.jira_rest_url}/issue/{execution_key}"
        body = {
            FIELDS: {
                SUMMARY: new_execution_name
            }
        }
        self._send_to_jira(url=end_point, body=body, method=requests.put)

    def add_test_execution_to_test_plan(self, test_plan_key: str, test_execution_key: str) -> None:
        """
        The GraphQL query to relate a test execution to a test plan.

        test_plan_key: The key of the test plan to which relate the test execution
        test_execution_key: The key of the test execution to relato to the test plan
        """
        test_plan_id = self._get_test_plan_id_from_key(test_plan_key)
        execution_id = self._get_test_execution_id_from_key(test_execution_key)
        mutation = ADD_TEST_EXECUTION_TO_TEST_PLAN_MUTATION % (test_plan_id, execution_id)
        self.execute_query(mutation)

    def add_test_run(self, execution_key: str = None, cases: List[Dict] = None, environment: str = None) -> None:
        """
        Adds a test status & URL to a test execution record for the provided cases.

        :param execution_key: Jira issue ID for the execution record
        :param cases: List of dictionaries (as test cases);
                      Within each test case should be:
                      * key: test case issue ID
                      * build_url: jenkins url to the build that ran/is running
                      * result: one of TO DO, EXECUTING, PASSED, FAILED, ABORTED
                      * EXECUTION_DATE - startedOn
                      * EXECUTION_DURATION ------ Not supported
                      * Execution - finishedOn
                      * EXECUTOR
                      * assignee
        :param environment: string indicating a SINGLE environment
        """
        if environment:
            test_execution_id = self._get_test_execution_id_from_key(test_execution_key=execution_key)
            self._add_test_environment_to_test_execution(test_execution_id=test_execution_id, environment=environment)

        for case in cases:
            if not case.get(TEST_RUN_ID):
                case[TEST_RUN_ID] = self._get_test_run_id(test_case_key=case[TEST_KEY],
                                                          test_execution_key=execution_key)
            self._update_test_result_status(case[TEST_RUN_ID], case[RESULT])
            self._get_test_run_custom_fields_id(case[TEST_RUN_ID])

            # Get all the parameters in the correct string format
            variables, query_params, query = self.get_query_parameters_add_test_run(case)
            string_variables = f"({','.join(variables)})"
            string_query = ','.join(query)

            self.execute_query(
                query_string=UPDATE_TEST_RUN_DINAMIC % (string_variables, string_query),
                params=query_params
            )
            self.logger.info(f"Updated test run of case {case[TEST_KEY]}")

    def _truncate_custom_fields_size(self, case):
        """Xray custom Fields just support 8192 characters, this truncates the value is is more than that."""
        for custom_field in case.get('customFields'):
            if len(custom_field['value']) > 8192:
                custom_field['value'] = custom_field['value'][:8166] + "\n**TRUNCATED FOR LENGTH**"

    def _get_test_run_custom_fields_id(self, test_run_id: str):
        if not os_environ.get('XRAY_BUILD_URL_ID') or not os_environ.get('XRAY_PARAMETERS_ID'):
            query = """
            {
                getTestRunById(id : "%s") {
                    customFields {
                        id
                        name
                    }
                }
            }
            """ % test_run_id
            result = self.execute_query(query)
            custom_fields = result['getTestRunById']['customFields']

            bld_url_id = [custom_field['id'] for custom_field in custom_fields if custom_field['name'] == 'Jenkins Url']
            if bld_url_id:
                os_environ['XRAY_BUILD_URL_ID'] = bld_url_id[0]
            parameters = [custom_field['id'] for custom_field in custom_fields if custom_field['name'] == 'Parameters']
            if parameters:
                os_environ['XRAY_PARAMETERS_ID'] = parameters[0]

    def reset_test_run(self, test_run_id: str) -> None:
        """Resets the test run."""
        mutation = """
            mutation {
                    resetTestRun( id: "%s")
                }
            """ % test_run_id
        self.execute_query(query_string=mutation)

    def get_query_parameters_add_test_run(self, case):
        """Gets the query parameters for adding a test run."""
        variables = []
        query_params = {}
        query = []

        # Get the executor and assignee id
        assignee = case.get('assignee')
        executor = case.get('executor')
        assignee_id = self._get_id_user_from_email(assignee) if assignee else None
        executor_id = self._get_id_user_from_email(executor) if executor and executor != assignee else assignee_id

        if case.get('test_run_id'):
            query.append('id: $id')
            variables.append("$id: String!")
            query_params['id'] = case['test_run_id']

        if case.get('execution_start'):
            query.append('startedOn: $startedOn')
            variables.append("$startedOn: String")
            query_params['startedOn'] = case['execution_start']

        if case.get('execution_finished'):
            query.append('finishedOn: $finishedOn')
            variables.append("$finishedOn: String")
            query_params['finishedOn'] = case['execution_finished']

        if case.get('assignee'):
            query.append('assigneeId: $assigneeId')
            variables.append("$assigneeId: String")
            query_params['assigneeId'] = assignee_id

        if case.get('executor'):
            query.append('executedById: $executedById')
            variables.append("$executedById: String")
            query_params['executedById'] = executor_id

        if case.get('comment'):
            query.append('comment: $comment')
            variables.append("$comment: String")
            query_params['comment'] = case['comment']

        if case.get('customFields'):
            self._truncate_custom_fields_size(case)
            self.set_custom_field(case=case, query=query, query_params=query_params, variables=variables)
        return variables, query_params, query

    @staticmethod
    def set_custom_field(case, query, query_params, variables):
        """
        Sets the custom field part of the query.

        Note: the query, query_params, and variables modified in here will reflect in the parameter from the caller.
        """
        build_url = [custom_field['value'] for custom_field in case['customFields'] if custom_field['id'] == 1]
        parameters = [custom_field['value'] for custom_field in case['customFields'] if custom_field['id'] == 2]
        custom_fields = []
        if build_url:
            custom_fields.append('{id: "%s", value: $build_url}' % os_environ.get('XRAY_BUILD_URL_ID'))
            variables.append("$build_url: JSON")
            query_params['build_url'] = build_url[FIRST_ENTRY]
        if parameters:
            custom_fields.append('{id: "%s", value: $parameters}' % os_environ.get('XRAY_PARAMETERS_ID'))
            variables.append("$parameters: JSON")
            query_params['parameters'] = parameters[FIRST_ENTRY]
        if custom_fields:
            query.append('customFields: [%s],' % ','.join(custom_fields))

    def get_test_run(self, test_run_id: str) -> dict:
        """Get the test run from run_id, return dict."""
        query = GET_TEST_RUN_BY_ID_QUERY % test_run_id
        return self.execute_query(query)[TEST_RUN_BY_ID]

    def create_test_case(self, name: str, objective: str, assignee: str = None, type: str = GENERIC_TEST_TYPE,
                         label: str = APEX_LABEL) -> str:
        """
        Add a test case to Jira project.

        Not used much as this is an activity that occurs before test planning.

        :param name:        Name of the test case
        :param objective:   Objective of the test case
        :param assignee:       Owner of the test case card

        :return:            Key for the test case

        Note: Not includes TEST_REPOSITORY_FIELD as in the apex_jira library as a parameter
        because it is not supported as a field in Jira Cloud
        """
        jira_json = {
            "fields": {
                "summary": name,
                "description": objective,
                "project": {
                    "key": self.project
                },
                "labels": [APEX_LABEL if label is None else label]
            }
        }

        if assignee:
            assigned_user = self._get_id_user_from_email(assignee)
            jira_json['fields']['assignee'] = {'accountId': assigned_user}

        params = {
            "testType": type,
            "jira": jira_json
        }

        result = self.execute_query(CREATE_TEST_CASE_MUTATION_NO_ASSIGNEE, params)
        return result['createTest']['test']['jira']['key']

    def get_test_case(self, test_case_id: str) -> dict:
        """
        Get test case info from Jira.

        :param test_case_id: ID for the test case to get
        :return: Info about the test case

        More specific: Used to retrieve the test type
        """
        query = GET_TEST_CASE_QUERY % (self.project, test_case_id)
        result = self.execute_query(query)

        # Adapted to work as the same output as in the apex_jira.py
        output = result['getTests']['results'][0]['testType']['name']
        return {'fields': {JIRA_SERVER_TEST_TYPE_FIELD_NAME_FIELD: {"value": output}}}

    def get_execution_result(self, test_execution_key: str, test_case_key: str) -> dict:
        """
        Get the result for a particular test cycle/test case combination.

        :param test_execution_key: Test cycle to retrieve from.
        :param test_case_key: Test case id for which to limit the results
        :return: list of execution records
        """
        test_run_id = self._get_test_run_id(test_case_key=test_case_key, test_execution_key=test_execution_key)
        if test_run_id:
            result = self.get_test_run(test_run_id=test_run_id)
            test_run_result = {
                EXECUTOR_FIELD: self.get_email_from_user_id(result[EXECUTED_BY_ID]),
                STATUS_FIELD: result[STATUS_FIELD][NAME_FIELD],
                STARTED_ON: result[STARTED_ON],
                FINISHED_ON: result[FINISHED_ON],
                TEST_KEY: result[TEST_FIELD][JIRA_FIELD][KEY_FIELD],
                TEST_EXEC_KEY: result[TEST_EXECUTION][JIRA_FIELD][KEY_FIELD],
                CUSTOM_FIELDS: result[CUSTOM_FIELDS]
            }
            return test_run_result
        else:
            return {
                EXECUTOR_FIELD: '',
                STATUS_FIELD: 'TODO',
                STARTED_ON: '',
                FINISHED_ON: '',
                TEST_KEY: test_case_key,
                TEST_EXEC_KEY: test_execution_key
            }

    def get_execution_results(self, test_execution_id: str) -> list[dict]:
        """
        Get all the execution results for a test execution.

        :param test_execution_id: Test cycle to retrieve from.
        :return: list of execution records
        """
        query = GET_EXECUTION_RESULTS_QUERY % (self.project, test_execution_id)
        test_runs = self.execute_query(query)['getTestExecutions']['results'][0]['testRuns']['results']
        test_runs_results = []
        for test_run in test_runs:
            test_run_result = {
                "executedBy": self.get_email_from_user_id(test_run['executedById']),
                "status": test_run['status']['name'],
                "startedOn": test_run['startedOn'],
                "finishedOn": test_run['finishedOn'],
                "testKey": test_run['test']['jira']['key'],
                "testExecKey": test_run['testExecution']['jira']['key'],
                "customFields": test_run['customFields']
            }
            test_runs_results.append(test_run_result)
        return test_runs_results

    def get_execution_records(self, test_plan_id: str) -> dict:
        """
        Get all the executions for a particular test plan id.

        :param test_plan_id: the tst plan id to get executions for
        :return: dict of execution records, execution number group

        Used to check the group number of the summary
        """
        query = GET_EXECUTION_RECORDS_QUERY % (self.project, test_plan_id)
        result = self.execute_query(query)
        executions = result['getTestPlans']['results'][0]['testExecutions']['results']
        for execution in executions:
            execution['group_id'] = int(execution['jira']['summary'].split(' ')[1].split('_')[0])
        return executions

    def get_assigned_test_cases_for_execution(self, execution_key: str) -> list:
        """
        Get a list of test case ids for a particular execution record.

        :param execution_key:
        :return: list of test case ids
        """
        query = GET_ASSIGNED_TEST_CASES_FOR_EXECUTION_QUERY % (self.project, execution_key)
        result = self.execute_query(query)
        list_cases = [test['jira']['key'] for test in result['getTestExecutions']['results'][0]['tests']['results']]
        return list_cases

    def get_test_plan(self, test_plan_key: str) -> dict:
        """
        Get test plan data from Jira.

        :param test_plan_key: Jira ID for the test plan to retrieve info
        :return: Info about the test plan

        Only used to get the Jenkins Job folder
        """
        self.set_job_folder_field_ids()
        query = GET_TEST_PLAN_QUERY % (self.project, test_plan_key, os_environ[JOB_FOLDER_ID])
        query_result = self.execute_query(query)
        job_url = query_result['getTestPlans']['results'][0]['jira'][os_environ[JOB_FOLDER_ID]]
        return {"fields": {os_environ[JOB_FOLDER_ID]: job_url}}

    def check_plan_url_does_not_exist(self, plan_url):
        """Raises RuntimeError if the plan URL does not exist."""
        matching_plans = self.get_matching_test_plans(plan_url)
        if matching_plans:
            raise RuntimeError(f"Test Plan already exists. Please remove:\n{matching_plans} from {self.server}")

    def get_matching_test_plans(self, plan_url: str) -> list[str]:
        """Gets the test plans that have a matching test plan url."""
        self.set_job_folder_field_ids()
        plan_url = plan_url.replace('"', "'")
        query = GET_MATCHING_TEST_PLANS_QUERY % (self.project, os_environ[JOB_FOLDER_NAME], plan_url)
        test_plans = self.execute_query(query)
        list_test_plans_keys = [test_plan['jira']['key'] for test_plan in test_plans['getTestPlans']['results']]
        return list_test_plans_keys

    def get_test_execution_from_test_plan(self, test_plan_key: str) -> list[str]:
        """Gets the test execution id for the given test plan id."""
        query = GET_TEST_EXECUTION_FROM_TEST_PLAN_QUERY % (self.project, test_plan_key)
        test_plans = self.execute_query(query)
        return [test_execution['jira']['key'] for test_execution in
                test_plans['getTestPlans']['results'][0]['testExecutions']['results']]

    def get_all_results_for_plan(self, test_plan_id: str) -> dict:
        """Get all the test runs/results for a particular test plan id."""
        query = GET_ALL_RESULTS_FOR_PLAN_QUERY % (self.project, test_plan_id)
        result = self.execute_query(query)
        test_executions = result['getTestPlans']['results'][0]['testExecutions']['results']
        test_plan_result = {test_plan_id: []}
        for test_execution in test_executions:
            for test_run in test_execution['testRuns']['results']:
                test_case_key = self.get_key_from_issue_id(test_run['test']['issueId'])
                test_execution_key = self.get_key_from_issue_id(test_run['testExecution']['issueId'])
                test_run_result = {
                    "status": test_run['status']['name'],
                    TEST_EXEC_KEY: test_execution_key,
                    TEST_CASE_KEY_FIELD: test_case_key,
                    "customFields": test_run['customFields']
                }
                test_plan_result[test_plan_id].append(test_run_result)
        return test_plan_result

    def get_all_plans_for_release(self, fix_version: str) -> list[str]:
        """Gets all the test plans keys for a particular release."""
        query = GET_TEST_PLANS_BY_RELEASE_VERSION_QUERY % (self.project, fix_version)
        test_executions = self.execute_query(query)
        return [test_plan['jira']['key'] for test_plan in test_executions['getTestPlans']['results']]

    def _send_to_jira(self, url: str, body: Dict[str, any] = None, method: callable = requests.get) -> dict:
        """
        Post (create) a new component in Jira with the following parameters.

        :param url: URL for the intended "endpoint"
        :param body: payload to send to Jira
        :param method: Callable method (requests.post, requests.put, or mock)
        :return: Key (str) for the new component
        :raises JiraException: if the return is not OK
        """
        body = body if body else {}
        self.logger.debug(url)
        self.logger.debug(body)
        response = method(url, auth=(self.user, self.password), headers=DEFAULT_HEADERS, json=body)
        if response.ok:
            return json_loads(response.text) if len(response.text) > 0 else {}
        else:
            self.logger.error(response.status_code)
            self.logger.error(f"{url=}")
            self.logger.error(f"{body=}")
            self.logger.error(f"{method}")
            raise JiraException(f"Call to Jira failed | {response.status_code}: {response.text}")

    def mark_test_plan_done(self, test_plan_id: str):
        """Mark test plan and its associated test execution as done."""
        self.change_status_to_done(jira_card_id=test_plan_id)
        test_execution_ids = self.get_test_execution_from_test_plan(test_plan_key=test_plan_id)
        for test_execution_id in test_execution_ids:
            self.change_status_to_done(jira_card_id=test_execution_id)

    def change_status_to_done(self, jira_card_id: str):
        """Safely sets the status of the current Jira Card to Done."""
        status = self.get_object_data(jira_card_id=jira_card_id)[FIELDS][STATUS_FIELD][NAME_FIELD]
        if status == 'Open':
            self.change_status(jira_card_id=jira_card_id, transition=IN_PROGRESS_TRANS_ID_CLOUD)
            self.change_status(jira_card_id=jira_card_id, transition=DONE_TRANS_ID_CLOUD)
        elif status == 'In Progress':
            self.change_status(jira_card_id=jira_card_id, transition=DONE_TRANS_ID_CLOUD)
        elif status == 'Done':
            self.logger.debug(f"Status of {jira_card_id} is {status}")
        else:
            self.logger.error(f"Unexpected status to change for Jira card {jira_card_id}: {status}")

    def change_status(self, jira_card_id: str, transition: str):
        """Transitions the status; used to move status of test plans/executions from Open to Done."""
        self._send_to_jira(
            url=f"{self.jira_rest_url}/issue/{jira_card_id}/transitions",
            body=JiraConnection._build_transition_body(transition),
            method=requests.post
        )

    def get_object_data(self, jira_card_id: str) -> dict:
        """Gets data for given object."""
        end_point = f"{self.jira_rest_url}/issue/{jira_card_id}"
        return self._send_to_jira(url=end_point)

    def _get_id_user_from_email(self, email) -> str:
        """
        Helper method to get the Jira user ID, it uses the JIRA API to get the user info.

        Xray use id's instead of keys with everything that has to do with the GraphQL API.

        Save in environment to not make the same request
        """
        if not os_environ.get(email):
            res = self._send_to_jira(f"{self.jira_rest_url}/user/search?query={email}")
            if res:
                test_exec_id = res[0]["accountId"]
            else:
                test_exec_id = self._get_id_user_from_email(self.user)
                self.logger.warning(f"email {email} not found, changing assignee to {self.user}")
            os_environ[email] = test_exec_id
        return os_environ[email]

    def _get_test_case_ids_from_keys(self, keys_requiered: List[str]) -> list[str]:
        """
        Get the id's of the tests from the GraphQL API.

        To add test to a test case or test execution are based on id's instead of key names.
        """
        list_test_id = []
        for test_key in list(set(keys_requiered)):
            test_id = self._get_test_id_from_test_key(test_key)
            list_test_id.append(test_id)
        return list_test_id

    def _get_test_plan_id_from_key(self, test_plan_key: str) -> str:
        """
        Get the id's of the test_plan from the GraphQL API.

        Save in environment to not make the same request
        """
        if not os_environ.get(test_plan_key):
            test_plan_key = test_plan_key.replace('"', "'")
            query = GET_TEST_PLAN_ID_QUERY % (self.project, test_plan_key)
            result = self.execute_query(query)['getTestPlans']['results'][0]['issueId']
            os_environ[test_plan_key] = result
        return os_environ[test_plan_key]

    def _get_test_execution_id_from_key(self, test_execution_key: str) -> str:
        """
        Get the id's of the test_execution from the GraphQL API.

        Save in environment to not make the same request.
        """
        if not os_environ.get(test_execution_key):
            test_execution_key = test_execution_key.replace('"', "'")
            query = GET_TEST_EXECUTION_ID_QUERY % (self.project, test_execution_key)
            result = self.execute_query(query)['getTestExecutions']['results'][0]['issueId']
            os_environ[test_execution_key] = result
        return os_environ[test_execution_key]

    def _add_tests_to_test_execution(self, execution_id, id_cases_to_add) -> None:
        """
        The function update_test_execution makes both the add and remove of tests.

        This function makes only the part of adding the tests.
        """
        mutation = ADD_TESTS_TO_TEST_EXECUTION_MUTATION % (execution_id, json.dumps(id_cases_to_add))
        self.execute_query(mutation)

    def _remove_tests_from_test_execution(self, execution_id, id_cases_to_remove) -> None:
        """
        The function update_test_execution makes both the add and remove of tests.

        This function makes only the part of removing the tests.
        """
        mutation = REMOVE_TESTS_FROM_TEST_EXECUTION_MUTATION % (execution_id, json.dumps(id_cases_to_remove))
        self.execute_query(mutation)

    def _get_test_execution_tests(self, execution_key: str) -> list[str]:
        """
        Function to get the tests in a test execution.

        Used for testing and assuring that the requiered tests are added or removed from the test execution
        """
        query = GET_TEST_EXECUTION_TESTS_QUERY % (self.project, execution_key)
        result = self.execute_query(query)
        list_tests = [tests['jira']['key'] for tests in result['getTestExecutions']['results'][0]['tests']['results']]
        return list_tests

    def _get_test_id_from_test_key(self, test_case_key: str) -> str:
        """
        Get the test case id given the test case key.

        Save in environment to not make the same request.
        """
        if not os_environ.get(test_case_key):
            query = GET_TEST_ID_FROM_TEST_KEY_QUERY % (self.project, test_case_key)
            result = self.execute_query(query)
            test_case_id = self._get_test_id_from_first_result(result['getTests']['results'])
            os_environ[test_case_key] = test_case_id
        return os_environ[test_case_key]

    @staticmethod
    def _get_test_id_from_first_result(results):
        """Returns the first result's issueId or empty string if there is no result."""
        return results[0]['issueId'] if results else ''

    def _get_test_run_id(self, test_case_key: str, test_execution_key: str) -> str:
        """
        Get the test run id given the test case key and the test execution key.
        """
        try:
            test_case_id = self._get_test_id_from_test_key(test_case_key)
            test_execution_id = self._get_test_execution_id_from_key(test_execution_key)
            query = GET_TEST_RUN_ID_QUERY % (test_case_id, test_execution_id)
            result = self.execute_query(query)
            return result['getTestRun']['id']
        except TransportQueryError:
            return ''

    def _update_test_result_status(self, test_run_id: str, status: str) -> None:
        """
        Part of the add_test_run function.

        The add_test_run function in the Jira Server updates the
        status, environment of the test execution and the execution details.
        In Jira Cloud the update has to be individual: Environment, Status, Ex_Details

        This part refers to the update of the status

        Possible states:
        PASSED, TO DO, FAILED, EXECUTING, ABORTED
        """
        mutation = UPDATE_TEST_RESULT_STATUS_MUTATION % (test_run_id, status)
        self.execute_query(mutation)

    def _add_test_environment_to_test_execution(self, test_execution_id: str, environment: str) -> None:
        mutation = ADD_TEST_ENVIRONMENT_TO_TEST_EXECUTION_MUTATION % (test_execution_id, environment)
        self.execute_query(mutation)

    def set_job_folder_field_ids(self):
        """
        Sets the job folder id and job folder name if they do not exist.

        Used because the id is not deterministic on Jira Cloud instances.
        """
        if not os_environ.get(JOB_FOLDER_ID) or not os_environ.get(JOB_FOLDER_NAME):
            url = f"{self.jira_rest_url}/field"
            request = self._send_to_jira(url=url)
            job_folder_id = [custom_field for custom_field in request if 'Job Folder' in custom_field['name']][0]
            os_environ[JOB_FOLDER_ID] = job_folder_id['id']
            os_environ[JOB_FOLDER_NAME] = job_folder_id['name']

    def execute_query(self, query_string: str, params=None, times=MAX_RETRIES, delay=PAUSE_BETWEEN_TRIES):
        """
        Executes the query with the given parameters.
        """
        query = gql(query_string)
        while times:
            try:
                return self.xray_client.execute(query, variable_values=params, parse_result=False)
            except (TimeoutError):
                time.sleep(delay)
                return self.execute_query(query_string, params, (times - 1), delay)
            except (TransportServerError) as error:
                if error.code == 401:
                    # Call for Xray initialization
                    os_environ.pop(XRAY_BEARER_TOKEN)
                    self._xray_client = None
                    return self.execute_query(query_string, params, (times - 1), delay)
                elif error.code == 502:
                    return self.execute_query(query_string, params, (times - 1), delay)
                raise
        raise

    def issue_url(self, issue_id):  # pragma: no cover
        """Create a URL to the issue."""
        return JIRA_ISSUE_URL.format(jira_server=self.server, issue_id=issue_id)

    def issue_html_link(self, issue_id, group_id):
        """Create an html link to the issue."""
        return JIRA_TEST_EXECUTION_URL.format(jira_server=self.server,
                                              test_execution_id=issue_id,
                                              group_id=group_id,
                                              test_execution_link=self.issue_url(issue_id))

    def remove_job_folder_and_test_plan(self, job_folder_link):
        """
        Modify the summary and the job folder link, future version will delete the issue.
        """
        matching_plans = self.get_matching_test_plans(job_folder_link)
        self.set_job_folder_field_ids()
        for issue_key in matching_plans:
            end_point = f"{self.jira_rest_url}/issue/{issue_key}"
            body = {
                FIELDS: {
                    SUMMARY: "Delete when possible",
                    os_environ[JOB_FOLDER_ID]: "https://delete/pls"
                }
            }
            self._send_to_jira(url=end_point, body=body, method=requests.put)

    def get_email_from_user_id(self, user_id: str):
        """Gets the user's email address from Jira Cloud based on hashed user id."""
        if user_id:
            if not os_environ.get(user_id):
                url = f"{self.jira_rest_url}/user"
                query = {'accountId': user_id}
                response = requests.request(
                    "GET",
                    url=url,
                    headers=DEFAULT_HEADERS,
                    params=query,
                    auth=(self.user, self.password)
                )
                if response.ok:
                    response = json_loads(response.text) if len(response.text) > 0 else {}
                else:
                    self.logger.error(response.status_code)
                    self.logger.error(f"{url=}")
                    self.logger.error(f"{query=}")
                    raise JiraException(f"Call to Jira failed | {response.status_code}: {response.text}")
                os_environ[user_id] = response['emailAddress']
            return os_environ[user_id]
        else:
            return ''

    def get_key_from_issue_id(self, issue_id):
        """Gets the issue key from Jira Cloud based on issue id."""
        if issue_id:
            url = f"{self.jira_rest_url}/issue/{issue_id}"
            response = requests.request(
                "GET",
                url=url,
                headers=DEFAULT_HEADERS,
                auth=(self.user, self.password)
            )
            if response.ok:
                response = json_loads(response.text) if len(response.text) > 0 else {}
            else:
                self.logger.error(response.status_code)
                self.logger.error(f"{url=}")
                raise JiraException(f"Call to Jira failed | {response.status_code}: {response.text}")
            return response['key']
        else:
            return ''

    def _add_evidence_to_test_run(self, test_run_id: str, data: dict) -> None:
        """Add data to 'evidence' in a test run."""
        filename = data['filename']
        mime_type = data['contentType']
        data = data['data']
        query = ADD_EVIDENCE_TEST_RUN
        parameters = {
            'data': data,
            'testRunId': test_run_id,
            'filename': filename,
            'mimeType': mime_type
        }
        self.execute_query(query, params=parameters)

    def attach_file_to_test_run(self, test_run_id: str, file_data: str, file_name: str = 'console.log') -> None:
        """Add file to a test run 'evidence'."""
        file_bytes = base64.b64encode(file_data.encode('utf-8')).decode('utf-8')
        evidence = {}
        evidence['data'] = file_bytes
        evidence['filename'] = file_name
        evidence['contentType'] = 'text/plain'
        self._add_evidence_to_test_run(test_run_id=test_run_id, data=evidence)
