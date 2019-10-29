import time
import click
import requests

import configparser


def read_conf(filename):
    config = configparser.ConfigParser()
    # TODO: make it configurable (alternatively try to read it from some default places line ~/.zuora_oauth.ini)
    config.read(filename)
    return config


def get_bearer_token(bearer_data):
    print('Obtaining bearer token...')
    r = requests.post('https://rest.zuora.com/oauth/token', data=bearer_data)
    r.raise_for_status()
    print('Success!')
    bearer_token = r.json()['access_token']
    return bearer_token


def read_zoql_file(filename):
    with open(filename, 'r') as f:
        lines = [l.strip() for l in f.readlines()]
        table_name = lines[0]
        zoql = lines[1]

        return table_name, zoql


def start_job(table_name, zoql, headers):
    query_url = "https://rest.zuora.com/v1/batch-query/"
    query_payload = {
        "format": "csv",
        "version": "1.1",
        "encrypted": "none",
        "useQueryLabels": "true",
        "dateTimeUtc": "true",
        "queries": [{
            "name": table_name,
            "query": zoql,
            "type": "zoqlexport"
        }]
    }

    r = requests.post(query_url, json=query_payload, headers=headers)
    r.raise_for_status()

    try:
        job_id = r.json()['id']
        job_url = query_url + '/jobs/{}'.format(job_id)
        print('Started job with ID: {}'.format(job_id))
    except KeyError:
        print(r.text)

    return job_url


def poll_job(job_url, headers):
    print('Polling status...')
    status = 'pending'
    trial_count = 0
    MAX_TRIALS = 10
    while status != 'completed':
        r = requests.get(job_url, headers=headers)
        r.raise_for_status()
        status = r.json()['status']
        print('Job status: {}...'.format(status))
        if status == 'completed':
            break

        time.sleep(1)

        trial_count = trial_count + 1
        if trial_count >= MAX_TRIALS:
            raise Exception('max trials exceeded')

    file_id = r.json()['batches'][0]['fileId']
    file_url = 'https://zuora.com/apps/api/file/{}'.format(file_id)

    return file_url


def get_file_content(file_url, headers):
    r = requests.get(file_url, headers=headers)
    return r.text


def write_to_output_file(content):
    output_filename = 'out.csv'
    with open(output_filename, 'w+') as out:
        out.write(content)


@click.command()
@click.option('-c', '--config-filename', default='zuora_oauth.ini', help='Config file containing Zuora ouath credentials', type=click.Path(exists=True), show_default=True)
@click.option('-z', '--zoql', default='input.zoql', help='ZOQL file to be executed', type=click.Path(exists=True), show_default=True)
@click.option('-e', '--environment', default='local', help='Zuora environment to execute on', show_default=True, type=click.Choice(['prod', 'preprod', 'local']))
def main(config_filename, zoql, environment):
    config = read_conf(config_filename)

    try:
        bearer_data = {
            'client_id': config[environment]['client_id'],
            'client_secret': config[environment]['client_secret'],
            'grant_type': 'client_credentials'
        }
    except KeyError:
        raise click.ClickException(f"Environment '{environment}' not configured in '{config_filename}'")

    bearer_token = get_bearer_token(bearer_data)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {bearer_token}'
    }

    table_name, zoql = read_zoql_file(zoql)

    # TODO: Make reuqest session instead of 3 separate requests
    # TODO: Pass headers to request session
    job_url = start_job(table_name, zoql, headers)
    file_url = poll_job(job_url, headers)
    content = get_file_content(file_url, headers)

    write_to_output_file(content)

    print('Completed!')


if __name__ == '__main__':
    main()
