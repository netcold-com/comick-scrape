#!/bin/bash
set -e

# Ask options upfront
read -rp "Install and configure Apache? (y/n) " install_apache
install_apache=${install_apache,,}

read -rp "Install systemd services and timers? (y/n) " install_services
install_services=${install_services,,}

echo "Starting setup... This may take a while."

# === Create user 'manhwa' with sudo rights ===
echo "Creating user 'manhwa' with password 'manhwa' and sudo privileges..."
if ! id -u manhwa &>/dev/null; then
    useradd -m -s /bin/bash manhwa
    echo 'manhwa:manhwa' | chpasswd
    usermod -aG sudo manhwa
    echo "User 'manhwa' created."
else
    echo "User 'manhwa' already exists, skipping creation."
fi

# === Install system dependencies ===
echo "Updating package list and installing system dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libatspi2.0-0 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 libgbm1 libcairo2 libpango-1.0-0 libasound2 xvfb tree chromium chromium-driver

# === Apache install/config if requested ===
if [[ "$install_apache" == "y" ]]; then
    echo "Installing Apache and dependencies..."
    apt install -y apache2 tree
    a2enmod rewrite

    echo "Configuring Apache for /var/www/html/manhwa..."
    tee -a /etc/apache2/apache2.conf > /dev/null << 'EOF'

<Directory /var/www/html/manhwa>
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>
EOF

    # Move default index.html if exists
    if [ -f /var/www/html/index.html ]; then
        mv /var/www/html/index.html /var/www/
    fi

    curl -o /var/www/html/manhwa/.htaccess https://raw.githubusercontent.com/netcold-com/comick-scrape/refs/heads/main/apache/.htaccess
    chown manhwa:manhwa /var/www/html/manhwa/.htaccess

    curl -o /etc/apache2/sites-available/000-default.conf https://raw.githubusercontent.com/netcold-com/comick-scrape/refs/heads/main/apache/000-default.conf
    chown root:root /etc/apache2/sites-available/000-default.conf

    systemctl restart apache2
    echo "Apache installed and configured."
fi

# === Prepare manhwa folder and download files ===
mkdir -p /var/www/html/manhwa
chown manhwa:manhwa /var/www/html/manhwa
chmod 700 /var/www/html/manhwa

echo "Downloading project files..."
for file in downloadChapters.py fetchUrls.py update-chapters.txt; do
    curl -o /var/www/html/manhwa/"$file" https://raw.githubusercontent.com/netcold-com/comick-scrape/refs/heads/main/python/"$file"
    chown manhwa:manhwa /var/www/html/manhwa/"$file"
    if [[ "$file" == "update-chapters.txt" ]]; then
        # Ask about update-chapters.txt permissions
        read -rp "Allow others to edit update-chapters.txt? (y/n) " allow_edit
        allow_edit=${allow_edit,,}

        if [[ "$allow_edit" == "y" ]]; then
            chmod 666 /var/www/html/manhwa/update-chapters.txt
            echo "Permissions set to allow everyone to read/write update-chapters.txt"
        else
            chmod 600 /var/www/html/manhwa/update-chapters.txt
            echo "Permissions set so only manhwa can read/write update-chapters.txt"
        fi
    else
        # For Python scripts, strict permissions so only manhwa can execute them
        if [[ "$file" == *.py ]]; then
            chmod 700 /var/www/html/manhwa/"$file"
        else
            chmod 600 /var/www/html/manhwa/"$file"
        fi
    fi
done

# === Install systemd services and timers if requested ===
if [[ "$install_services" == "y" ]]; then
    echo "Creating systemd services and timers..."

    tee /etc/systemd/system/download.service > /dev/null << EOF
[Unit]
Description=Run Python script downloadChapters.py with xvfb-run

[Service]
Type=oneshot
WorkingDirectory=/var/www/html/manhwa
ExecStart=/usr/bin/xvfb-run -a /usr/bin/python3 downloadChapters.py
User=manhwa
Group=manhwa
EOF

    tee /etc/systemd/system/download.timer > /dev/null << EOF
[Unit]
Description=Run download.service 1 hour after fetch.service

[Timer]
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF

    tee /etc/systemd/system/fetch.service > /dev/null << EOF
[Unit]
Description=Run Python script fetchUrls.py with xvfb-run

[Service]
Type=oneshot
WorkingDirectory=/var/www/html/manhwa
ExecStart=/usr/bin/xvfb-run -a /usr/bin/python3 fetchUrls.py
User=manhwa
Group=manhwa
EOF

    tee /etc/systemd/system/fetch.timer > /dev/null << EOF
[Unit]
Description=Run fetch.service weekly

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
EOF

    systemctl daemon-reload
    systemctl enable --now download.timer fetch.timer
    echo "Systemd services and timers installed and started."
fi

# === Install Python packages as manhwa user ===
echo "Installing Python packages as user 'manhwa'..."
sudo -u manhwa bash -c '
export PATH="$HOME/.local/bin:$PATH"
python3 -m pip install --user --upgrade pip
python3 -m pip install --user playwright selenium requests urllib3 charset_normalizer chardet
python3 -m playwright install
'

echo "Setup complete! Run 'sudo -i -u manhwa' to switch to the manhwa user shell."
