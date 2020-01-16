import os
import click
import configparser
import xml.etree.ElementTree as ET
from pathlib import Path

from .consts import ZUORA_RESOURCES
from .api import ZuoraClient

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


# TODO: Move config and environment options here, as they are currently duplicated between the commands
@click.group()
def main():
    pass


def read_conf(filename):
    config = configparser.ConfigParser()
    config.read(filename)
    return config


def get_client_data(config, environment):
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
        is_production = config[environment].get('production') == 'true'
        client_id = config[environment]['client_id'],
        client_secret = config[environment]['client_secret'],
    except KeyError:
        environments = ', '.join(config.sections())
        error = f"""
        Environment '{environment}' not found!
        Environments configured: {environments}
        """
        click.echo(click.style(error, fg='red'))
        raise click.ClickException(Errors.environment_not_found)

    return client_id, client_secret, is_production


def read_zoql_file(filename):
    with open(filename, 'r') as f:
        lines = [l.strip() for l in f.readlines()]
        return '\n'.join(lines)


def write_to_output_file(outfile, content):
    with open(outfile, 'w+') as out:
        out.write(content)


@main.command()
@click.argument('resource')
@click.option('-c', '--config-filename', default=DEFAULT_CONFIG_PATH, help='Config file containing Zuora ouath credentials', type=click.Path(exists=False), show_default=True)
@click.option('-e', '--environment', help='Zuora environment to execute on')
def describe(resource, config_filename, environment):
    """ List available fields of Zuora resource """
    if resource not in ZUORA_RESOURCES:
        click.echo(click.style(f"Resource cannot be found '{resource}', available resources:", fg='red'))
        for resource in ZUORA_RESOURCES:
            click.echo(click.style(resource))

        click.echo()
        raise click.ClickException(Errors.resource_not_found)

    config = read_conf(config_filename)
    client_id, client_secret, is_production = get_client_data(config, environment)
    zuora_client = ZuoraClient(client_id, client_secret, is_production)

    response = zuora_client.get_resource(resource)
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
    client_id, client_secret, is_production = get_client_data(config, environment)
    zuora_client = ZuoraClient(client_id, client_secret, is_production)
    click.echo(click.style(zuora_client.headers['Authorization'], fg='green'))


@main.command()
@click.option('-c', '--config-filename', default=DEFAULT_CONFIG_PATH, help='Config file containing Zuora ouath credentials', type=click.Path(exists=False), show_default=True)
@click.option('-z', '--zoql', help='ZOQL file or query to be executed', type=str)
@click.option('-o', '--output', default=None, help='Where to write the output to, default is STDOUT', type=click.Path(), show_default=True)
@click.option('-e', '--environment', help='Zuora environment to execute on')
@click.option('-m', '--max-retries', default=float('inf'), help='Maximum retries for query', type=click.FLOAT)
def query(config_filename, zoql, output, environment, max_retries):
    """ Run ZOQL Query """
    config = read_conf(config_filename)
    client_id, client_secret, is_production = get_client_data(config, environment)
    zuora_client = ZuoraClient(client_id, client_secret, is_production, max_retries)

    # In order to check if file exists, first we check if it looks like a path,
    # by checking if the dirname is valid, then check if the file exists.
    # If we would only check if the file exist, we'd pass the filename as an inline ZOQL query
    if os.path.exists(os.path.dirname(zoql)):
        if os.path.isfile(zoql):
            zoql = read_zoql_file(zoql)
        else:
            click.echo(click.style(f"File does not exist '{zoql}'", fg='red'))
            raise click.ClickException(Errors.file_not_exists)

    try:
        content = zuora_client.query(zoql)
    except ValueError as e:
        click.echo(click.style(str(e), fg='red'))
        raise click.ClickException(Errors.invalid_zoql)
    except TimeoutError:
        error = """
        Max trials exceeded!
        You can increase it by '-m [number of retries]' option.
        If '-m' is not provided it will poll until job is finished.
        """
        click.echo(click.style(error, fg='red'))
        raise click.ClickException(Errors.retries_exceeded)

    # TODO: Make reuqest session instead of 3 separate requests
    # TODO: Pass headers to request session

    if output is not None:
        write_to_output_file(output, content)
    else:
        click.echo(click.style(content, fg='green'))


if __name__ == '__main__':
    main()
