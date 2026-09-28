# Guia Oficial de Implantação e Hospedagem em Produção - ProtocoloEdu

Este documento estabelece o passo a passo técnico para colocar o **ProtocoloEdu** no ar em ambiente de produção com alta disponibilidade, conformidade com a LGPD e máxima segurança institucional.

---

## 1. Dimensionamento do Servidor (Sizing Recomendado)

Para atender simultaneamente períodos de pico de matrículas (janeiro e julho) com centenas de uploads concorrentes:

| Componente | Mínimo (Colégios / Faculdades Médias) | Recomendado (Grandes Centros Universitários) |
| :--- | :--- | :--- |
| **Processador (vCPU)** | 2 vCPUs | 4 vCPUs |
| **Memória RAM** | 4 GB | 8 GB |
| **Armazenamento** | 50 GB SSD NVMe | 150 GB+ SSD NVMe (com expansão de volume) |
| **Sistema Operacional** | Ubuntu 22.04 LTS ou 24.04 LTS | Ubuntu 22.04 LTS ou 24.04 LTS |
| **Região / Data Center** | **São Paulo, Brasil** (AWS `sa-east-1`, OCI Vinhedo/SP ou GCP SP) | **São Paulo, Brasil** (Soberania de dados / LGPD) |

---

## 2. Passo a Passo de Instalação (Docker & Docker Compose)

### Passo 1: Preparar o Servidor
Acesse o servidor via SSH e instale o Docker e o Git:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin git curl
sudo systemctl enable --now docker
```

### Passo 2: Clonar ou Enviar o Projeto
```bash
cd /opt
# Clone seu repositório ou descompacte o pacote:
git clone https://seu-repositorio/protocolo-imes.git protocoloedu
cd protocoloedu
```

### Passo 3: Configurar as Variáveis de Ambiente
Copie o modelo de produção:
```bash
cp .env.example .env
nano .env
```
Preencha a sua chave oficial do Gemini (`GEMINI_API_KEY`) e as senhas das secretarias.

### Passo 4: Subir os Contêineres
Inicie a aplicação e o proxy reverso Nginx com um único comando:
```bash
docker compose up -d --build
```
Verifique se tudo está ativo:
```bash
docker compose ps
docker compose logs -f app
```

---

## 3. Configuração de Domínio e Certificado SSL Gratuito (HTTPS)

Para apontar seu domínio (ex: `protocolo.suafaculdade.edu.br`):

1. **DNS**: No seu provedor de domínio (Registro.br, Cloudflare, etc.), crie um registro do tipo `A` apontando para o IP público do seu servidor.
2. **Certificado Let's Encrypt**:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d protocolo.suafaculdade.edu.br
```
O Certbot configurará automaticamente o redirecionamento de HTTP para HTTPS com certificado TLS 1.3 válido por 90 dias com renovação automática.

---

## 4. Política de Backup e Salvaguarda Documental (Disaster Recovery)

Como todos os arquivos de custódia e dossiês ficam salvos localmente em pastas mapeadas no host (`./storage` e `./data_dossiers`), o backup é simples e confiável.

### Script de Backup Automático Diário (`/opt/backup_protocolo.sh`):
```bash
#!/bin/bash
DATA=$(date +%Y%m%d_%H%M%S)
DESTINO="/backup/protocoloedu"
mkdir -p $DESTINO

# Compacta os dossiês e o acervo documental A-Z
tar -czf $DESTINO/backup_documentos_$DATA.tar.gz /opt/protocoloedu/storage /opt/protocoloedu/data_dossiers /opt/protocoloedu/*.json

# Mantém apenas os últimos 30 dias de backup
find $DESTINO -type f -name "*.tar.gz" -mtime +30 -delete

echo "Backup concluído em: $DESTINO/backup_documentos_$DATA.tar.gz"
```
Agende no crontab (`crontab -e`) para rodar toda madrugada às 03:00:
```cron
0 3 * * * /bin/bash /opt/backup_protocolo.sh > /dev/null 2>&1
```

---

## 5. Conformidade Regulatória e LGPD

1. **Soberania Nacional**: Com o servidor hospedado no Brasil, não ocorre transferência internacional indevida de dados sensíveis.
2. **Guardião de Custódia Ativo**: O sistema expurga qualquer arquivo rejeitado ou não autenticado do disco, mantendo no prontuário do aluno apenas documentos homologados.
3. **Logs de Auditoria Imutáveis**: Todas as aprovações, recusas e pareceres da IA possuem carimbo temporal UTC e identificador de sessão para fiscalizações do MEC.
