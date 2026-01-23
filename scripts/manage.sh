#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PLAYBOOK="$ROOT_DIR/ansible/site.yml"
INVENTORY="$ROOT_DIR/ansible/inventory.yml"

require_ansible() {
  if ! command -v ansible-playbook >/dev/null 2>&1; then
    echo "Installing Ansible..."
    sudo apt-get update
    sudo apt-get install -y ansible
  fi

  local required_collection="community.general"
  local required_version="1.3.6"

  if ansible-galaxy collection list "$required_collection" 2>/dev/null \
     | grep -q "$required_collection.*$required_version"; then
    return 0
  fi

  echo "Installing ${required_collection}:${required_version}..."
  ansible-galaxy collection install \
    "${required_collection}:${required_version}"
}

ensure_ansible() {
  if ! command -v ansible-playbook >/dev/null 2>&1; then
    echo "Ansible not found. Run ./manage.sh setup first."
    exit 2
  fi
}

run_playbook() {
  local -a args=("$@")
  ansible-playbook -i "$INVENTORY" "$PLAYBOOK" "${args[@]}" --become
}

usage() {
  cat <<'EOF'
Usage:
  ./manage.sh setup                       Install Ansible and run complete server setup.
  ./manage.sh sync [--check]              Apply config (or check current state with --check).
  ./manage.sh add-user <username>         Add user.
EOF
}

cmd="${1:-}"
shift || true

case "$cmd" in
  setup)
    require_ansible
    run_playbook
    ;;
  sync)
    ensure_ansible
    if [[ "${1:-}" == "--check" ]]; then
      run_playbook --check --diff
    elif [[ -z "${1:-}" ]]; then
      run_playbook
    else
      echo "Unknown flag for sync: ${1:-}"
      usage
      exit 2
    fi
    ;;
  add-user)
    user="${1:-}"
    [[ -n "$user" ]] || { echo "Missing username"; usage; exit 2; }
    ensure_ansible
    run_playbook --tags adduser -e "new_user=$user"
    ;;
  ""|help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $cmd"
    usage
    exit 2
    ;;
esac
