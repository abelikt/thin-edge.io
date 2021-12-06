#!/usr/bin/python3
"""Download latest thin-edge build artifacts from GitHub.

In order to run it often, you need a GitHub token set to $THEGHTOKEN.
See https://github.com/settings/tokens to generate a token with repo, workflow scope.

See also here
https://docs.github.com/en/rest/reference/actions#download-an-artifact
"""

import argparse
import json
import os
import os.path
import requests
from requests.auth import HTTPBasicAuth


def download_artifact(
    url: str, name: str, token: str, user: str, workflowname: str, output: str = None
) -> None:
    """Download the artifact and store it as a zip file"""

    assert workflowname.endswith(".yml")

    headers = {"Accept": "application/vnd.github.v3+json"}

    auth = HTTPBasicAuth(user, token)

    print(f"Will try file {name}.zip")

    workflowname = os.path.splitext(workflowname)[0]

    if output:
        artifact_filename = os.path.splitext(os.path.basename(output))[0] + ".zip"
    else:
        artifact_filename = f"{workflowname}_{name}.zip"

    if os.path.exists(artifact_filename):
        print(f"Skipped {artifact_filename} as it is already there")
        # raise SystemError("File already there!")
        return

    req = requests.get(url, auth=auth, headers=headers, stream=True)

    with open(os.path.expanduser(artifact_filename), "wb") as thefile:
        for chunk in req.iter_content(chunk_size=128):
            thefile.write(chunk)
        print(f"Downloaded {name}.zip as {artifact_filename}")


def get_artifacts_for_runid(
    runid: int,
    token: str,
    user: str,
    myfilter: str,
    workflowname: str,
    output: str = None,
) -> None:
    """Download artifacts for a given runid"""

    print("Getting artifacts of workflow")

    url = f"https://api.github.com/repos/{user}/thin-edge.io/actions/runs/{runid}/artifacts"
    headers = {"Accept": "application/vnd.github.v3+json"}

    auth = HTTPBasicAuth(user, token)

    req = requests.get(url, auth=auth, headers=headers)
    if not req.status_code == 200:
        print("Status code:", req.status_code)
        raise SystemError

    text = json.loads(req.text)

    # print(json.dumps(text, indent='  '))

    artifacts = text["artifacts"]

    print(f"Found {len(artifacts)} artifacts")

    for artifact in artifacts:
        artifact_name = artifact["name"]
        artifact_url = artifact["archive_download_url"]
        # print(artifact_name, artifact_url)
        print("Found:", artifact_name)
        if myfilter is None:
            download_artifact(
                artifact_url, artifact_name, token, user, workflowname, output
            )
        elif artifact_name.startswith(myfilter):
            download_artifact(
                artifact_url, artifact_name, token, user, workflowname, output
            )
        else:
            pass  # skip that file


def get_workflow(token: str, user: str, name: str) -> int:
    """
    Derive the last run ID of a GitHub workflow.

    :param token: GitHub token
    :param user: GitHub user name
    :param name: Name of the workflow
    :return: ID of the workflow
    """

    print(f"Getting id of last execution of workflow {name}")

    assert name.endswith(".yml")

    headers = {"Accept": "application/vnd.github.v3+json"}
    auth = HTTPBasicAuth(user, token)
    index = 0  # Hint: 0 and 1 seem to have an identical meaning when we request
    param = {"per_page": 1, "page": index}

    # first request:
    url = f"https://api.github.com/repos/{user}/thin-edge.io/actions/workflows/{name}"
    req = requests.get(url, params=param, auth=auth, headers=headers)

    stuff = json.loads(req.text)

    # print(json.dumps(stuff, indent='  '))

    wfid = stuff.get("id")
    if not wfid:
        raise SystemError(stuff)

    # print(stuff.get('id'))

    print(f"ID of workflow {name} is {wfid}")

    return wfid


def get_valid_run(wfid: int, token: str, user: str, name: str, state: str) -> int:

    # second request:

    index = 0  # Hint: 0 and 1 seem to have an identical meaning when we request
    found = False
    headers = {"Accept": "application/vnd.github.v3+json"}
    auth = HTTPBasicAuth(user, token)

    url = f"https://api.github.com/repos/{user}/thin-edge.io/actions/workflows/{wfid}/runs"

    print("Getting execution of workflow")

    while not found:
        param = {"per_page": 1, "page": index}
        req = requests.get(url, params=param, auth=auth, headers=headers)
        stuff = json.loads(req.text)

        # print(json.dumps(stuff, indent='  '))

        if not stuff.get("workflow_runs"):
            print("GOT ERROR:")
            print(json.dumps(stuff, indent="  "))
            raise SystemError

        workflowname = stuff["workflow_runs"][0]["name"]
        wfrunid = int(stuff["workflow_runs"][0]["id"])
        wfrun = stuff["workflow_runs"][0]["run_number"]
        conclusion = stuff["workflow_runs"][0]["conclusion"]
        print("Workflow   : ", workflowname)
        print("Conclusion : ", conclusion)
        print("ID         : ", wfrunid)
        print("Run        : ", wfrun)
        print("Status     :", stuff["workflow_runs"][0]["status"])
        print("Creation   :", stuff["workflow_runs"][0]["created_at"])
        # print(stuff['workflow_runs'][0]['artifacts_url'])

        filename = f"{workflowname}_{wfrun}.json"
        with open(filename, "w") as thefile:
            thefile.write(json.dumps(stuff, indent="  "))

        if state == conclusion:
            found = True
        else:
            print(f"Workflow conclusion was {conclusion}. Trying an older one ...")
            index += 1

    return wfrunid


def main():
    """main entry point"""

    parser = argparse.ArgumentParser()
    parser.add_argument("username", type=str, help="GitHub Username")
    parser.add_argument("workflowname", type=str, help="Name of workflow")
    parser.add_argument(
        "--filter", type=str, help="Download only files starting with ..."
    )
    parser.add_argument("-o", "--output", type=str, help="File to store the result to.")
    args = parser.parse_args()

    username = args.username
    workflowname = os.path.basename(args.workflowname)
    myfilter = args.filter
    output = args.output

    token = None

    if "THEGHTOKEN" in os.environ:
        token = os.environ["THEGHTOKEN"]
    else:
        print("Warning: Environment variable THEGHTOKEN not set")

    wfid = get_workflow(token, username, workflowname)

    runid = get_valid_run(wfid, token, username, workflowname, "success")

    get_artifacts_for_runid(runid, token, username, myfilter, workflowname, output)


if __name__ == "__main__":
    main()
