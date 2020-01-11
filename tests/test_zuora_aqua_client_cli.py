from click.testing import CliRunner
from zuora_aqua_client_cli.run_zoql import bearer, describe, query
from unittest.mock import patch, Mock, ANY


@patch('zuora_aqua_client_cli.run_zoql.get_bearer_token')
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
        bearer_data = {
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            'grant_type': 'client_credentials'
        }

        results = runner.invoke(bearer, ['--environment', 'test', '--config-filename', 'test.ini'])

        mock_get_bearer_token.assert_called_with(bearer_data)
        assert results.output == "Bearer bearer_token\n"
        assert results.exit_code == 0


@patch('zuora_aqua_client_cli.run_zoql.get_resource')
@patch('zuora_aqua_client_cli.run_zoql.get_bearer_token')
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

        mock_get_resource.assert_called_with('TestResource', ANY)
        assert results.output == 'TestRource\n  Test - Test\nRelated Objects\n'
        assert results.exit_code == 0


@patch('zuora_aqua_client_cli.run_zoql.get_file_content')
@patch('zuora_aqua_client_cli.run_zoql.poll_job')
@patch('zuora_aqua_client_cli.run_zoql.start_job')
@patch('zuora_aqua_client_cli.run_zoql.get_headers')
@patch('zuora_aqua_client_cli.run_zoql.get_bearer_token')
def test_query_string(mock_bearer, mock_get_headers, mock_start_job, mock_poll_job, mock_get_file_content):
    runner = CliRunner()

    mock_headers = Mock()
    mock_get_headers.return_value = mock_headers
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

        mock_start_job.assert_called_with('test_string', mock_headers)
        mock_poll_job.assert_called_with('job_url', mock_headers, ANY)
        mock_get_file_content.assert_called_with('file_url', mock_headers)
        assert results.output == 'Test\n'
        assert results.exit_code == 0
