import time
import requests

import configparser


def read_conf():
    config = configparser.ConfigParser()
    # TODO: make it configurable (alternatively try to read it from some default places line ~/.zuora_oauth.ini)
    config.read('zuora_oauth.ini')
    return config

def get_bearer_token(bearer_data):
    print('Obtaining bearer token...')
    r = requests.post('https://rest.zuora.com/oauth/token', data=bearer_data)
    r.raise_for_status()
    print('Success!')
    bearer_token = r.json()['access_token']
    return bearer_token

def read_zoql_file():
    with open('test.zoql', 'r') as f:
        lines = [l.strip() for l in f.readlines()]
        table_name = lines[0]
        zoql = lines[1]

        return table_name, zoql


def start_job(table_name, zoql):
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

def poll_job(job_url):
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

def get_file_content(file_url):
    r = requests.get(file_url, headers=headers)
    return r.text

def write_to_output_file(content):
    output_filename = 'out.csv'
    with open(output_filename, 'w+') as out:
        out.write(content)


if __name__ == '__main__':
    config = read_conf()
    bearer_data = {
        'client_id': config['production']['client_id'],
        'client_secret': config['production']['client_secret'],
        'grant_type': 'client_credentials'
    }

    bearer_token = get_bearer_token(bearer_data)

    headers = {
        'Content-Type': "application/json",
        'Authorization': "Bearer {}".format(bearer_token),
    }

    table_name, zoql = read_zoql_file()

    job_url = start_job(table_name, zoql)
    file_url = poll_job(job_url)
    content = get_file_content(file_url)
    write_to_output_file(content)

    print('Completed!')
