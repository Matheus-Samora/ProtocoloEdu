# Dockerfile de Produção para ProtocoloEdu API
FROM python:3.11-slim

# Evita buffering para logs em tempo real
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instala dependências do sistema necessárias para compilação e criptografia
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.lock requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.lock

# Copia código da aplicação
COPY . .

# Runtime data directories only; source code remains root-owned.
RUN useradd --uid 10001 --create-home appuser && \
    mkdir -p /app/storage /app/data_dossiers /app/security-state && \
    chown appuser:appuser /app/storage /app/data_dossiers /app/security-state && \
    chmod 700 /app/storage /app/data_dossiers /app/security-state
ENV PROTOCOL_ENV=production
ENV COOKIE_SECURE=true
USER appuser

# Expõe porta padrão
EXPOSE 8080

# Inicia com Gunicorn para alta concorrência em produção
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "120", "api_server:app"]
