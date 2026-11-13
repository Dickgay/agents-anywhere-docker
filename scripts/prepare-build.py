#!/usr/bin/env python3
"""Preserve upstream license notices inside the final server image."""
from pathlib import Path
import shutil

root = Path('upstream')
source = root / 'docker/Dockerfile'
text = source.read_text()
license_path = root / 'LICENSE'
if not license_path.is_file():
    # v2.1.0 declares MIT in its root README and carries the full matching
    # project copyright/license in dsh-bridge/LICENSE, before root LICENSE existed.
    readme = (root / 'README.md').read_text()
    legacy_license = root / 'dsh-bridge/LICENSE'
    if '## 开源许可\n\nMIT。' not in readme or not legacy_license.is_file():
        raise SystemExit('No recognized upstream license declaration was found.')
    legacy_text = legacy_license.read_text()
    if not legacy_text.startswith('MIT License\n') or 'Agents Anywhere Contributors' not in legacy_text:
        raise SystemExit('Legacy project license is not the expected MIT notice.')
    shutil.copyfile(legacy_license, license_path)
license_text = license_path.read_text()
if 'Apache License' in license_text and 'Version 2.0' in license_text:
    spdx = 'Apache-2.0'
elif license_text.startswith('MIT License\n'):
    spdx = 'MIT'
else:
    raise SystemExit('Unrecognized upstream license; review before publishing.')
files = ['LICENSE']
if (root / 'NOTICE').is_file():
    files.append('NOTICE')
text += '\nCOPY ' + ' '.join(files) + ' /usr/share/licenses/agents-anywhere/\n'
text += f'LABEL org.opencontainers.image.licenses="{spdx}"\n'
(root / 'docker/Dockerfile.publish').write_text(text)
print(f'Prepared upstream license and notices: {spdx}')
