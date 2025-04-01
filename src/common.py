import logging
import requests
import time
import sys

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

# Logger, pra se ter mais controle das mensagens

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename="logger.log",
    filemode="w"
)

# Variáveis gerais

Logger = logging.getLogger()

TENANT_ID = "#"
EMBEDDED_CLIENT_ID = "#"
CLIENT_ID = "#"

EMAIL = "#"   
PASSWORD = "#"

PAGE_LOAD_WAIT_TIME = 10
WORKSPACE_REQUEST_INTERVAL = 3

# Funções gerais

# Função para pegar o access token

def GetAccessToken(driver: webdriver, device_code_json: str) -> str:
    access_token = None

    driver.get(device_code_json.get("verification_uri", "#"))

    InteractWithUI(driver=driver, css="[id='otc']", value=device_code_json.get("user_code", "Erro!"))

    try:
        InteractWithUI(driver=driver, css="[class='table'][role='button'][aria-describedby='tileError loginHeader']")
    except:
        try:
            Logger.info("Inserindo e-mail...")                        
            InteractWithUI(driver=driver, css="[type='email'][id='i0116']", value=EMAIL)

            Logger.info("Inserindo senha...")
            InteractWithUI(driver=driver, css="[type='password'][id='i0118']", value=PASSWORD)

            Logger.info("Clicando para continuar...")
            InteractWithUI(driver=driver, css="[id='idSIButton9']")

            try:
                Logger.info("Clicando em 'continuar' para permanecer conectado...")
                InteractWithUI(driver=driver, css="[id='idSIButton9']")
            except:
                Logger.info("Não foi necessário clicar em 'continuar' para permanecer conectado.")
                pass
        except:
            Logger.error("Não foi possível prosseguir o fluxo.")
            raise Exception

    WaitLoading(driver)
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
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        if "access_token" in token_json:
            access_token = token_json["access_token"]
            break
        elif token_json.get("error") == "authorization_pending":
            time.sleep(interval)
        else:
            Logger.error(f"Erro inesperado: {token_json}")

    if not access_token:
        sys.exit()

    return access_token

# Função pra peger o device code

def GetDeviceCode(tenant_id: str, client_id: str, scope: str) -> dict:
    device_code_url =  f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
    device_code_data = {
        "client_id": client_id,
        "scope": scope
    }
    device_code_headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    device_code_response = requests.post(device_code_url, data=device_code_data, headers=device_code_headers)
    
    return device_code_response.json()

# Função para interagir com a UI da página

def InteractWithUI(driver, css : str, value = None) -> None:
    if value:
        WebDriverWait(driver, PAGE_LOAD_WAIT_TIME).until(EC.visibility_of_element_located((By.CSS_SELECTOR, css)))
        element = driver.find_element(By.CSS_SELECTOR, css)
        element.send_keys(value)
        element.send_keys(Keys.RETURN)
    else:
        WebDriverWait(driver, PAGE_LOAD_WAIT_TIME).until(EC.visibility_of_element_located((By.CSS_SELECTOR, css)))
        element = driver.find_element(By.CSS_SELECTOR, css)
        element.click()

# Função para esperar o loading da página

def WaitLoading(driver: webdriver) -> None:
    while True:
        state = driver.execute_script("return document.readyState")

        if state == "complete":
            break
    return