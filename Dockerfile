# --- Estágio 1: Base do Python e Dependências do Sistema ---
# Usa uma imagem oficial do Python 3.11, versão 'slim' para ser mais leve.
FROM python:3.11-slim

# Atualiza os pacotes e instala o poppler-utils, necessário para algumas
# bibliotecas de processamento de PDF. O '&& rm -rf /var/lib/apt/lists/*'
# limpa o cache para manter a imagem final pequena.
RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*

# --- Estágio 2: Configuração da Aplicação ---
# Define o diretório de trabalho dentro do contentor.
WORKDIR /app

# Copia o ficheiro de requerimentos para o diretório de trabalho.
# Manter este passo separado otimiza o cache do Docker.
COPY requirements.txt .

# Instala as bibliotecas Python, usando '--no-cache-dir' para otimizar o tamanho.
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o conteúdo do projeto para o diretório de trabalho no contentor.
# Isto garante que 'credentials.json', 'drive_config.json', etc., sejam incluídos.
COPY . .

# --- Estágio 3: Execução ---
# --- CORREÇÃO IMPORTANTE ---
# O comando foi encapsulado em 'sh -c' para garantir que a variável de ambiente
# $PORT seja corretamente interpretada pelo shell do contêiner antes de ser
# passada para o gunicorn. Isso resolve o erro "'$PORT' is not a valid port number".
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 300 servidor_web:app"]

