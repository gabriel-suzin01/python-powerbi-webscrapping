from info import Web_Extractor
from sharepoint import Update_File

def main() -> None:
    infos = Web_Extractor()
    json_data = infos.GetInfo()

    sharepoint = Update_File()
    sharepoint.Post(json_data)

if __name__ == "__main__":
    main()