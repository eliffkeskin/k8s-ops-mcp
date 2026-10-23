from openai import OpenAI, APIConnectionError
import sys
import requests
import os
import time

SYSTEM_PROMPT = "You are a code-reviewer. Only list the problems. Don't write any code, create any command, and JSON. The answers will be plain text."

def log(level, msg):

    if level == "error":
        print(f"[{level}] {msg}", file=sys.stderr)
    else:
        print(f"[{level}] {msg}")

def parse_diff(text):
    added = 0
    files = []

    for line in text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        if line.startswith("diff --git"):
            file_name = line.split()[-1]
            file_name = file_name.split("/", 1)[1]
            files.append(file_name)   
    
    return added, files

def get_diff(repo, number, token):

    base = f"https://api.github.com/repos/{repo}"
    url = f"{base}/pulls/{number}"
    headers = {"Accept": "application/vnd.github.diff",
                "Authorization": f"Bearer {token}"}
    try:
        response_get = requests.get(url, headers=headers)
        response_get.raise_for_status()
        diff_text = response_get.text
        added, files = parse_diff(diff_text)

        log("info", f"diff is fetched: {len(files)} file {added} lines are added.")
        return diff_text
    except requests.exceptions.HTTPError as e:
        log("error", e.response.status_code)
        sys.exit(1)

def review(diff_text):

    start = time.time()
    model = os.environ.get("REVIEW_MODEL")
    base_url = os.environ.get("OLLAMA_BASE_URL")
    try:
        client = OpenAI(base_url=base_url, api_key="ollama")
        response = client.chat.completions.create(model=model, messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Please review this git diff:\n{diff_text}"}
        ], temperature=0
        )
        content = response.choices[0].message.content
        elapsed = time.time()-start
        log("info", f"model= {model}")
        log("info", f"review is completed ({len(content.splitlines())} lines {elapsed:.2f} s)")
        return content
    except APIConnectionError as e:
        log("error", f"{e}")
        sys.exit(1)


def post_comment(repo, number, token, body):

    base = f"https://api.github.com/repos/{repo}"
    url = f"{base}/issues/{number}/comments"

    headers = {"Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}"}
    try:
        response_post = requests.post(    
            url= url,
            json={'body': body},
            headers=headers
            )
        response_post.raise_for_status()
        comment = response_post.json()
        log("info", f"comment is added: {comment['html_url']}.")
    except requests.exceptions.HTTPError as e:
        log("error", e.response.status_code)
        sys.exit(1)

def main():

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")

    if token is None:
        log("error", "GITHUB_TOKEN is not set")
        sys.exit(1)
    
    if repo is None:
        log("error", "GITHUB_REPOSITORY is not set")
        sys.exit(1)

    if len(sys.argv) <2:
        log("error", "PR is not defined.")
        sys.exit(1)

    number = sys.argv[1]
    log("info", f"repo= {repo}")

    diff_text = get_diff(repo, number, token)

    content = review(diff_text)

    dry_run = "--dry-run"

    if dry_run in sys.argv:
        print(content)
    else:
        post_comment(repo, number, token, content)


if __name__ == "__main__":
    main()




