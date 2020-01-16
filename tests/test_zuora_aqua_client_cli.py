from click.testing import CliRunner
from zuora_aqua_client_cli.run_zoql import bearer, describe, query
from unittest.mock import patch, Mock


@patch('zuora_aqua_client_cli.run_zoql.ZuoraClient.get_bearer_token')
def test_bearer(mock_get_bearer_token):
    mock_get_bearer_token.return_value = 'bearer_token'
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('test.ini', 'w+') as config:
            config.write("""
            [test]
            client_id = test_id
            client_secret = test_secret
            """)

        results = runner.invoke(bearer, ['--environment', 'test', '--config-filename', 'test.ini'])

        assert results.output == "Bearer bearer_token\n"
        assert results.exit_code == 0


@patch('zuora_aqua_client_cli.run_zoql.ZuoraClient.get_resource')
@patch('zuora_aqua_client_cli.run_zoql.ZuoraClient.get_bearer_token')
@patch('zuora_aqua_client_cli.run_zoql.ZUORA_RESOURCES', ['TestResource'])
def test_describe(mock_bearer_token, mock_get_resource):
    runner = CliRunner()

    mock_get_resource.return_value = """<?xml version="1.0" encoding="UTF-8"?>
    <object>
    <name>TestResource</name>
    <label>TestRource</label>
    <fields>
      <field>
         <name>Test</name>
         <label>Test</label>
      </field>
    </fields>
    <related-objects>
    </related-objects>
    </object>
    """

    with runner.isolated_filesystem():
        with open('test.ini', 'w+') as config:
            config.write("""
            [test]
            client_id = test_id
            client_secret = test_secret
            """)
        results = runner.invoke(describe, ['--environment', 'test', '--config-filename', 'test.ini', 'TestResource'])

        assert results.output == 'TestRource\n  Test - Test\nRelated Objects\n'
        assert results.exit_code == 0


@patch('zuora_aqua_client_cli.run_zoql.ZuoraClient.get_file_content')
@patch('zuora_aqua_client_cli.run_zoql.ZuoraClient.poll_job')
@patch('zuora_aqua_client_cli.run_zoql.ZuoraClient.start_job')
@patch('zuora_aqua_client_cli.run_zoql.ZuoraClient.set_headers')
@patch('zuora_aqua_client_cli.run_zoql.ZuoraClient.get_bearer_token')
def test_query_string(mock_bearer, mock_set_headers, mock_start_job, mock_poll_job, mock_get_file_content):
    runner = CliRunner()

    mock_headers = Mock()
    mock_set_headers.return_value = mock_headers
    mock_start_job.return_value = 'job_url'
    mock_poll_job.return_value = 'file_url'
    mock_get_file_content.return_value = 'Test'

    with runner.isolated_filesystem():
        with open('test.ini', 'w+') as config:
            config.write("""
            [test]
            client_id = test_id
            client_secret = test_secret
            """)
        results = runner.invoke(
            query,
            [
                '--environment', 'test',
                '--config-filename', 'test.ini',
                '--zoql', 'test_string'
            ]
        )

        assert results.output == 'Test\n'
        assert results.exit_code == 0
