from http.client import HTTPException

from bs4 import BeautifulSoup
from fastapi import FastAPI, Request
import requests
from urllib.parse import urlparse

app = FastAPI()


@app.post("/categories")
async def get_categories(request: Request):
    try:
        data = await request.json()
        url = data.get("url", "")
        products = scrape_from_category(url)
        return products
    except Exception:
        raise HTTPException()


@app.post("/product")
async def get_product(request: Request):
    try:
        data = await request.json()
        url = data.get("url", "")
        product = scrape_product(url)
        return product
    except Exception:
        raise HTTPException()


class Option:
    def __init__(self, sku, name, valor, image_url):
        self.sku = sku
        self.name = name
        self.valor = float(valor)
        self.image_url = image_url


class Product:
    def __init__(self, title, value, total_products, images, image_main_url, sku, description,
                 options):
        self.title = title
        self.value = value
        self.total_products = total_products
        self.image_main_url = image_main_url
        self.sku = sku
        self.description = description
        self.images = images
        self.options = options


class ProductCategory:
    def __init__(self, title, image, link):
        self.title = title
        self.image = image
        self.link = link


def is_shopify_store(soup):
    script_tags = soup.find_all("script")

    for script_tag in script_tags:
        if "Shopify.cdnHost" in script_tag.text:
            return True

    return False


def scrape_from_category(url):
    products = []

    parsed_url = urlparse(url)

    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    if is_shopify_store(soup):
        titles_tag = soup.find_all("h2", class_="pt-title prod-thumb-title-color")
        images_tag = soup.find_all("img", class_="lazyload")

        for title_tag, image_tag in zip(titles_tag, images_tag):
            if title_tag and image_tag:
                title_text = title_tag.text.strip()
                image_url = image_tag.get("data-src")
                a_tag = title_tag.find("a")
                link = a_tag.get("href")

                product = ProductCategory(title_text, "https:" + image_url, base_url + link)
                products.append(product)

        show_more_button = soup.find("div", class_="show-more")
        if show_more_button:
            next_page_url = show_more_button.find("a").get("href")

            response = requests.get(base_url + "/" + next_page_url)
            soup = BeautifulSoup(response.content, "html.parser")

        titles_tag = soup.find_all("h2", class_="pt-title prod-thumb-title-color")
        images_tag = soup.find_all("img", class_="lazyload")

        for title_tag, image_tag in zip(titles_tag, images_tag):
            if title_tag and image_tag:
                title_text = title_tag.text.strip()
                image_url = image_tag.get("data-src")
                a_tag = title_tag.find("a")
                link = a_tag.get("href")

                product = ProductCategory(title_text, "https:" + image_url, base_url + link)
                products.append(product)

    return products


def scrape_product(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.content, "html.parser")

    if is_shopify_store(soup):

        response = requests.get(url + ".js")

        if response.status_code == 200:
            json_data = response.json()

            title = json_data["title"]
            value = format_value(json_data["price"])
            image_main = "https:" + json_data["featured_image"]
            variants = json_data["variants"]
            first_sku = variants[0]["sku"]
            description = format_description(json_data["description"])

            images = set()
            options = []

            for variant in variants:
                sku = variant["sku"]
                name = variant["title"]
                valor = format_value(variant["price"])
                img_url = variant["featured_image"]["src"]

                if img_url not in images:
                    images.add(img_url)

                option = Option(sku, name, valor, img_url)
                options.append(option)

            product = Product(title, value, len(variants), images, image_main,
                              first_sku, description, options)

            return product

        return None


def format_value(value):
    return value / 100


def format_description(description_html):
    soup = BeautifulSoup(description_html, "html.parser")

    text = soup.get_text(separator="\n", strip=True)

    paragraphs = soup.find_all('p')
    for paragraph in paragraphs:
        text = text.replace(str(paragraph), f"{paragraph.get_text(strip=True)}\n")

    text = text.replace('\n', ' ').replace('\r', '')

    return text

'''
def get_total_products_available(variants):
    total_products = 0

    for variant in variants:
        if variant["available"]:
            total_products += 1

    return total_products
'''