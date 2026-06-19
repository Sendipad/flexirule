#!/bin/bash

set -e

cd ~ || exit

# Install dependencies
sudo apt-get update
sudo apt-get install -y libcups2-dev redis-server mariadb-client libmariadb-dev

pip install frappe-bench

# Setup Frappe Bench
# Use version-15 as the default branch for Frappe
frappebranch="version-15"
frappeuser="frappe"

git clone "https://github.com/${frappeuser}/frappe" --branch "${frappebranch}" --depth 1
bench init --skip-assets --skip-redis-config-generation --frappe-path ~/frappe --python "$(which python)" frappe-bench

# Manual Database Setup
mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL character_set_server = 'utf8mb4'"
mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'"
mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "CREATE USER 'test_frappe'@'localhost' IDENTIFIED BY 'test_frappe'"
mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "CREATE DATABASE test_frappe"
mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "GRANT ALL PRIVILEGES ON \`test_frappe\`.* TO 'test_frappe'@'localhost'"
mariadb --host 127.0.0.1 --port 3306 -u root -proot -e "FLUSH PRIVILEGES"

# Site Configuration
mkdir -p ~/frappe-bench/sites/test_site
cat << EOF > ~/frappe-bench/sites/test_site/site_config.json
{
 "db_name": "test_frappe",
 "db_password": "test_frappe",
 "db_type": "mariadb",
 "db_host": "127.0.0.1",
 "db_port": 3306
}
EOF

cd ~/frappe-bench || exit

# Disable background workers for testing speed
sed -i 's/watch:/# watch:/g' Procfile
sed -i 's/schedule:/# schedule:/g' Procfile
sed -i 's/socketio:/# socketio:/g' Procfile
sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile

# Fetch flexirule from current workspace
bench get-app flexirule "${GITHUB_WORKSPACE}"
bench setup requirements --dev

# Start bench in background
bench start &>> ~/frappe-bench/bench_start.log &

# Build assets
CI=Yes bench build --app frappe

# Reinstall and seed the app
bench --site test_site reinstall --db-root-password root --admin-password admin --yes
bench --verbose --site test_site install-app flexirule
