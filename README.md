# 🔭 Monitoramento Power BI

Este projeto surgiu com a necessidade de monitorar os horários de atualização dos fluxos localizados no Power BI Online.
Os dados são coletados e repassados para um arquivo .xlsx, que é então publicado no Sharepoint e utilizado em um relatório Power BI!

### 👣 Passo a Passo para converter em um .exe

- A biblioteca usada para transformar arquivos python em .exe é `pyinstaller`.
- Pra fazer isso: `pyinstaller --onefile --noconsole nome_arquivo.py`.
- Recomendado usar um ambiente virtual (`venv`) para isolar as dependências!
- O arquivo executável estará na pasta dist.

### 📝 Qualidade de código

###### _Todos os scripts foram verificados com a biblioteca `pylint`, versão 3.3.8 e receberam classificação máxima (10/10)!_ ✅