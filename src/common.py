"""
    Módulo com funções e variáveis usadas em outras partes do projeto.

    Inclui:
    - Funções para autenticação e obtenção de tokens de acesso.
    - Funções para interagir com a UI usando Selenium.
    - Configuração de logging para monitoramento e depuração.
"""

import configparser
import os
import sys
import time
import logging
from pathlib import Path
from dotenv import load_dotenv
import requests
from requests.exceptions import RequestException

from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

# Configurando logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="logger.log",
    filemode="w"
)

# Configurando arquivo .ini

Config = configparser.ConfigParser()

if getattr(sys, 'frozen', False): # atributo criado pelo pyinstaller
    Config.read(Path(sys.executable).parent / "settings.ini")
else:
    Config.read(Path(__file__).parent / "settings.ini")

# Variáveis globais

Logger = logging.getLogger()

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

WEBDRIVER_OPTIONS = webdriver.ChromeOptions()

if Config.get("INIT", "SHOW_SCREEN").lower() == "false":
    WEBDRIVER_OPTIONS.add_argument("--headless=new")
else:
    WEBDRIVER_OPTIONS.add_argument("--start-maximized")

WEBDRIVER_OPTIONS.add_argument("--disable-notifications")
WEBDRIVER_OPTIONS.add_argument("--disable-extensions")
WEBDRIVER_OPTIONS.add_argument("--disable-background-networking")
WEBDRIVER_OPTIONS.add_argument("--disable-gpu")

LOAD_TIME = 10
WORKSPACE_REQUEST_INTERVAL = 3

# Variáveis locais

TIMEOUT = 10

# Funções

def get_access_token(driver: webdriver, device_code_json: str) -> str:
    """
        Obtém o token de acesso usando o código do dispositivo.
        Este token é usado para realizar requisições à API do Power BI / Sharepoint.

        Parâmetros:
        - driver (webdriver): Instância do WebDriver do Selenium. É a instância do navegador ativo.
        - device_code_json (str): Código do dispositivo obtido da função get_device_code.
    """

    access_token = None

    driver.get(device_code_json.get("verification_uri", "#"))

    interact_with_ui(driver=driver, css="[id='otc']", value=device_code_json["user_code"])

    try:
        css = "[class='table'][role='button'][aria-describedby='tileError loginHeader']"
        interact_with_ui(driver=driver, css=css)
    except WebDriverException:
        try:
            Logger.info("[Selenium] Inserindo e-mail...")
            interact_with_ui(driver=driver, css="[type='email'][id='i0116']", value=EMAIL)

            Logger.info("[Selenium] Inserindo senha...")
            interact_with_ui(driver=driver, css="[type='password'][id='i0118']", value=PASSWORD)

            Logger.info("[Selenium] Clicando para continuar...")
            interact_with_ui(driver=driver, css="[id='idSIButton9']")

            try:
                Logger.info("[Selenium] Clicando em 'continuar' para permanecer conectado...")
                interact_with_ui(driver=driver, css="[id='idSIButton9']")
            except WebDriverException:
                Logger.info("[Selenium] Não foi necessário clicar em 'continuar'.")
        except WebDriverException:
            Logger.error("[Selenium] Não foi possível prosseguir o fluxo.")

    wait_loading(driver)
    time.sleep(WORKSPACE_REQUEST_INTERVAL)

    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    token_data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": CLIENT_ID,
        "device_code": device_code_json["device_code"]
    }

    expires_in = device_code_json["expires_in"]
    interval = device_code_json.get("interval", 5)

    start_time = time.time()

    while time.time() - start_time < expires_in:
        try:
            token_response = requests.post(token_url, data=token_data, timeout=TIMEOUT)
            token_json = token_response.json()

            if "access_token" in token_json:
                access_token = token_json["access_token"]
                break

            if token_json.get("error"):
                raise RequestException
        except RequestException as error:
            Logger.error("[Requests] Erro inesperado: %s", error)

        time.sleep(interval)

    if not access_token:
        Logger.critical("[Requests] Não foi possível obter o token de acesso!")
        sys.exit()

    return access_token

def get_device_code(tenant_id: str, client_id: str, scope: str) -> dict:
    """
        Obtém o código do dispositivo para autenticação OAuth2.
        Este código posteriormente é processado, para obter um token de acesso.
        
        Parâmetros:
        - tenant_id (str): ID do tenant do Azure AD.
        - client_id (str): ID do cliente (aplicativo registrado no Azure AD).
        - scope (str): É a url que se quer ter acesso, seguido de '.default'.

        OBS.: Para que funcione corretamente, tem que ter as permissões no portal do Azure.
    """

    auth_url =  f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
    data = {
        "client_id": client_id,
        "scope": scope
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(url=auth_url, data=data, headers=headers, timeout=TIMEOUT)
    except RequestException as error:
        Logger.error("[Requests] Erro inesperado! Descrição: %s", error)

    return response.json()

def wait(driver: webdriver) -> WebDriverWait:
    """
        Método usado somente para reduzir o método WebDriverWait.

        Parâmetros:
        - driver (webdriver): Instância do navegador a esperar.
    """
    return WebDriverWait(driver, LOAD_TIME)

def interact_with_ui(driver: webdriver, css: str, value = None) -> None:
    """
        Função usada para interagir com a UI da página.
        Pode ser usada para clicar em botões ou inserir valores em campos de texto.

        Parâmetros:

        - driver (webdriver): Instância do WebDriver do Selenium. É a instância do navegador ativo.
        - css (str): Seletor CSS do elemento com o qual se quer interagir.
        - value (str, opcional): Valor a ser inserido no input. Se vazio, o elemento é clicado.
    """

    selector = (By.CSS_SELECTOR, css)

    if value:
        wait(driver).until(EC.visibility_of_element_located(selector))
        element = driver.find_element(*selector) # o '*' desempacota a tupla
        element.send_keys(value)
        element.send_keys(Keys.RETURN)
    else:
        wait(driver).until(EC.visibility_of_element_located(selector))
        element = driver.find_element(*selector) # o '*' desempacota a tupla
        element.click()

def wait_loading(driver: webdriver) -> None:
    """
        Função que espera o carregamento completo da página.
        Útil para garantir que a página esteja totalmente carregada antes de prosseguir.

        Parâmetros:
        - driver (webdriver): Instância do WebDriver do Selenium. É a instância do navegador ativo.
    """

    while True:
        state = driver.execute_script("return document.readyState")

        if state == "complete":
            break
    