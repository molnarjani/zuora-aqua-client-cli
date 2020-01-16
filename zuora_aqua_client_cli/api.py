import time
import requests


class ZuoraClient(object):
    def __init__(self, client_id, client_secret, is_prod=False, max_retries=float('inf')):
        self.client_id = client_id
        self.client_secret = client_secret
        self.is_prod = is_prod
        self.max_retries = max_retries
        self.base_url = 'https://zuora.com' if self.is_prod else 'https://apisandbox.zuora.com'
        self.base_api_url = 'https://rest.zuora.com' if self.is_prod else 'https://rest.apisandbox.zuora.com'
        self.set_headers()

    def set_headers(self):
        self.bearer_token = self.get_bearer_token()
        self._headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.bearer_token}'
        }

    def get_bearer_token(self):
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        r = requests.post(self.base_api_url + '/oauth/token', data=payload)
        r.raise_for_status()
        bearer_token = r.json()['access_token']
        return bearer_token

    def query(self, zoql):
        self._job_url = self.start_job(zoql)
        self._file_url = self.poll_job()
        self.content = self.get_file_content()

        return self.content

    def start_job(self, zoql):
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
        query_url = self.base_api_url + '/v1/batch-query/'
        r = requests.post(query_url, json=query_payload, headers=self._headers)
        r.raise_for_status()

        try:
            job_id = r.json()['id']
            _job_url = query_url + '/jobs/{}'.format(job_id)
        except KeyError:
            raise ValueError(r.text)

        return _job_url

    def poll_job(self):
        """ Continuously polls the job until done
            Unless max_retries is provided it polls until end of universe
            otherwise tries it `max_retries` times

            # TODO: Change timeout to actual timeout rather than # of times
        """

        status = 'pending'
        trial_count = 0
        while status != 'completed':
            r = requests.get(self._job_url, headers=self._headers)
            r.raise_for_status()
            status = r.json()['status']
            if status == 'completed':
                break

            time.sleep(1)

            trial_count = trial_count + 1
            if trial_count >= self.max_retries:
                raise TimeoutError()

        file_id = r.json()['batches'][0]['fileId']
        file_url = self.base_url + '/apps/api/file/{}'.format(file_id)

        return file_url

    def get_file_content(self):
        r = requests.get(self._file_url, headers=self._headers)
        return r.content.decode("utf-8")

    def get_resource(self, resource):
        r = requests.get(self.base_api_url + f'/v1/describe/{resource}', headers=self._headers)
        r.raise_for_status()
        return r.text
