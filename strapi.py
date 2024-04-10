import logging
from io import BytesIO
from urllib.parse import urljoin

import requests
from requests.exceptions import ConnectionError, ReadTimeout
from retry import retry


BACKEND_ROOTURL = 'http://localhost:1337/'
API_PATH = '/api/'


logger = logging.getLogger(__file__)


class Strapi():

    def __init__(self, api_token, base_url=BACKEND_ROOTURL, api_path=API_PATH):
        self.headers = {'Authorization': f'bearer {api_token}'}
        self.base_url = base_url
        self.api_url = urljoin(base_url, api_path)

    @retry((ReadTimeout, ConnectionError),
           delay=0, max_delay=3600, backoff=2, jitter=1, )
    def read(self, endpoint, params={}):
        api_url = urljoin(self.api_url, endpoint)
        logger.debug(f'Send request {api_url=}')
        response = requests.get(api_url, params=params, headers=self.headers, )
        response.raise_for_status()
        logger.debug(f"Получили ответ. {response=}")
        return response.json()

    @retry((ReadTimeout, ConnectionError),
           delay=0, max_delay=3600, backoff=2, jitter=1, )
    def create(self, endpoint, data={}):
        api_url = urljoin(self.api_url, endpoint)
        logger.debug(f'Send request {api_url=}')
        response = requests.post(api_url, json=data, headers=self.headers, )
        response.raise_for_status()
        logger.debug(f"Получили ответ. {response=}")
        return response.json()

    @retry((ReadTimeout, ConnectionError),
           delay=0, max_delay=3600, backoff=2, jitter=1, )
    def update(self, endpoint, data={}):
        api_url = urljoin(self.api_url, endpoint)
        logger.debug(f'Send request {api_url=}')
        response = requests.put(api_url, json=data, headers=self.headers, )
        response.raise_for_status()
        logger.debug(f"Получили ответ. {response=}")
        return response.json()

    @retry((ReadTimeout, ConnectionError),
           delay=0, max_delay=3600, backoff=2, jitter=1, )
    def delete(self, endpoint,):
        api_url = urljoin(self.api_url, endpoint)
        logger.debug(f'Send request {api_url=}')
        response = requests.delete(api_url, headers=self.headers, )
        response.raise_for_status()
        logger.debug(f"Получили ответ. {response=}")
        return response.json()

    @retry((ReadTimeout, ConnectionError),
           delay=0, max_delay=3600, backoff=2, jitter=1, )
    def get_asset(self, url):
        resource_url = urljoin(self.base_url, url)
        logger.debug(f'Send request {resource_url=}')
        response = requests.get(resource_url)
        response.raise_for_status()
        logger.debug(f"Получили ответ. {response=}")
        return response.content

    def get_all_products(self):
        api_response = self.read('products')
        products = api_response.get('data', [])
        return [(product.get("id"),
                 product.get('attributes', {}).get('title'), )
                for product in products]

    def get_product(self, product_id):
        params = {'populate': '*'}
        api_response = self.read(f'products/{product_id}', params)
        product = api_response.get('data', {}).get('attributes', {})
        title = product.get('title', '')
        description = product.get('description', '')
        price = product.get('price', '')
        image = (product.get('picture', {}).get('data', {})
                        .get('attributes').get('url'))
        picture = BytesIO(self.get_asset(image))
        return title, description, price, picture

    def get_or_create_cart(self, telegram_id):
        params = {'filters[telegram_id][$eq]': telegram_id}
        api_response = self.read('carts', params)
        cart = api_response.get('data')
        if not cart:
            payload = {"data": {"telegram_id": telegram_id}}
            api_response = self.create('carts', payload)
            cart = api_response.get('data')
        else:
            cart = cart[0]
        return cart.get('id', 0)

    def add_to_cart(self, telegram_id, product_id, quantity):
        cart_id = self.get_or_create_cart(telegram_id)
        payload = {"data": {"product": product_id, "cart": cart_id},
                   "quantity": quantity}
        self.create('cart-products', payload)

    def remove_from_cart(self, cart_product_id):
        self.delete(f'cart-products/{cart_product_id}')

    def get_cart_content(self, telegram_id):
        cart_id = self.get_or_create_cart(telegram_id)
        params = {'populate': 'cart_products.product'}
        api_response = self.read(f'carts/{cart_id}', params)
        api_cart_products = (api_response.get('data', {}).get('attributes', {})
                             .get('cart_products', {}).get('data', []))
        cart_products = [
            (
                cart_product.get('id'),
                cart_product.get('attributes', {}).get('quantity'),
                cart_product.get('attributes', {}).get('product', {})
                            .get('data', {}).get('attributes', {})
                            .get('title'),
                cart_product.get('attributes', {}).get('product', {})
                            .get('data', {}).get('attributes', {})
                            .get('description'),
                cart_product.get('attributes', {}).get('product', {})
                            .get('data', {}).get('attributes', {})
                            .get('price'),
            ) for cart_product in api_cart_products
        ]
        return cart_products

    def save_email(self, telegram_id, email):
        cart_id = self.get_or_create_cart(telegram_id)
        payload = {"data": {"email": email}}
        return self.update(f'carts/{cart_id}', payload)
