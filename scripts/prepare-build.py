#!/usr/bin/env python3
"""Preserve upstream license notices inside the final server image."""
from pathlib import Path

root = Path('upstream')
source = root / 'docker/Dockerfile'
text = source.read_text()
if not (root / 'LICENSE').is_file():
    raise SystemExit('Upstream LICENSE is missing.')
files = ['LICENSE']
if (root / 'NOTICE').is_file():
    files.append('NOTICE')
text += '\nCOPY ' + ' '.join(files) + ' /usr/share/licenses/agents-anywhere/\n'
text += 'LABEL org.opencontainers.image.licenses="Apache-2.0"\n'
(root / 'docker/Dockerfile.publish').write_text(text)
