import os
import yaml
import json

import datetime
from pathlib import Path

from github import Github
from mako.template import Template

HERE = Path(__file__).parent.absolute()
TEMPLATES_PATH = HERE.joinpath('templates')

GH_PAT = os.environ.get('GH_PAT', None)
GH_ORG = 'ooi-data'
SITE_BRANCH = 'gh-pages'
STATUS_REPO = 'status'

IGNORE_REPOS = [
    'ooi-harvester',
    'staged-harvest',
    'helm-charts',
    'docker-images',
    'discrete-sample',
    'specification',
    'qaqc',
    'read-history-status-action',
    'PyGithub',
    'stream_template',
    'status',
    'sync-data-stream-action',
    'ooi-data.github.io'
]

STATUS_CLASSES = {
    'success': 'btn-success',
    'pending': 'btn-info',
    'failed': 'btn-danger',
}

TIME_STR = datetime.datetime.utcnow().isoformat()


def fetch_status(repo):
    status_dict = {'name': repo.name, 'request': None, 'process': None}
    for content in repo.get_contents('history'):
        if content.name == 'request.yaml':
            status_dict['request'] = yaml.load(
                content.decoded_content, Loader=yaml.SafeLoader
            )
        elif content.name == 'process.yaml':
            status_dict['process'] = yaml.load(
                content.decoded_content, Loader=yaml.SafeLoader
            )
    return status_dict


def file_exists(repo, file_path, branch):
    try:
        repo.get_contents(file_path, ref=branch)
        return True
    except Exception as e:
        if e.status == 404:
            return False
        raise


def write_status_json(org, all_status):
    status_repo = org.get_repo(STATUS_REPO)
    status_json_path = 'status.json'
    if file_exists(status_repo, status_json_path, SITE_BRANCH):
        contents = status_repo.get_contents(status_json_path, ref=SITE_BRANCH)
        status_repo.update_file(
            path=contents.path,
            message=f"⬆️ Updating status json file ({TIME_STR})",
            content=json.dumps(all_status),
            sha=contents.sha,
            branch=SITE_BRANCH,
        )
    else:
        status_repo.create_file(
            path=status_json_path,
            message=f"✨ Create status json file ({TIME_STR})",
            content=json.dumps(all_status),
            branch=SITE_BRANCH,
        )


def write_rendered_html(org, html):
    status_repo = org.get_repo(STATUS_REPO)
    status_html = 'index.html'
    if file_exists(status_repo, status_html, SITE_BRANCH):
        contents = status_repo.get_contents(status_html, ref=SITE_BRANCH)
        status_repo.update_file(
            path=contents.path,
            message=f"⬆️ Updating site html ({TIME_STR})",
            content=html,
            sha=contents.sha,
            branch=SITE_BRANCH,
        )
    else:
        status_repo.create_file(
            path=status_html,
            message=f"✨ Create site html ({TIME_STR})",
            content=html,
            branch=SITE_BRANCH,
        )


def main():
    gh = Github(GH_PAT)
    org = gh.get_organization(GH_ORG)

    print("1) Fetching repo status ...")
    all_status = []
    for repo in org.get_repos():
        if repo.name not in IGNORE_REPOS:
            try:
                status = fetch_status(repo)
                all_status.append(status)
            except Exception:
                print(
                    f"https://github.com/{repo.full_name} is not a data stream repository. Skipping ..."
                )
                continue

    print("2) Writing status json ...")
    write_status_json(org, all_status)

    template = Template(filename=str(TEMPLATES_PATH.joinpath('index.html')))
    rendered_html = template.render(
        data_streams=all_status, status_map=STATUS_CLASSES
    )
    print("3) Writing rendered html ...")
    write_rendered_html(org, rendered_html)

    print(f"4) Done. {datetime.datetime.utcnow().isoformat()}")


if __name__ == "__main__":
    # execute only if run as a script
    main()
