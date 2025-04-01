import pandas as pd
import requests
import io

from common import CLIENT_ID, TENANT_ID, Logger, GetAccessToken, GetDeviceCode
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import quote

file_path = "/sites/nome_site/Shared Documents/nome_pasta/nome_arquivo.xlsx"
URL_FORMAT = quote(file_path, safe='/') # essa linha converte o caminho do arquivo para o formato correto na URL  
FILE_URL = f"https://nome_tenant.sharepoint.com/sites/nome_site/_api/web/GetFileByServerRelativeUrl('{URL_FORMAT}')/$value"

class Update_File:
    def __init__(self) -> None:
        self.__options = webdriver.ChromeOptions()
        self.__options.add_argument("--headless=new") # alterar pra --headless=new se não quiser que apareça / --start-maximized pra aparecer            
        self.__options.add_argument("--disable-notifications")        
        self.__options.add_argument("--disable-extensions")           
        self.__options.add_argument("--disable-background-networking")
        self.__options.add_argument("--disable-gpu")  

        self.__access_token = None
        self.__driver = None

    def Post(self, json: dict) -> None:
        rows = []

        self.__driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.__options)

        SCOPE = "https://nome_tenant.sharepoint.com/.default"
        device_code_json = GetDeviceCode(TENANT_ID, CLIENT_ID, SCOPE)

        self.__access_token = GetAccessToken(driver=self.__driver, device_code_json=device_code_json)

        headers = {
            "Authorization": f"Bearer {self.__access_token}",
        }

        for timestamp, workspaces in json.items():
            for workspace, reports in workspaces.items():
                for report_name, report_data in reports.items():
                    rows.append({
                        "Data e Hora": timestamp,
                        "Workspace": workspace,
                        "Relatório": report_name,
                        "Tipo": report_data["tipo"],
                        "Última Atualização": report_data["last_update"],
                        "Atualizado Hoje": report_data["atualizado_hoje"],
                        "Sucesso na Atualização": report_data["update_success"],
                        "Próxima Atualização": report_data["next_update"],
                        "Agendamento Cancelado": report_data["agendamento_cancelado"]
                    })

        dataframe = pd.DataFrame(rows)

        excel_buffer = io.BytesIO()
        dataframe.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        try:    
            target_folder = requests.put(url=FILE_URL, headers=headers, data=excel_buffer.getvalue())

            if target_folder.status_code not in (200, 201, 204):
                raise Exception(f"Erro ao acessar o SharePoint. Código de status: {target_folder.status_code}, Resposta: {target_folder.text}")
            
            Logger.info("Arquivo atualizado com sucesso no SharePoint.")
        except Exception as error:
            Logger.error(f"Erro: {error}")