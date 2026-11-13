#!/usr/bin/env python3
"""Resolve an official release and inspect public Docker Hub manifests."""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

UPSTREAM = 'anywhere-labs/Agents-Anywhere'
ACCEPT = ', '.join([
    'application/vnd.oci.image.index.v1+json',
    'application/vnd.docker.distribution.manifest.list.v2+json',
    'application/vnd.oci.image.manifest.v1+json',
    'application/vnd.docker.distribution.manifest.v2+json',
])


def github(path):
    request = urllib.request.Request(
        'https://api.github.com/' + path,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28'},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def manifest_digest(image, tag):
    query = urllib.parse.urlencode({'service': 'registry.docker.io',
                                   'scope': f'repository:{image}:pull'})
    with urllib.request.urlopen('https://auth.docker.io/token?' + query, timeout=60) as response:
        token = json.load(response)['token']
    request = urllib.request.Request(
        f'https://registry-1.docker.io/v2/{image}/manifests/{tag}',
        method='HEAD', headers={'Authorization': 'Bearer ' + token, 'Accept': ACCEPT},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.headers['Docker-Content-Digest']
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return ''
        raise RuntimeError(f'Cannot inspect public Docker Hub image {image}:{tag}: HTTP {error.code}. '
                           'Ensure the repository exists and is public.') from error


def main():
    username = os.environ.get('DOCKERHUB_USERNAME', '').strip().lower()
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', username):
        raise SystemExit('Set repository variable DOCKERHUB_USERNAME to your Docker Hub namespace.')
    image = username + '/agents-anywhere'
    latest = github(f'repos/{UPSTREAM}/releases/latest')
    requested = os.environ.get('REQUESTED_VERSION', '').strip()
    if requested and not re.fullmatch(r'v?\d+\.\d+\.\d+', requested):
        raise SystemExit('Version must be an official stable tag such as v2.1.0.')
    tag = ('v' + requested.removeprefix('v')) if requested else latest['tag_name']
    if not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
        raise SystemExit('Upstream latest release is not a supported stable semver tag.')
    release = github(f'repos/{UPSTREAM}/releases/tags/{tag}')
    if release['draft'] or release['prerelease']:
        raise SystemExit('Only published stable releases are supported.')
    obj = github(f'repos/{UPSTREAM}/git/ref/tags/{tag}')['object']
    for _ in range(8):
        if obj['type'] == 'commit':
            break
        if obj['type'] != 'tag':
            raise SystemExit('Release tag does not point to a commit.')
        obj = github(f'repos/{UPSTREAM}/git/tags/{obj["sha"]}')['object']
    if obj['type'] != 'commit' or not re.fullmatch(r'[0-9a-f]{40}', obj['sha']):
        raise SystemExit('Unable to resolve an immutable upstream commit.')
    version = tag.removeprefix('v')
    digest = manifest_digest(image, version)
    is_latest = tag == latest['tag_name']
    alias_digest = manifest_digest(image, 'latest') if is_latest and digest else ''
    outputs = {'tag': tag, 'version': version, 'sha': obj['sha'], 'image': image,
               'build': str(not bool(digest)).lower(), 'latest': str(is_latest).lower(),
               'promote': str(bool(digest) and is_latest and alias_digest != digest).lower()}
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.writelines(f'{key}={value}\n' for key, value in outputs.items())
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
        summary.write(f'## Release check\n\n- Upstream: `{tag}` (`{obj["sha"]}`)\n'
                      f'- Image: `{image}:{version}`\n'
                      f'- New build required: `{outputs["build"]}`\n'
                      f'- Repair latest alias: `{outputs["promote"]}`\n')


if __name__ == '__main__':
    main()
