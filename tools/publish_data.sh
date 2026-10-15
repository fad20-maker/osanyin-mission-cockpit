#!/usr/bin/env bash
# Publie les données chiffrées de la vitrine sur la branche « donnees ».
# Usage : CODE=<code d'accès> bash tools/publish_data.sh <dossier_instantane> [message]
# Ne pousse JAMAIS sur main : chaque publication sur main consomme le quota Netlify.
set -euo pipefail
SNAP="$1"; MSG="${2:-Mise à jour des données}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
: "${CODE:?variable CODE absente}"
WORK="$(mktemp -d)"
git clone -q --depth 1 --branch donnees https://github.com/fad20-maker/osanyin-mission-cockpit "$WORK/donnees"
python3 "$HERE/tools/export.py" "$SNAP" "$CODE" "$WORK/donnees" >/dev/null
cd "$WORK/donnees"
git config user.name "Coordination Osanyin"
git config user.email "fad20-maker@users.noreply.github.com"
git add data.enc.json
if git diff --cached --quiet; then echo "Aucun changement de données."; exit 0; fi
git commit -q -m "$MSG"
for i in 1 2 3; do
  if git push -q origin donnees; then echo "Données publiées."; exit 0; fi
  git pull -q --rebase origin donnees || true; sleep 5
done
echo "Échec de la publication des données." >&2; exit 1
