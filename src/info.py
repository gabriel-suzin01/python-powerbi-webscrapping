import datetime
import time
import requests
import sys

from bs4 import BeautifulSoup
from common import CLIENT_ID, TENANT_ID, PAGE_LOAD_WAIT_TIME, EMAIL, PASSWORD, Logger, GetAccessToken, GetDeviceCode, InteractWithUI, WaitLoading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://app.powerbi.com/groups/"

MAX_RETRIES = 3
RETRY_DELAY = 5

class Web_Extractor:
    def __init__(self) -> None:
        self.__options = webdriver.ChromeOptions()
        self.__options.add_argument("--headless=new") # alterar pra --headless=new se não quiser que apareça / --start-maximized pra aparecer            
        self.__options.add_argument("--disable-notifications")        
        self.__options.add_argument("--disable-extensions")           
        self.__options.add_argument("--disable-background-networking")
        self.__options.add_argument("--disable-gpu")      

        self.__access_token = None
        self.__driver = None
        
        self.__json = {}
        self.__current_date = datetime.datetime.today().strftime("%d/%m/%Y - %H:%M:%S")

    def __GetWorkspaces(self) -> list:
        for attempt in range(1, MAX_RETRIES + 1, 1):
            try:
                workspaces_url = f"https://api.powerbi.com/v1.0/myorg/groups"

                SCOPE = "https://analysis.windows.net/powerbi/api/.default"
                device_code_json = GetDeviceCode(TENANT_ID, CLIENT_ID, SCOPE)
                
                self.__driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.__options)

                self.__access_token = GetAccessToken(driver=self.__driver, device_code_json=device_code_json)

                headers = {
                    "Authorization": f"Bearer {self.__access_token}" 
                }

                response = requests.get(workspaces_url, headers=headers)
                response.raise_for_status()
                response = response.json()
                
                workspaces = set()
                
                return list(workspaces)
            except Exception as error:
                Logger.error(f"Não foi possível pegar as workspaces! Tentativa {attempt}. Erro: {error}")
                if attempt < MAX_RETRIES:
                    Logger.info(f"Tentando novamente em {RETRY_DELAY} segundos...")
                    time.sleep(RETRY_DELAY)
                else:
                    Logger.critical("Todas as tentativas de pegar as workspaces falharam!")
                    sys.exit()

    def __Login(self, url : str) -> None:
        if not any(word in url for word in ["singleSignOn", "signin", "login"]):
            return
        
        for attempt in range(1, MAX_RETRIES + 1, 1):
            try:
                if not self.__driver:
                    self.__driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.__options)
                elif not any(word in url for word in ["singleSignOn", "signin", "login"]):
                    return
                
                self.__driver.get(url)

                InteractWithUI(driver=self.__driver, css="[id='email']", value=EMAIL)
                InteractWithUI(driver=self.__driver, css="[id='i0118']", value=PASSWORD)

                try:
                    InteractWithUI(driver=self.__driver, css="[id='idSIButton9']")
                    InteractWithUI(driver=self.__driver, css="[id='idBtn_Back']")
                except:
                    Logger.info("Sem tela de 'Continuar conectado'.")

                return
            except Exception as error:
                Logger.error(f"Não foi possível fazer login! Tentativa {attempt}. Erro: {error}")
                if attempt < MAX_RETRIES:
                    Logger.info(f"Tentando novamente em {RETRY_DELAY} segundos...")
                    time.sleep(RETRY_DELAY)
                else:
                    Logger.critical("Todas as tentativas de login falharam!")
                    sys.exit()

    def __ReadInfo(self, url : str) -> None:
        for attempt in range(1, MAX_RETRIES + 1, 1):
            try:
                WaitLoading(self.__driver)

                if any(word in self.__driver.current_url for word in ["singleSignOn", "signin", "login"]):
                    self.__Login(url)

                Logger.info(f"Acessando {url}...")
                self.__driver.get(url)
                WaitLoading(self.__driver)

                WebDriverWait(self.__driver, PAGE_LOAD_WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, "cdk-virtual-scroll-viewport")))

                soup = BeautifulSoup(self.__driver.page_source, "html.parser")

                workspace_name = soup.find("h1", {"class": ["workspace-name", "tri-text-overflow-ellipsis", "tri-subtitle1"]}).get_text(strip=True)

                all_info = soup.find("cdk-virtual-scroll-viewport", {"id": "artifactContentView"})

                if all_info:
                    all_info = all_info.find("div", {"class": "cdk-virtual-scroll-content-wrapper"})
                if not all_info:
                    return
                
                rows = all_info.find_all("div", {"role": "row"})

                execution_data = {}

                for row in rows:
                    # Logger.debug(row.prettify()) --> somente usado para testes

                    name = row.find("span", {"class": "name-container"})

                    if name:
                        name = name.find("a", {"class": ["name", "trimmedTextWithEllipsis", "ng-star-inserted"]}).get_text(strip=True)
                    else: name = "Desconhecido"

                    file_type = row.find("span", {"data-testid": "fluentListCell.type"})
                    
                    if file_type:
                        file_type = file_type.get("title", "Tipo desconhecido.")

                        if file_type == "Pasta":
                            continue
                    else: file_type = "Desconhecido"

                    last_refresh = row.find("span", {"data-testid": "fluentListCell.lastRefresh"})
                    
                    if last_refresh:
                        last_refresh = last_refresh.get("title", "Data de última atualização desconhecida.")
                        date_equals_today = True if last_refresh[0:9] == self.__current_date[0:9] else False
                    else: 
                        last_refresh = "Desconhecido"
                        date_equals_today = False

                    span = row.find("span", {"class": "dataflow-refresh-icons"})
                    update_check = row.find("i", {"class": ["warning", "glyphicon", "pbi-glyph-warning", "glyph-small"]}) or (span.find("button", {"class": ["glyphicon", "pbi-glyph-warning", "ng-star-inserted"]}) if span else None)
                    update_check = False if update_check else True

                    # if update_check == False:
                    #     try:    
                    #         element = WebDriverWait(self.__driver, PAGE_LOAD_WAIT_TIME).until(EC.element_to_be_clickable(self.__driver.find_element("xpath", "//button[@data-testid='quick-action-button-Atualizar agora']")))

                    #         actions = ActionChains(self.__driver)
                    #         actions.move_to_element(element).perform()
                    #         element.click()
                    #     except Exception as error:
                    #         Logger.error("Não foi possível atualizar! ", error)

                    next_refresh = row.find("span", {"data-testid": "fluentListCell.nextRefresh"})
                    
                    if next_refresh:
                        next_refresh = next_refresh.get("title", "Data da próxima atualização desconhecida.")
                        schedule_canceled = True if next_refresh == "N/D" else False
                    else: 
                        next_refresh = "Desconhecido"
                        schedule_canceled = False

                    if workspace_name not in execution_data:
                        execution_data[workspace_name] = {}

                    if name in execution_data[workspace_name]:
                        name = name + " " + file_type

                    execution_data[workspace_name][name] = {
                        "tipo": file_type,
                        "last_update": last_refresh,
                        "atualizado_hoje": date_equals_today,
                        "update_success": update_check,
                        "next_update": next_refresh,
                        "agendamento_cancelado": schedule_canceled
                    }
                
                if self.__current_date not in self.__json:
                    self.__json[self.__current_date] = {}

                self.__json[self.__current_date].update(execution_data)
                return
            except Exception as error:
                Logger.error(f"Tentativa {attempt} falhou para {url}. Erro: {error}")
                if attempt < MAX_RETRIES:
                    Logger.info(f"Tentando novamente em {RETRY_DELAY} segundos...")
                    time.sleep(RETRY_DELAY)
                else:
                    Logger.critical(f"Todas as tentativas falharam para: {url}")

    def GetInfo(self) -> dict:
        urls = self.__GetWorkspaces()

        for url in urls:
            self.__ReadInfo(url)

        self.__driver.quit()
        return self.__json