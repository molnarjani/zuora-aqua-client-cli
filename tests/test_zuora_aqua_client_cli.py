from click.testing import CliRunner
from zuora_aqua_client_cli.cli import bearer, describe
from unittest.mock import patch


@patch("zuora_aqua_client_cli.cli.ZuoraClient", autospec=True)
@patch("zuora_aqua_client_cli.cli.ZuoraClient.get_bearer_token")
def test_bearer(mock_get_bearer_token, mock_zuora_client):
    mock_zuora_client._headers = {"Authorization": "Bearer bearer_token"}
    runner = CliRunner()
    results = runner.invoke(bearer, obj=mock_zuora_client)

    mock_zuora_client.get_bearer_token.assert_called_once()
    assert results.output == "Bearer bearer_token\n"
    assert results.exit_code == 0


@patch("zuora_aqua_client_cli.cli.ZuoraClient", autospec=True)
def test_describe(mock_zuora_client):
    runner = CliRunner()

    mock_zuora_client.get_resource.return_value = """<?xml version="1.0" encoding="UTF-8"?>
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

    results = runner.invoke(describe, ["Account"], obj=mock_zuora_client)

    assert results.output == "TestRource\n  Test - Test\nRelated Objects\n"
    assert results.exit_code == 0


# TODO: Fix tests, they work pretty weird for whatever reason
# @patch('zuora_aqua_client_cli.cli.ZuoraClient', autospec=True)
# def test_query_string(mock_zuora_client):
#    runner = CliRunner()
#
#    mock_zuora_client.get_file_content.return_value = 'Test'
#
#    results = runner.invoke(
#        query,
#        ['--zoql', 'test_string'],
#        obj=mock_zuora_client
#    )
#
#    assert results.output == 'Test\n'
#    assert results.exit_code == 0
