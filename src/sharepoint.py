"""
    Módulo responsável por atualizar o arquivo Excel no SharePoint.
    O arquivo é gerado a partir de um JSON contendo os dados extraídos via webscraping.
    Utiliza a API do SharePoint para realizar o upload do arquivo.
"""

import io
from urllib.parse import quote
import pandas
import requests
from requests.exceptions import RequestException

from selenium import webdriver

from src.common import CHROME_SERVICE, WEBDRIVER_OPTIONS, TIMEOUT
from src.common import get_access_token, get_device_code
from src.setup import Config, Logger, get_env_values

nome_site = Config.get("INIT", "SITE_NAME")
nome_dominio = Config.get("INIT", "DOMAIN_NAME")

if nome_site == "none":
    Logger.critical("Nome de site não existe!")
    raise ValueError("Nome do site não existe! (none)")
if nome_dominio == "none":
    Logger.critical("Nome do domínio não existe!")
    raise ValueError("Nome do domínio não existe! (none)")

# criar pasta e arquivo no sharepoint
# caso modificar o caminho, mudar as variáveis abaixo
FILE_PATH = (
    f"/sites/{nome_site}/Shared Documents/"
    "Configurações - Monitoramento BIs/update-pbis-log.xlsx"
)
FILE_URL = (
    f"https://{nome_dominio}.sharepoint.com/sites/{nome_site}/_api/web/"
    f"GetFileByServerRelativeUrl('{quote((FILE_PATH), safe='/')}')/$value"
)
SCOPE = f"https://{nome_dominio}.sharepoint.com/.default" # escopo de permissividade

class UpdateSharepointFile:
    """
        Classe responsável por atualizar o arquivo Excel no SharePoint.
        O arquivo é gerado a partir de um JSON contendo os dados extraídos via webscraping.

        Métodos:
        - get_data(): Retorna o dataframe com os dados que serão enviados para o SharePoint.
        - put_in_sharepoint(json): Publica o arquivo Excel atualizado no SharePoint.
    """

    def __init__(self) -> None:
        self.__options = WEBDRIVER_OPTIONS

        self.__driver = None

        self.__data = {}

    def get_data(self) -> dict:
        """
            Retorna o dataframe com os dados que serão enviados para o SharePoint.
            Útil para verificar os dados antes do envio.
        """

        return self.__data

    def put_in_sharepoint(self, json: dict) -> None:
        """
            Envia o arquivo Excel com os dados para o SharePoint.
            O arquivo é gerado a partir do JSON fornecido.

            Parâmetros:
            - json (dict): Dicionário contendo os dados a serem enviados.    
        """

        rows = []

        response = get_device_code(
            get_env_values().get('TENANT_ID'),
            get_env_values().get('CLIENT_ID'),
            SCOPE
        )
        print(response)

        self.__driver = webdriver.Chrome(service=CHROME_SERVICE, options=self.__options)

        access_token = get_access_token(driver=self.__driver, device_code_json=response)

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

        self.__data = pandas.DataFrame(rows)

        excel_buffer = io.BytesIO()
        self.__data.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        try:
            request = requests.put(
                url=FILE_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                data=excel_buffer.getvalue(),
                timeout=TIMEOUT
            )

            if request.status_code not in (200, 201, 204):
                raise RequestException(f"Status: {request.status_code} | Resposta: {request.text}")
            Logger.info("[Requests] Arquivo atualizado com sucesso no SharePoint.")
        except RequestException as error:
            Logger.error("[Requests] Erro: %s", error)
        