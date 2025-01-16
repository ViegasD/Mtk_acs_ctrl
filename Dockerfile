# Dockerfile para uma aplicação Flask com a biblioteca librouteros

# Utiliza a imagem oficial do Python 3.9
FROM python:3.9

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos necessários para a aplicação
COPY . /app

# Instala as dependências necessárias
RUN pip install --no-cache-dir flask librouteros

# Expõe a porta 5000 para o Flask
EXPOSE 5000

# Define a variável de ambiente para não usar buffer de saída
ENV PYTHONUNBUFFERED=1

# Comando para rodar a aplicação Flask
CMD ["python", "app.py"]
