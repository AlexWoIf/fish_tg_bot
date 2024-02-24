import logging

import requests
from requests.exceptions import ConnectionError, ReadTimeout
from retry import retry


STRAPI_BASEURL = 'http://localhost:1337/api/'


logger = logging.getLogger(__file__)


@retry((ReadTimeout, ConnectionError),
       delay=0, max_delay=3600, backoff=2, jitter=1, )
def persistent_request(url, params, headers):
    logger.debug(f'Send request with {params=} {headers=}')
    response = requests.get(url, params=params, headers=headers, )
    response.raise_for_status()
    logger.debug(f"Получили ответ. {response.json()=}")
    return response


class Strapi():

    def __init__(self, api_token, base_url=STRAPI_BASEURL):
        self.api_token = api_token
        self.base_url = base_url

    def get_all_products(self):
        url = f'{self.base_url}products/'
        params = {}
        headers = {'Authorization': f'bearer {self.api_token}'}
        response = persistent_request(url, params, headers)
        products = response.json().get('data', [])
        return products
