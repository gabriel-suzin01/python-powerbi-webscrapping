# 🔭 Monitoramento Power BI

Este projeto automatiza o monitoramento dos horários de atualização dos fluxos / modelos semânticos do Power BI Online.
Os dados são coletados e repassados para um arquivo .xlsx, que é então publicado no Sharepoint e utilizado em um relatório Power BI!

### 👣 Instalação e execução

- **O arquivo executável já está na pasta `files`, basta baixar!**
- Caso quiser alterar alguma configuração de execução, basta alterar os valores das variáveis dentro do arquivo `settings.ini`.

### 🛠️ Conversão .py --> .exe

- A criação de uma `venv` é fundamental! Para criar uma `venv`:
    1. `python -m venv nome_venv`
    2. `venv\Scripts\activate` | windows OU `source venv/bin/activate` | linux
    3. `pip install -r requirements.txt`
- Caso queira converter manualmente o `main.py` em arquivo .exe, é possível fazer isso com a biblioteca `pyinstaller`. O código é o seguinte: `pyinstaller --onefile --noconsole --paths=./nome_da_pasta --hidden-import=setup --hidden-import=common --hidden-import=info --hidden-import=sharepoint --hidden-import=__init__ main.py`, para adicionar todas as importações e dependências corretamente.

### 📝 Qualidade de código

###### _Todos os scripts foram verificados com a biblioteca `pylint`, versão 3.3.8 e receberam classificação máxima (10/10)!_ ✅