"""
    Módulo responsável por coletar as informações do Power BI Online via webscrapping.
    Os principais dados coletados são: data hora de última atualização, atualizado hoje,
    erro na última atualização e data hora da próxima atualização.
"""

import sys
import datetime
import time
import requests

from bs4 import BeautifulSoup
from bs4.element import Tag
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from src.common import CLIENT_ID, TENANT_ID, TIMEOUT, EMAIL, PASSWORD, WEBDRIVER_OPTIONS, Logger
from src.common import get_access_token, get_device_code, interact_with_ui, wait, wait_loading

BASE_URL = "https://app.powerbi.com/groups/"
LOGIN_WORDS = ("singleSignOn", "signin", "login")

MAX_RETRIES = 3
RETRY_DELAY = 5

class WebExtractor:
    """
        Classe responsável por coletar os dados do Power BI Online.
        As informações são coletadas workspace por workspace.

        Métodos:
        - get_workspaces(): Pega todos os workspaces existentes em um diretório Azure.
        - get_info(): Método principal que executa a coleta dos dados.
    """

    def __init__(self) -> None:
        self.__options = WEBDRIVER_OPTIONS

        self.__access_token = None
        self.__driver = None

        self.__json = {}
        self.__current_date = datetime.datetime.today().strftime("%d/%m/%Y - %H:%M:%S")

    def __login(self, url: str) -> None:
        """
            Método usado para fazer a autenticação ao Power BI Online, caso solicitado.

            Parâmetros:
            - url (str): url que a autenticação foi solicitada.
        """

        if not any(word in url for word in LOGIN_WORDS):
            return

        for attempt in range(1, MAX_RETRIES + 1, 1):
            try:
                if not self.__driver:
                    service = Service(ChromeDriverManager().install())
                    self.__driver = webdriver.Chrome(service=service, options=self.__options)
                elif not any(word in url for word in ["singleSignOn", "signin", "login"]):
                    return
                self.__driver.get(url)

                interact_with_ui(driver=self.__driver, css="[id='email']", value=EMAIL)
                interact_with_ui(driver=self.__driver, css="[id='i0118']", value=PASSWORD)

                try:
                    interact_with_ui(driver=self.__driver, css="[id='idSIButton9']")
                    interact_with_ui(driver=self.__driver, css="[id='idBtn_Back']")
                except NoSuchElementException:
                    Logger.info("[Selenium] Sem tela de 'Continuar conectado'.")

                return
            except WebDriverException as error:
                Logger.error("[Selenium] Tentativa %s. Erro: %s", attempt, error)
                if attempt < MAX_RETRIES:
                    Logger.info("[Selenium] Tentando novamente em %s segundos...", RETRY_DELAY)
                    time.sleep(RETRY_DELAY)
                else:
                    Logger.critical("[Selenium] Todas as tentativas de login falharam!")
                    sys.exit()

    def __read_info(self, url: str) -> None:
        """
            Método responsável por fazer a leitura, workspace por workspace.
            Os dados recolhidos serão utilizados posteriormente na tela de monitoramento.

            Parâmetros:
            - url (str): url do workspace que deve ser feita a leitura dos dados.
        """

        for attempt in range(1, MAX_RETRIES + 1, 1):
            try:
                wait_loading(self.__driver)

                if any(word in self.__driver.current_url for word in LOGIN_WORDS):
                    self.__login(url)

                Logger.info("Acessando %s...", url)
                self.__driver.get(url)
                wait_loading(self.__driver)

                wait(self.__driver).until(EC.presence_of_element_located(
                    (By.TAG_NAME, "cdk-virtual-scroll-viewport")
                ))

                soup = BeautifulSoup(self.__driver.page_source, "html.parser")

                # achando o nome da workspace

                workspace_name = self.__safe_get_text(
                    soup,
                    (
                        "h1",
                        {"class": ["workspace-name", "tri-text-overflow-ellipsis", "tri-subtitle1"]}
                    )
                )

                if info := soup.find("cdk-virtual-scroll-viewport", {"id": "artifactContentView"}):
                    info = info.find(
                        "div", 
                        {"class": "cdk-virtual-scroll-content-wrapper"}
                    )
                if not info:
                    return

                # começando a pegar os dados linha a linha

                execution_data = {}

                for row in info.find_all("div", {"role": "row"}):
                    # Logger.debug(row.prettify()) --> somente usado para testes

                    name = self.__safe_get_text(
                        row.find("span", {"class": "name-container"}),
                        ("a", {"class": ["name", "trimmedTextWithEllipsis", "ng-star-inserted"]})
                    )

                    file_type = (
                        row.find("span", {"data-testid": "fluentListCell.type"}) or {}
                    ).get("title", "Desconhecido")

                    if file_type == "Pasta":
                        continue

                    last_refresh = (
                        row.find("span", {"data-testid": "fluentListCell.lastRefresh"}) or {}
                    ).get("title", "Data de última atualização desconhecida.")

                    update_check = row.find(
                        "i",
                        {"class": ["warning", "glyphicon", "pbi-glyph-warning", "glyph-small"]}
                    ) or (row.find("span", {"class": "dataflow-refresh-icons"}).find(
                        "button",
                        {"class": ["glyphicon", "pbi-glyph-warning", "ng-star-inserted"]}
                    ) if row.find("span", {"class": "dataflow-refresh-icons"}) else None)

                    # implementar lógica de atualizar automaticamente no futuro

                    next_upt = (
                        row.find("span", {"data-testid": "fluentListCell.nextRefresh"}) or {}
                    ).get("title", "Data da próxima atualização desconhecida.")

                    if workspace_name not in execution_data:
                        execution_data[workspace_name] = {}

                    if name in execution_data[workspace_name]:
                        name = name + " " + file_type

                    execution_data[workspace_name][name] = {
                        "tipo": file_type,
                        "last_update": last_refresh,
                        "atualizado_hoje": last_refresh[0:9] == self.__current_date[0:9],
                        "update_success": update_check,
                        "next_update": next_upt,
                        "agendamento_cancelado": next_upt == "N/D"
                    }

                if self.__current_date not in self.__json:
                    self.__json[self.__current_date] = {}
                self.__json[self.__current_date].update(execution_data)
                return
            except WebDriverException as error:
                Logger.error("[Selenium] Tentativa %s falhou - %s. Erro: %s", attempt, url, error)
                if attempt < MAX_RETRIES:
                    Logger.info("[Selenium] Tentando novamente em %s segundos...", RETRY_DELAY)
                    time.sleep(RETRY_DELAY)
                else:
                    Logger.critical("[Selenium] Todas as tentativas falharam para: %s", url)

    def __safe_get_text(self, parent: Tag, selector: tuple[str, dict] | None) -> str:
        """
            Função que realiza a sanitização: verifica se existe ou não o elemento.
            Caso não existir, retorna "Desconhecido".

            Parâmetros:
            - parent (Tag): Elemento pai do elemento a ser procurado, "selector".
            - selector (tuple[str, dict] | None): Elemento a ser pego o texto.
        """

        tag = parent.find(*selector) if parent else None
        return tag.get_text(strip=True) if tag else "Desconhecido (a)"

    def get_workspaces(self) -> list:
        """
            Função responsável por pegar os workspaces do diretório.
            Retorna os workspaces no formato de lista.
        """

        for attempt in range(1, MAX_RETRIES + 1, 1):
            try:
                workspaces_url = "https://api.powerbi.com/v1.0/myorg/groups"

                scope = "https://analysis.windows.net/powerbi/api/.default"
                code = get_device_code(TENANT_ID, CLIENT_ID, scope)

                service = Service(ChromeDriverManager().install())
                self.__driver = webdriver.Chrome(service=service, options=self.__options)

                self.__access_token = get_access_token(driver=self.__driver, device_code_json=code)

                headers = {
                    "Authorization": f"Bearer {self.__access_token}" 
                }

                response = requests.get(url=workspaces_url, headers=headers, timeout=TIMEOUT)
                response.raise_for_status()
                response = response.json()

                workspaces = set()
            except WebDriverException as error:
                Logger.error("[Selenium] Tentativa %s. Erro: %s", attempt, error)
                if attempt < MAX_RETRIES:
                    Logger.info("[Selenium] Tentando novamente em %s segundos...", RETRY_DELAY)
                    time.sleep(RETRY_DELAY)
                else:
                    Logger.critical("[Selenium] Não foi possível pegar as workspaces!")
                    sys.exit()

            return list(workspaces)

    def get_info(self) -> dict:
        """
            Método que gerencia toda a classe.
            Faz login quando necessário, pega as workspaces e coleta dos dados.
        """

        urls = self.get_workspaces()

        for url in urls:
            self.__read_info(url)

        self.__driver.quit()
        return self.__json
    