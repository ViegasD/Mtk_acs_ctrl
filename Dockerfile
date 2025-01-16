# Use uma imagem base do Python
FROM python:3.9-slim

# Defina o diretório de trabalho no container
WORKDIR /app

# Copie os arquivos da aplicação para o diretório de trabalho
COPY . .

# Instale as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Exponha a porta na qual a aplicação será executada
EXPOSE 5000

# Comando para iniciar a aplicação
CMD ["python", "liberaçãomikrotik.py"]
