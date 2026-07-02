#!/usr/bin/env bash
# Bootstrap ASMP host layout + minimal registry on macOS/Linux.
# Usage: curl -fsSL https://raw.githubusercontent.com/agent-service-manifest-protocol/agent-service-manifest-protocol/main/scripts/bootstrap-asmp.sh | bash
set -euo pipefail

ASMP_DIR="${HOME}/.asmp"
SERVICES_DIR="${ASMP_DIR}/services"
HOST_FILE="${ASMP_DIR}/host.yaml"
INSTALL_DIR="${ASMP_DIR}/bin"
SERVE_PY="${INSTALL_DIR}/asmp-serve.py"
CLI_PY="${INSTALL_DIR}/asmp"
REPO_RAW="https://raw.githubusercontent.com/agent-service-manifest-protocol/agent-service-manifest-protocol/main"

echo "→ ASMP bootstrap"

command -v python3 >/dev/null || { echo "python3 required"; exit 1; }
python3 -c "import yaml" 2>/dev/null || python3 -m pip install --user pyyaml

mkdir -p "${SERVICES_DIR}" "${INSTALL_DIR}"

if [[ ! -f "${HOST_FILE}" ]]; then
  cat > "${HOST_FILE}" <<'EOF'
asmp: "0.1"
kind: host

host_id: "my-machine"
device_class: personal_computer

registry:
  path: ~/.asmp/services/
  api: http://127.0.0.1:7700

policy:
  agent_can_register: true
  requires_approval: false
  max_services: 100
  allowed_ports: "7000-9999"

discovery:
  scan_paths:
    - ~/repos-personal
    - ~/repos-aic
    - ~/repos-eidos-agi
  scan_interval: 5m
  stale_after: 900
EOF
  echo "✓ Wrote ${HOST_FILE}"
else
  echo "· ${HOST_FILE} already exists — kept"
fi

curl -fsSL "${REPO_RAW}/scripts/asmp-serve.py" -o "${SERVE_PY}"
curl -fsSL "${REPO_RAW}/scripts/asmp" -o "${CLI_PY}"
chmod +x "${SERVE_PY}" "${CLI_PY}"
echo "✓ Installed ${SERVE_PY}"
echo "✓ Installed ${CLI_PY}"

if curl -fsS "http://127.0.0.1:7700/health" >/dev/null 2>&1; then
  echo "✓ Registry already running on :7700"
else
  echo "→ Starting registry in background..."
  nohup python3 "${SERVE_PY}" >> "${HOME}/.asmp/asmp-registry.log" 2>&1 &
  sleep 1
  if curl -fsS "http://127.0.0.1:7700/health" >/dev/null 2>&1; then
    echo "✓ Registry listening on http://127.0.0.1:7700"
  else
    echo "! Registry did not respond yet — check ${HOME}/.asmp/asmp-registry.log"
  fi
fi

echo ""
echo "CLI (add ~/.asmp/bin to PATH if needed):"
echo "  asmp health"
echo "  asmp list"
echo "  asmp find --capability email.ingest"
echo "  asmp scan"
echo "  asmp litmus"
echo ""
echo "Litmus:"
echo "  asmp litmus"
echo ""
echo "Ship with software: add asmp.yaml at repo root — scanner finds it automatically."
echo "  https://agentservicemanifest.io/docs/spec/ship-with-software"
echo ""
echo "Next: wire MCP so agents discover services in every session"
echo "  https://agentservicemanifest.io/docs/install#agent-prompt"