# DRIMS - Deployment Guide

## Overview
This guide covers deploying the Disaster Relief Inventory Management System (DRIMS) on Red Hat Enterprise Linux (RHEL) or compatible systems.

## System Requirements

### RHEL 8/9 Requirements
- Python 3.11 or higher
- PostgreSQL 13 or higher
- Nginx (recommended for production)
- 2GB RAM minimum (4GB recommended)
- 20GB disk space

## Deployment Steps

### 1. Install System Dependencies

```bash
# Install Python and development tools
sudo dnf install python3.11 python3.11-pip python3.11-devel gcc

# Install PostgreSQL
sudo dnf install postgresql-server postgresql-contrib

# Install Nginx
sudo dnf install nginx

# Install additional dependencies
sudo dnf install git
```

### 2. Set Up PostgreSQL

```bash
# Initialize PostgreSQL
sudo postgresql-setup --initdb

# Start and enable PostgreSQL
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE drims_db;
CREATE USER drims_user WITH PASSWORD 'CHANGE_THIS_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE drims_db TO drims_user;
\q
EOF
```

### 3. Deploy Application

```bash
# Create application directory
sudo mkdir -p /opt/drims
cd /opt/drims

# Clone repository (adjust URL to your Git server)
sudo git clone https://github.com/yourusername/drims.git .

# Create application user
sudo useradd -r -s /bin/false drims-app

# Set ownership
sudo chown -R drims-app:drims-app /opt/drims

# Switch to application user
sudo -u drims-app bash

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

### 4. Configure Environment

```bash
# Create .env file (as drims-app user)
cat > .env << 'EOF'
SECRET_KEY=GENERATE_RANDOM_KEY_HERE
DATABASE_URL=postgresql://drims_user:CHANGE_THIS_PASSWORD@localhost/drims_db
FLASK_ENV=production
EOF

# Generate a secure secret key
python3 -c 'import secrets; print("SECRET_KEY=" + secrets.token_hex(32))' >> .env.tmp
# Manually copy the SECRET_KEY from .env.tmp to .env

# Set proper permissions
chmod 600 .env
```

### 5. Initialize Database

```bash
# Still as drims-app user with venv activated
export $(cat .env | xargs)

# Initialize database tables
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Create initial admin user
flask create-admin
```

### 6. Create Systemd Service

Exit back to root user, then create service file:

```bash
# Create service file
sudo nano /etc/systemd/system/drims.service
```

Add the following content:

```ini
[Unit]
Description=Disaster Relief Inventory Management System (DRIMS)
After=network.target postgresql.service

[Service]
Type=notify
User=drims-app
Group=drims-app
WorkingDirectory=/opt/drims
Environment="PATH=/opt/drims/venv/bin"
EnvironmentFile=/opt/drims/.env
ExecStart=/opt/drims/venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile /var/log/drims/access.log \
    --error-logfile /var/log/drims/error.log \
    app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create log directory:

```bash
sudo mkdir -p /var/log/drims
sudo chown drims-app:drims-app /var/log/drims
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable drims
sudo systemctl start drims
sudo systemctl status drims
```

### 7. Configure Nginx Reverse Proxy

```bash
sudo nano /etc/nginx/conf.d/drims.conf
```

Add the following:

```nginx
server {
    listen 80;
    server_name drims.yourdomain.com;  # Change to your domain

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/drims/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

Enable and restart Nginx:

```bash
sudo systemctl enable nginx
sudo systemctl restart nginx
```

### 8. Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 9. Set Up SSL/TLS (Recommended)

Install certbot for Let's Encrypt:

```bash
sudo dnf install certbot python3-certbot-nginx
sudo certbot --nginx -d drims.yourdomain.com
```

## Post-Deployment

### Create Additional Users

```bash
# SSH into server
cd /opt/drims
sudo -u drims-app bash
source venv/bin/activate
export $(cat .env | xargs)

# Create users
flask create-user
```

### Monitoring

```bash
# Check application logs
sudo journalctl -u drims -f

# Check Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Check application-specific logs
sudo tail -f /var/log/drims/access.log
sudo tail -f /var/log/drims/error.log
```

### Backup Strategy

Create backup script `/opt/backup-drims.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/drims"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
sudo -u postgres pg_dump drims_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup uploaded files (if any)
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /opt/drims/static/uploads 2>/dev/null

# Keep only last 30 days of backups
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

Make executable and add to cron:

```bash
sudo chmod +x /opt/backup-drims.sh
sudo crontab -e
# Add: 0 2 * * * /opt/backup-drims.sh
```

### Updates and Maintenance

```bash
# Pull latest changes
cd /opt/drims
sudo -u drims-app git pull origin main

# Activate venv and update dependencies
sudo -u drims-app bash
source venv/bin/activate
pip install -r requirements.txt

# Restart service
exit
sudo systemctl restart drims
```

## Security Checklist

- [ ] Change default PostgreSQL password
- [ ] Generate strong SECRET_KEY
- [ ] Enable firewall (firewalld)
- [ ] Install and configure SELinux
- [ ] Set up SSL/TLS certificates
- [ ] Configure regular backups
- [ ] Enable log rotation
- [ ] Keep system updated (`sudo dnf update`)
- [ ] Restrict SSH access
- [ ] Monitor application logs

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u drims -n 50
```

### Database connection issues
```bash
sudo -u postgres psql
\l  # List databases
\du # List users
```

### Permission issues
```bash
sudo chown -R drims-app:drims-app /opt/drims
sudo chmod 600 /opt/drims/.env
```

## Support

For issues or questions, contact your system administrator or refer to the project documentation.
