import os
import time
import click
import requests

import configparser
import xml.etree.ElementTree as ET

from .consts import ZUORA_RESOURCES
from pathlib import Path

HOME = os.environ['HOME']
DEFAULT_CONFIG_PATH = Path(HOME) / Path('.zacc.ini')

default_environment = None
production = False


class Errors:
    config_not_found = 'ConfigNotFoundError'
    retries_exceeded = 'RetriesExceededError'
    invalid_zoql = 'InvalidZOQLError'
    resource_not_found = 'ResourceNotFound'
    file_not_exists = 'FileNotExists'
    environment_not_found = 'EnvironmentNotFoundError'


def read_conf(filename):
    config = configparser.ConfigParser()
    config.read(filename)
    return config


def get_headers(config, environment):
    global production
    if not config.sections():
        error = f"""
        Configuration not found or empty!
        Please create config in $HOME/.zacc.ini or explicitly pass using the '-c /path/to/config' option!

        Sample configuration:

        # Cli settings
        [zacc]
        # In case the environment is not passed use 'env1' section
        default_environment = env1

        [env1]
        client_id = client1
        client_secret = secret1

        [env2]
        # Uses the production Zuora endpoints instead of the apisandbox
        production = true
        client_id = client2
        client_secret = secret2
        """
        click.echo(click.style(error, fg='red'))
        raise click.ClickException(Errors.config_not_found)

    if environment is None:
        try:
            environment = config.get('zacc', 'default_environment')
        except (configparser.NoOptionError, configparser.NoSectionError):
            error = f"""
        No environment passed, no default environment set!
        Please set a default environment by adding

        [zacc]
        default_environment = <environment_section>

        to your configuration, or pass environment explicity using the '-e' flag.
            """
            click.echo(click.style(error, fg='red'))
            raise click.ClickException(Errors.environment_not_found)

    # Throw away config-only section, as it is not a real environment
    try:
        del config['zacc']
    except KeyError:
        pass

    try:
        production = config[environment].get('production') == 'true'
        bearer_data = {
            'client_id': config[environment]['client_id'],
            'client_secret': config[environment]['client_secret'],
            'grant_type': 'client_credentials'
        }
    except KeyError:
        environments = ', '.join(config.sections())
        error = f"""
        Environment '{environment}' not found!
        Environments configured: {environments}
        """
        click.echo(click.style(error, fg='red'))
        raise click.ClickException(Errors.environment_not_found)

    bearer_token = get_bearer_token(bearer_data)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {bearer_token}'
    }

    return headers


def get_bearer_token(bearer_data):
    url = 'https://rest.zuora.com/oauth/token' if production else 'https://rest.apisandbox.zuora.com/oauth/token'
    r = requests.post(url, data=bearer_data)
    r.raise_for_status()
    bearer_token = r.json()['access_token']
    return bearer_token


def read_zoql_file(filename):
    with open(filename, 'r') as f:
        lines = [l.strip() for l in f.readlines()]
        return '\n'.join(lines)


def start_job(zoql, headers):
    query_url = "https://rest.zuora.com/v1/batch-query/" if production else "https://rest.apisandbox.zuora.com/v1/batch-query/"
    query_payload = {
        "format": "csv",
        "version": "1.1",
        "encrypted": "none",
        "useQueryLabels": "true",
        "dateTimeUtc": "true",
        "queries": [{
            "query": zoql,
            "type": "zoqlexport"
        }]
    }

    r = requests.post(query_url, json=query_payload, headers=headers)
    r.raise_for_status()

    try:
        job_id = r.json()['id']
        job_url = query_url + '/jobs/{}'.format(job_id)
    except KeyError:
        click.echo(click.style(r.text, fg='red'))
        raise click.ClickException(Errors.invalid_zoql)

    return job_url


def poll_job(job_url, headers, max_retries):
    """ Continuously polls the job until done
        Unless max_retries is provided it polls until end of universe
        otherwise tries it `max_retries` times

        # TODO: Change timeout to actual timeout rather than # of times
    """

    click.echo('Polling status...')
    status = 'pending'
    trial_count = 0
    MAX_TRIALS = max_retries
    while status != 'completed':
        r = requests.get(job_url, headers=headers)
        r.raise_for_status()
        status = r.json()['status']
        click.echo(f'Job status: {status}...')
        if status == 'completed':
            break

        time.sleep(1)

        trial_count = trial_count + 1
        if trial_count >= MAX_TRIALS:
            error = """
            Max trials exceeded!
            You can increase it by '-m [number of retries]' option.
            If '-m' is not provided it will poll until job is finished.
            """
            click.echo(click.style(error, fg='red'))
            raise click.ClickException(Errors.retries_exceeded)

    file_id = r.json()['batches'][0]['fileId']
    file_url = 'https://zuora.com/apps/api/file/{}'.format(file_id) if production else 'https://apisandbox.zuora.com/apps/api/file/{}'.format(file_id)

    return file_url


