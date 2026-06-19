#!/bin/bash

# Exit immediately if a command exits with a non-zero status or references an unbound variable
set -eu

cd ~ || exit

# ==============================================================================
# 1. Environment Variables Configuration
# ==============================================================================
# GITHUB_WORKSPACE targets the /app directory where Jules automatically clones the repo
export GITHUB_WORKSPACE=${GITHUB_WORKSPACE:-"/app"}
export GITHUB_BASE_REF=${GITHUB_BASE_REF:-"version-15"}
export GITHUB_REF=${GITHUB_REF:-"refs/heads/version-15"}

# Consistent uppercase variables to satisfy strict unbound environment checks
GITHUB_BRANCH=${GITHUB_BASE_REF:-${GITHUB_REF##*/}}
export FRAPPE_USER=${FRAPPE_USER:-"frappe"}
export FRAPPE_BRANCH=${FRAPPE_BRANCH:-$GITHUB_BRANCH}
export MARIADB_ROOT_PASSWORD=${MARIADB_ROOT_PASSWORD:-"mariadb_root_password"}

# Suppress interactive frontend prompt requests
export CI=Yes
# ==============================================================================

echo "Starting environment setup for FlexiRule..."

# 2. System Package Setup
sudo apt update
sudo apt remove -y mysql-server mysql-client || true
sudo apt install -y cron mariadb-server mariadb-client libmariadb-dev redis-server libcups2-dev

# 3. Explicitly Start Background Engine Daemons
sudo service redis-server start
sudo service mariadb start

# Ensure additional Redis instances for Frappe (Queue and Cache)
# These are required by Frappe version 15+ in CI environments
echo "Starting additional Redis instances..."
/usr/bin/redis-server --port 11000 --daemonize yes
/usr/bin/redis-server --port 13000 --daemonize yes

sleep 5 # Grace period for MariaDB socket to bind to port 3306

# 4. Install Frappe Bench CLI tool
pip install frappe-bench

# 5. Initialize Core Frappe Framework
if [ ! -d "frappe" ]; then
    echo "Cloning Frappe..."
    git clone "https://github.com/${FRAPPE_USER}/frappe" --branch "${FRAPPE_BRANCH}" --depth 1 ~/frappe
fi

if [ ! -d "frappe-bench" ]; then
    echo "Initializing Bench..."
    bench init --skip-assets --frappe-path ~/frappe --python "$(which python3)" frappe-bench
fi

# 6. Configure MariaDB Database, Users, and Collations
echo "Configuring MariaDB..."
# First, ensure we can log in to reset the password if needed
sudo mariadb -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('');" || true

sudo mariadb -u root << EOF
SET GLOBAL character_set_server = 'utf8mb4';
SET GLOBAL collation_server = 'utf8mb4_unicode_ci';
CREATE USER IF NOT EXISTS 'test_frappe'@'localhost' IDENTIFIED BY 'test_frappe';
CREATE DATABASE IF NOT EXISTS test_frappe;
GRANT ALL PRIVILEGES ON \`test_frappe\`.* TO 'test_frappe'@'localhost';
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MARIADB_ROOT_PASSWORD}';
FLUSH PRIVILEGES;
EOF

# 7. CI Optimization: Strip Unnecessary Background Daemons
cd ~/frappe-bench || exit
sed -i 's/watch:/# watch:/g' Procfile
sed -i 's/schedule:/# schedule:/g' Procfile
sed -i 's/socketio:/# socketio:/g' Procfile
sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile

# Set root credentials in common_site_config for bench commands to work
bench set-config -g mariadb_root_username root
bench set-config -g mariadb_root_password "${MARIADB_ROOT_PASSWORD}"

# ==============================================================================
# 8. Link and Configure FlexiRule from /app Context
# ==============================================================================
echo "Linking FlexiRule app..."
# Symlink and register via pip directly to bypass the bench url-parsing bug
if [ ! -d "apps/flexirule" ]; then
    ln -s "${GITHUB_WORKSPACE}" ~/frappe-bench/apps/flexirule
fi
~/frappe-bench/env/bin/pip install -e ~/frappe-bench/apps/flexirule

# Safely append flexirule to apps.txt with clean newlines to prevent merging
if ! grep -q "flexirule" ~/frappe-bench/sites/apps.txt 2>/dev/null; then
    printf "\nflexirule\n" >> ~/frappe-bench/sites/apps.txt
    sed -i '/^$/d' ~/frappe-bench/sites/apps.txt
fi

# Run bench setup to discover and fetch dependencies for flexirule
bench setup requirements --dev
# ==============================================================================

# 9. Create Site and Install App
echo "Creating site and installing app..."
bench new-site test_site --mariadb-root-password "${MARIADB_ROOT_PASSWORD}" --admin-password admin --force
bench --site test_site install-app flexirule

# 10. Build Assets
echo "Building assets..."
bench build --app flexirule

# 11. Run Tests
echo "Running tests..."
bench --site test_site set-config allow_tests true
bench --site test_site run-tests --app flexirule

echo "Setup and testing completed successfully!"
