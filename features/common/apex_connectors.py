"""
Class to simplify connections to main APEX-specific external servers & services (Confluence, Jira, Jenkins, etc.).
"""

from os import environ
from framework.apex_constants import (
    USER_NAME, USER_PASSWORD,
    GITHUB_USERNAME, DEFAULT_JIRA_PROJECT,
    GITHUB_PASSWORD,
    SECRETS_MANAGER_ENDPOINT,
)
from framework.apex_jenkins import JenkinsConnection
from framework.apex_jira_cloud import JiraConnection
from framework.apex_confluence import ConfluenceConnection
from framework.apex_github import GitHubConnection
from framework.apex_storage import ApexDatabase, QTA_SERVER, QTA_USER_NAME as DB_USER, QTA_USER_PASSWORD as DB_PASSWORD
from framework.config import ApexConfig, DEFAULT_CONFIG
from framework.apex_secrets_manager import SecretsManagerConnection


class Connectors:
    """Generic class with connection options for various builders and tools."""

    def __init__(self, jenkins_server: str,
                 jira_project=DEFAULT_JIRA_PROJECT,
                 config_type=DEFAULT_CONFIG,
                 test_plan_id=None):
        self._jenkins_server = jenkins_server
        self._jenkins = None
        self._jira = None
        self._apex_storage = None
        self._confluence = None
        self._github = None
        self._cred_service = None
        self._secrets_manager = None
        self._test_plan_id = test_plan_id
        self._jira_project = None
        self.set_jira_project(jira_project)
        self.config = ApexConfig(config_type)

    @property
    def jenkins_server(self):
        """Return the jenkins server URL (basic part)."""
        return self._jenkins_server

    @property
    def jenkins(self):
        """Return a connection to the jenkins server."""
        if not self._jenkins:
            self._jenkins = JenkinsConnection(server=self._jenkins_server,
                                              user=environ[USER_NAME],
                                              password=environ[USER_PASSWORD])
        return self._jenkins

    @property
    def jira(self):
        """Return a connection to the jira server."""
        if not self._jira:
            self._jira = JiraConnection(project=self._jira_project)
        return self._jira

    def set_jira_project(self, jira_project):
        """Set the jira project."""
        self._jira_project = jira_project

    @property
    def confluence(self):
        """Return a connection the confluence server."""
        if not self._confluence:
            self._confluence = ConfluenceConnection()
        return self._confluence

    @property
    def github(self):
        """Return a connection to GitHub Enterprise server."""
        if not self._github:
            self._github = GitHubConnection(username=environ[GITHUB_USERNAME],
                                            password=environ[GITHUB_PASSWORD])
        return self._github

    @property
    def apex_storage(self):
        """Return a connection to the ApexDatabase server & database."""
        if not self._apex_storage:
            self._apex_storage = ApexDatabase(server=QTA_SERVER,
                                              user=environ[DB_USER],
                                              password=environ[DB_PASSWORD])
        return self._apex_storage

    @property
    def secrets_manager(self):
        """Return a connection to the secrets manager server."""
        if not self._secrets_manager:
            self._secrets_manager = SecretsManagerConnection(server=SECRETS_MANAGER_ENDPOINT,
                                                             username=environ[USER_NAME],
                                                             password=environ[USER_PASSWORD])
        return self._secrets_manager