def get_file_content(file_url, headers):
    r = requests.get(file_url, headers=headers)
    return r.content.decode("utf-8")


def write_to_output_file(outfile, content):
    with open(outfile, 'w+') as out:
        out.write(content)


# TODO: Move config and environment options here, as they are currently duplicated between the commands
@click.group()
def main():
    pass


def get_resource(resource, headers):
    url = f'https://rest.zuora.com/v1/describe/{resource}' if production else f'https://rest.apisandbox.zuora.com/v1/describe/{resource}'
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.text


@main.command()
@click.argument('resource')
@click.option('-c', '--config-filename', default=DEFAULT_CONFIG_PATH, help='Config file containing Zuora ouath credentials', type=click.Path(exists=False), show_default=True)
@click.option('-e', '--environment', help='Zuora environment to execute on')
def describe(resource, config_filename, environment):
    """ List available fields of Zuora resource """
    if resource not in ZUORA_RESOURCES:
        click.echo(click.style(f"Resource cannot be found '{resource}', available resources:", fg='red'))
        for resource in ZUORA_RESOURCES:
            click.echo(click.style(resource, fg='green'))

        click.echo()
        raise click.ClickException(Errors.resource_not_found)

    config = read_conf(config_filename)
    headers = get_headers(config, environment)

    response = get_resource(resource, headers)
    root = ET.fromstring(response)
    resource_name = root[1].text
    fields = root[2]
    related_objects = root[3]

    click.echo(click.style(resource_name, fg='green'))
    for child in fields:
        name = ''
        label = ''
        for field in child:
            if field.tag == 'name':
                name = field.text
            elif field.tag == 'label':
                label = field.text

        click.echo(click.style(f'  {name} - {label}', fg='green'))

    click.echo(click.style('Related Objects', fg='green'))
    for child in related_objects:
        name = ''
        label = ''
        object_type = child.items()[0][1].split('/')[-1]
        for field in child:
            if field.tag == 'name':
                name = field.text
            elif field.tag == 'label':
                label = field.text

        click.echo(click.style(f'  {name}<{object_type}> - {label}', fg='green'))


@main.command()
@click.option('-c', '--config-filename', default=DEFAULT_CONFIG_PATH, help='Config file containing Zuora ouath credentials', type=click.Path(exists=False), show_default=True)
@click.option('-e', '--environment', help='Zuora environment to execute on')
def bearer(config_filename, environment):
    """ Prints bearer than exits """
    config = read_conf(config_filename)
    headers = get_headers(config, environment)

    click.echo(click.style(headers['Authorization'], fg='green'))


@main.command()
@click.option('-c', '--config-filename', default=DEFAULT_CONFIG_PATH, help='Config file containing Zuora ouath credentials', type=click.Path(exists=False), show_default=True)
@click.option('-z', '--zoql', help='ZOQL file or query to be executed', type=str)
@click.option('-o', '--output', default=None, help='Where to write the output to, default is STDOUT', type=click.Path(), show_default=True)
@click.option('-e', '--environment', help='Zuora environment to execute on')
@click.option('-m', '--max-retries', default=float('inf'), help='Maximum retries for query', type=click.FLOAT)
def query(config_filename, zoql, output, environment, max_retries):
    """ Run ZOQL Query """
    config = read_conf(config_filename)
    headers = get_headers(config, environment)

    # In order to check if file exists, first we check if it looks like a path,
    # by checking if the dirname is valid, then check if the file exists.
    # If we would only check if the file exist, we'd pass the filename as an inline ZOQL query
    if os.path.exists(os.path.dirname(zoql)):
        if os.path.isfile(zoql):
            zoql = read_zoql_file(zoql)
        else:
            click.echo(click.style(f"File does not exist '{zoql}'", fg='red'))
            raise click.ClickException(Errors.file_not_exists)

    # TODO: Make reuqest session instead of 3 separate requests
    # TODO: Pass headers to request session
    job_url = start_job(zoql, headers)
    file_url = poll_job(job_url, headers, max_retries)
    content = get_file_content(file_url, headers)

    if output is not None:
        write_to_output_file(output, content)
    else:
        click.echo(click.style(content, fg='green'))


if __name__ == '__main__':
    main()
