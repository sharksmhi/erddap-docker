#!/usr/bin/env bash
set -e

echo ""
echo "Welcome to ERDDAP Ubuntu Server Install"
echo ""
echo "The following tasks will be done:"
echo ""
echo " * Create user account for server administration"
echo ""
echo "     This account should be used instead of root for administration of the"
echo "     server."
echo ""
echo " * Ensure that root login is disabled for SSH"
echo ""
echo "     The administrator account should be used instead of root when logging in"
echo "     over SSH."
echo ""
echo " * Ensure that the firewall is activated"
echo ""
echo "     UFW (Uncomplicated Firewall) will be configured and activated, unless"
echo "     already active."
echo ""
echo " * Ensure that docker is installed"
echo ""
echo "     If docker and docker-compose is not already installed, they will be"
echo "     installed from the official docker repo."
echo ""


read -p "Are you sure you want to continue (y/n)? " reply
[[ "$reply" =~ ^[Yy]$ ]] || exit 0

# Creat the admin user
while [[ -z "$admin_username" ]];
do
  read -p "Choose an administrator username: " admin_username
done

if ! id "$admin_username" > /dev/null 2>&1; then
  echo ""
  echo "Creating user account: $admin_username ..."
  echo ""
  sudo adduser "$admin_username" --gecos ""
  sudo adduser "$admin_username" sudo
fi

# Disable root login with password for SSH (if enabled)
if grep -Fq 'PermitRootLogin yes' /etc/ssh/sshd_config; then
  echo ""
  echo "Disabling root login for SSH ..."
  echo ""
  sudo sed -i 's/PermitRootLogin yes/PermitRootLogin prohibit-password/g' /etc/ssh/sshd_config
  sudo service sshd restart
fi

# Configure and enable firewall (if not already enabled)
if sudo ufw status | grep -qi inactive; then
  echo ""
  echo "Configuring firewall ..."
  echo ""
  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw allow ssh
  sudo ufw allow 2222 # SFTP Docker container
  sudo ufw allow http
  sudo ufw enable
fi

# Install docker and docker-compose (if not already installed)
if ! command docker -v > /dev/null 2>&1; then
  echo ""
  echo "Installing docker ..."
  echo ""
  sudo apt update
  sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
  # TODO: How to verify fingerprint automatically?
  sudo apt-key fingerprint 0EBFCD88
  sudo add-apt-repository \
    "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) \
    stable"
  sudo apt install -y docker-ce docker-ce-cli containerd.io
  sudo systemctl enable docker
fi

if ! command docker-compose -v > /dev/null 2>&1; then
  echo ""
  echo "Installing docker-compose ..."
  echo ""
  sudo curl -L \
    "https://github.com/docker/compose/releases/download/1.25.4/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
fi
