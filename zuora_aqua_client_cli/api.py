import time
from datetime import datetime

import requests


class ZuoraClient(object):
    def __init__(
        self,
        client_id,
        client_secret,
        is_prod=False,
        max_retries=float("inf"),
        project="",
        project_prefix="",
        partner="",
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.is_prod = is_prod
        self.max_retries = max_retries
        self.project = project
        self.project_prefix = project_prefix
        self.partner = partner
        self.base_url = "https://zuora.com" if self.is_prod else "https://apisandbox.zuora.com"
        self.base_api_url = "https://rest.zuora.com" if self.is_prod else "https://rest.apisandbox.zuora.com"
        self.set_headers()

    def set_headers(self):
        self.bearer_token = self.get_bearer_token()
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
        }

    def get_bearer_token(self):
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        try:
            r = requests.post(self.base_api_url + "/oauth/token", data=payload)
            r.raise_for_status()
            bearer_token = r.json()["access_token"]
        except requests.exceptions.ConnectionError as e:
            # raise more generic error so CLI does not have to know about implementations of API
            raise TimeoutError(e)
        except requests.exceptions.HTTPError as e:
            raise ValueError(e)
        return bearer_token

    def query(self, zoql):
        self._job_url = self.start_job(zoql)
        self._file_ids = self.poll_job()
        self.content = []
        for file_id in self._file_ids:
            self.content.append(self.get_file_content(file_id))

        return self.content

    def start_job(self, queries):
        query_payload = {
            "format": "csv",
            "version": "1.1",
            "encrypted": "none",
            "useQueryLabels": "true",
            "dateTimeUtc": "true",
            "queries": [{"query": query, "type": "zoqlexport"} for query in queries],
        }

        if self.partner:
            query_payload["partner"] = self.partner

        if self.project_prefix:
            query_payload["project"] = "{prefix}_{timestamp}".format(
                prefix=self.project_prefix, timestamp=datetime.now()
            )

        if self.project:
            query_payload["project"] = self.project

        query_url = self.base_api_url + "/v1/batch-query/"
        r = requests.post(query_url, json=query_payload, headers=self._headers)
        r.raise_for_status()

        try:
            job_id = r.json()["id"]
            _job_url = query_url + "/jobs/{}".format(job_id)
        except KeyError:
            raise ValueError(r.text)

        return _job_url

    def poll_job(self):
        """ Continuously polls the job until done
            Unless max_retries is provided it polls until end of universe
            otherwise tries it `max_retries` times

            # TODO: Change timeout to actual timeout rather than # of times
        """

        status = "pending"
        trial_count = 0
        while status != "completed":
            r = requests.get(self._job_url, headers=self._headers)
            r.raise_for_status()
            status = r.json()["status"]
            if status == "completed":
                break

            time.sleep(1)

            trial_count += 1
            if trial_count >= self.max_retries:
                raise TimeoutError()

        return map(lambda batch: batch["fileId"], r.json()["batches"])

    def get_file_content(self, file_id):
        file_url = self.base_url + "/apps/api/file/{}".format(file_id)
        r = requests.get(file_url, headers=self._headers)
        return r.content.decode("utf-8")

    def get_resource(self, resource):
        r = requests.get(self.base_api_url + f"/v1/describe/{resource}", headers=self._headers)
        r.raise_for_status()
        return r.text
