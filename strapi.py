import logging
from io import BytesIO
from urllib.parse import urljoin

import requests
from requests.exceptions import ConnectionError, ReadTimeout
from retry import retry


BACKEND_ROOTURL = 'http://localhost:1337/'
API_PATH = '/api/'


logger = logging.getLogger(__file__)


@retry((ReadTimeout, ConnectionError),
       delay=0, max_delay=3600, backoff=2, jitter=1, )
def persistent_request(url, params={}, headers={}):
    logger.debug(f'Send request with {params=} {headers=}')
    response = requests.get(url, params=params, headers=headers, )
    response.raise_for_status()
    logger.debug(f"Получили ответ. {response=}")
    return response


class Strapi():

    def __init__(self, api_token, base_url=BACKEND_ROOTURL, api_path=API_PATH):
        self.api_token = api_token
        self.base_url = base_url
        self.api_url = urljoin(base_url, api_path)

    def get_all_products(self):
        api_url = urljoin(self.api_url, 'products/')
        params = {}
        headers = {'Authorization': f'bearer {self.api_token}'}
        response = persistent_request(api_url, params, headers)
        products = response.json().get('data', [])
        return [
                    (product.get("id"),
                     product.get('attributes', {}).get('title'),)
                    for product in products
               ]

    def get_product(self, product_id):
        api_url = urljoin(self.api_url, f'products/{product_id}')
        params = {'populate': '*'}
        headers = {'Authorization': f'bearer {self.api_token}'}
        response = persistent_request(api_url, params, headers)
        product = response.json().get('data', {}).get('attributes', {})
        title = product.get('title', '')
        description = product.get('description', '')
        price = product.get('price', '')
        img_filepath = (product.get('picture', {}).get('data', {})
                               .get('attributes').get('url'))
        img_url = urljoin(self.base_url, img_filepath)
        response = persistent_request(img_url)
        picture = BytesIO(response.content)
        return title, description, price, picture
