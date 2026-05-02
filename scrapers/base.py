import logging

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


class BaseScraper:
    def __init__(self, fuente):
        self.fuente = fuente
        self.url = fuente.get("url", "")
        self.ciudad = fuente.get("ciudad", "")
        self.nombre = fuente.get("nombre_real", fuente.get("dominio", ""))
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "es-CO,es;q=0.9",
        })

    def fetch(self, url=None):
        target = url or self.url
        try:
            response = self.session.get(target, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            logger.error(f"Error fetching {target}: {e}")
            return None

    def extraer_eventos(self):
        raise NotImplementedError("Cada scraper debe implementar extraer_eventos()")

    def run(self):
        try:
            eventos = self.extraer_eventos()
            logger.info(f"OK {self.nombre}: {len(eventos)} eventos encontrados")
            return eventos
        except Exception as e:
            logger.error(f"ERR {self.nombre}: {e}")
            return None
