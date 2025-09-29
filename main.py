"""Módulo principal. Ele que é o responsável pela execução do programa."""

from .src.info import WebExtractor
from .src.sharepoint import UpdateSharepointFile

def main() -> None:
    """Função principal."""
    infos = WebExtractor()
    json_data = infos.get_info()

    sharepoint = UpdateSharepointFile()
    sharepoint.put_in_sharepoint(json_data)

if __name__ == "__main__":
    main()
