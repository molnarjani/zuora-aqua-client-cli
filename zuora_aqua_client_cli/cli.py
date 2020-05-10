import os
import click
import configparser
import xml.etree.ElementTree as ET
from pathlib import Path

from .consts import ZUORA_RESOURCES
from .api import ZuoraClient

HOME = os.environ["HOME"]
DEFAULT_CONFIG_PATH = Path(HOME) / Path(".zacc.ini")

default_environment = None
production = False


class Errors:
    config_not_found = "ConfigNotFoundError"
    retries_exceeded = "RetriesExceededError"
    invalid_zoql = "InvalidZOQLError"
    resource_not_found = "ResourceNotFound"
    file_not_exists = "FileNotExists"
    environment_not_found = "EnvironmentNotFoundError"
    connection_error = "ConnectionError"


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

        # Optional partner and project fields can be configured per environment, see more on what these do:
        # https://knowledgecenter.zuora.com/Central_Platform/API/AB_Aggregate_Query_API/B_Submit_Query
        # partner = partner
        # Adding project prefix will add only a prefix to the project, so it's easy to identify
        # but will add a timestamp to it so it's not hanging when multiple jobs are executed at the same time
        # project_prefix = myproject
        # If both 'project' and 'project_prefix' is defined, project takes precedence
        # project = myproject

        [env2]
        # Uses the production Zuora endpoints instead of the apisandbox
        production = true
        client_id = client2
        client_secret = secret2
        """
        click.echo(click.style(error, fg="red"))
        raise click.ClickException(Errors.config_not_found)

    if environment is None:
        try:
            environment = config.get("zacc", "default_environment")
        except (configparser.NoOptionError, configparser.NoSectionError):
            error = f"""
        No environment passed, no default environment set!
        Please set a default environment by adding

        [zacc]
        default_environment = <environment_section>

        to your configuration, or pass environment explicitly using the '-e' flag.
            """
            click.echo(click.style(error, fg="red"))
            raise click.ClickException(Errors.environment_not_found)

    # Throw away config-only section, as it is not a real environment
    try:
        del config["zacc"]
    except KeyError:
        pass

    try:
        is_production = config[environment].get("production") == "true"
        client_id = config[environment]["client_id"]
        client_secret = config[environment]["client_secret"]
        partner = config[environment].get("partner")
        project = config[environment].get("project")
        project_prefix = config[environment].get("project_prefix")
    except KeyError:
        environments = ", ".join(config.sections())
        error = f"""
        Environment '{environment}' not found!
        Environments configured: {environments}
        """
        click.echo(click.style(error, fg="red"))
        raise click.ClickException(Errors.environment_not_found)

    return client_id, client_secret, is_production, partner, project, project_prefix


@click.group()
@click.option(
    "-c",
    "--config-filename",
    default=DEFAULT_CONFIG_PATH,
    help="Config file containing Zuora ouath credentials",
    type=click.Path(exists=False),
    show_default=True,
)
@click.option("-e", "--environment", help="Zuora environment to execute on")
@click.option("--project", help="Project name")
@click.option("--project-prefix", help="Project prefix")
@click.option("--partner", help="Partner name")
@click.option(
    "-m", "--max-retries", default=float("inf"), help="Maximum retries for query", type=click.FLOAT,
)
@click.pass_context
def cli(ctx, config_filename, environment, project, project_prefix, partner, max_retries):
    """ Sets up an API client, passes to commands in context """
    config = read_conf(config_filename)
    (
        client_id,
        client_secret,
        is_production,
        default_partner,
        default_project,
        default_project_prefix,
    ) = get_client_data(config, environment)
    try:
        zuora_client = ZuoraClient(
            client_id=client_id,
            client_secret=client_secret,
            is_prod=is_production,
            max_retries=max_retries,
            partner=default_partner if default_partner else partner,
            project=default_project if default_project else project,
            project_prefix=default_project_prefix if default_project_prefix else project_prefix,
        )
    except TimeoutError:
        error = """
        Connection error, please check you network connection!
        Tips:
          - Are you connected to network?
          - Can you resolve 'rest.zuora.com'?
          - Can you reach Zuora servers?
        """
        click.echo(click.style(error, fg="red"))
        raise click.ClickException(Errors.connection_error)
    except ValueError as e:
        error = f"""
        Authentication error, please check you credentials!
        Message from Zuora:
            {e.__context__.response.text}
        """

        click.echo(click.style(error, fg="red"))
        raise click.ClickException(Errors.connection_error)

    ctx.obj = zuora_client


def read_zoql_file(filename):
    with open(filename, "r") as f:
        return f.read().split("\n\n")


def write_to_output_file(outfile, content):
    with open(outfile, "w+") as out:
        out.write("\n".join(content))


@cli.command()
@click.pass_obj
@click.argument("resource")
def describe(zuora_client, resource):
    """ List available fields of Zuora resource """
    if resource not in ZUORA_RESOURCES:
        click.echo(click.style(f"Resource cannot be found '{resource}', available resources:", fg="red"))
        for resource in ZUORA_RESOURCES:
            click.echo(click.style(resource))

        click.echo()
        raise click.ClickException(Errors.resource_not_found)

    response = zuora_client.get_resource(resource)
    root = ET.fromstring(response)
    resource_name = root[1].text
    fields = root[2]
    related_objects = root[3]

    click.echo(click.style(resource_name, fg="green"))
    for child in fields:
        name = ""
        label = ""
        for field in child:
            if field.tag == "name":
                name = field.text
            elif field.tag == "label":
                label = field.text

        click.echo(click.style(f"  {name} - {label}", fg="green"))

    click.echo(click.style("Related Objects", fg="green"))
    for child in related_objects:
        name = ""
        label = ""
        object_type = child.items()[0][1].split("/")[-1]
        for field in child:
            if field.tag == "name":
                name = field.text
            elif field.tag == "label":
                label = field.text

        click.echo(click.style(f"  {name}<{object_type}> - {label}", fg="green"))


@cli.command()
@click.pass_obj
def bearer(zuora_client):
    """ Prints bearer than exits """
    click.echo(click.style(zuora_client._headers["Authorization"], fg="green"))


@cli.command()
@click.pass_obj
@click.argument("zoql")
@click.option(
    "-o",
    "--output",
    default=None,
    help="Where to write the output to, default is STDOUT",
    type=click.Path(),
    show_default=True,
)
def query(zuora_client, zoql, output):
    """ Run ZOQL Query

        :arg
            - zoql: Filename or inline query string

            as inline query:
            `zacc query "select ... from ..."` - query is read as inline query, argument is passed to query as is

            as path:
            `zacc query ~/test.zql`
            `zacc query test.zql`
            `zacc query /tmp/test.zql`

            File can contain on or more queries separated with 1 empty line between 2 queries

        :param
            -- output: output filename to write the file to
            -- max-retries: after how many retries to stop polling (if the query takes too long)


    """

    # In order to check if file exists, first we check if it looks like a path,
    # by checking if the dirname is valid, then check if the file exists.
    # If we would only check if the file exist, we'd pass the filename as an inline ZOQL query
    # Length is checked because it can cause OS Error if its too long, see: https://github.com/molnarjani/zuora-aqua-client-cli/issues/38
    if len(zoql) < 255 and (os.path.exists(os.path.dirname(zoql)) or Path(Path.cwd() / zoql).exists()):
        if os.path.isfile(zoql):
            zoql = read_zoql_file(zoql)
        else:
            click.echo(click.style(f"File does not exist '{zoql}'", fg="red"))
            raise click.ClickException(Errors.file_not_exists)

    try:
        # Transform to list of one element if it's an inline query
        zoql = zoql if isinstance(zoql, list) else [zoql]

        content = zuora_client.query(zoql)
    except ValueError as e:
        click.echo(click.style(str(e), fg="red"))
        raise click.ClickException(Errors.invalid_zoql)
    except TimeoutError:
        error = """
        Max trials exceeded!
        You can increase it by '-m [number of retries]' option.
        If '-m' is not provided it will poll until job is finished.
        """
        click.echo(click.style(error, fg="red"))
        raise click.ClickException(Errors.retries_exceeded)

    # TODO: Make reuqest session instead of 3 separate requests
    # TODO: Pass headers to request session

    if output is not None:
        write_to_output_file(output, content)
    else:
        click.echo(click.style("\n".join(content), fg="green"))


if __name__ == "__main__":
    cli()
