import os
import time
import click
import requests

import configparser
import xml.etree.ElementTree as ET

from .consts import ZUORA_RESOURCES


def read_conf(filename):
    config = configparser.ConfigParser()
    # TODO: make it configurable (alternatively try to read it from some default places line ~/.zuora_oauth.ini)
    config.read(filename)
    return config


def get_headers(config, environment):
    try:
        bearer_data = {
            'client_id': config[environment]['client_id'],
            'client_secret': config[environment]['client_secret'],
            'grant_type': 'client_credentials'
        }
    except KeyError:
        raise click.ClickException(f"Environment '{environment}' not configured in '{config}'")

    bearer_token = get_bearer_token(bearer_data)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {bearer_token}'
    }

    return headers


def get_bearer_token(bearer_data):
    click.echo('Obtaining bearer token...')
    r = requests.post('https://rest.zuora.com/oauth/token', data=bearer_data)
    r.raise_for_status()
    click.echo(click.style('Success!', fg='green'))
    bearer_token = r.json()['access_token']
    return bearer_token


def read_zoql_file(filename):
    with open(filename, 'r') as f:
        lines = [l.strip() for l in f.readlines()]
        return '\n'.join(lines)


def start_job(zoql, headers):
    query_url = "https://rest.zuora.com/v1/batch-query/"
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
        click.echo(click.style(f"Started job with ID: {job_id}", fg='green'))
    except KeyError:
        click.echo(click.style(r.text, fg='red'))
        raise click.ClickException('Exiting, bye.')

    return job_url


def poll_job(job_url, headers, max_retries):
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
            click.echo(click.style("Max trials exceeded! You can increase it by '-m [number of retries]' option.", fg='red'))
            raise click.ClickException('Exiting, bye.')

    file_id = r.json()['batches'][0]['fileId']
    file_url = 'https://zuora.com/apps/api/file/{}'.format(file_id)

    return file_url


def get_file_content(file_url, headers):
    r = requests.get(file_url, headers=headers)
    return r.text


def write_to_output_file(outfile, content):
    with open(outfile, 'w+') as out:
        out.write(content)


@click.group()
def main():
    pass


def get_resource(resource, headers):
    r = requests.get(f'https://rest.zuora.com/v1/describe/{resource}', headers=headers)
    r.raise_for_status()
    return r.text


@main.command()
@click.argument('resource')
@click.option('-c', '--config-filename', default='zuora_oauth.ini', help='Config file containing Zuora ouath credentials', type=click.Path(exists=True), show_default=True)
@click.option('-e', '--environment', default='local', help='Zuora environment to execute on', show_default=True, type=click.Choice(['prod', 'preprod', 'local']))
def describe(resource, config_filename, environment):
    """ List available fields of Zuora resource """
    if resource not in ZUORA_RESOURCES:
        click.echo(click.style(f"Resource cannot be found '{resource}', available resources:", fg='red'))
        for resource in ZUORA_RESOURCES:
            click.echo(click.style(resource, fg='green'))

        click.echo()
        raise click.ClickException('Exiting, bye.')

    config = read_conf(config_filename)
    headers = get_headers(config, environment)

    response = get_resource(resource, headers)
    root = ET.fromstring(response)
    resource_name = root[1].text
    fields = root[2]
    related_objects = root[3]

    click.echo(resource_name)
    for child in fields:
        name = ''
        label = ''
        for field in child:
            if field.tag == 'name':
                name = field.text
            elif field.tag == 'label':
                label = field.text

        click.echo(f'  {name} - {label}')

    click.echo('Related Objects')
    for child in related_objects:
        name = ''
        label = ''
        object_type = child.items()[0][1].split('/')[-1]
        for field in child:
            if field.tag == 'name':
                name = field.text
            elif field.tag == 'label':
                label = field.text

        click.echo(f'  {name}<{object_type}> - {label}')


@main.command()
@click.option('-c', '--config-filename', default='zuora_oauth.ini', help='Config file containing Zuora ouath credentials', type=click.Path(exists=True), show_default=True)
@click.option('-z', '--zoql', help='ZOQL file or query to be executed', type=str)
@click.option('-o', '--output', default=None, help='Where to write the output to, default is STDOUT', type=click.Path(), show_default=True)
@click.option('-e', '--environment', default='local', help='Zuora environment to execute on', show_default=True, type=click.Choice(['prod', 'preprod', 'local']))
@click.option('-m', '--max-retries', default=10, help='Maximum retries for query', type=click.INT)
def query(config_filename, zoql, output, environment, max_retries):
    """ Run ZOQL Query """
    config = read_conf(config_filename)
    headers = get_headers(config, environment)

    # If a file path is passed, read it else keep it as a string
    if os.path.exists(zoql):
        zoql = read_zoql_file(zoql)

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
