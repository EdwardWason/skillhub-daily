#!/usr/bin/env python3
"""
GitHub API 文件上传脚本
绕过 git push，直接使用 GitHub REST API 创建/更新仓库文件
"""
import os
import sys
import base64
import json
import time
import requests

REPO_OWNER = "EdwardWason"
REPO_NAME = "skillhub-daily"
BASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents"

# 需要忽略的文件/目录
IGNORED = {'.git', '__pycache__', '.pyc', '.env.local', 'node_modules', '.zip'}

def get_token():
    token = os.environ.get('GH_TOKEN')
    if not token:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.local')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('GH_TOKEN='):
                        token = line.strip().split('=', 1)[1]
                        break
    return token

def file_exists(path, token):
    url = f"{BASE_URL}/{path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code == 200:
        return r.json().get('sha')
    return None

def upload_file(local_path, repo_path, token):
    with open(local_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode('utf-8')

    url = f"{BASE_URL}/{repo_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    data = {
        "message": f"Upload {repo_path}",
        "content": content,
        "branch": "main"
    }

    sha = file_exists(repo_path, token)
    if sha:
        data["sha"] = sha
        data["message"] = f"Update {repo_path}"

    r = requests.put(url, headers=headers, json=data, timeout=60)
    if r.status_code in (200, 201):
        print(f"  ✅ {'Updated' if sha else 'Created'}: {repo_path}")
        return True
    else:
        print(f"  ❌ Failed ({r.status_code}): {repo_path} - {r.text[:200]}")
        return False

def should_ignore(rel_path):
    parts = rel_path.replace('\\', '/').split('/')
    for part in parts:
        if part.startswith('.git') or part in IGNORED or part.endswith('.zip'):
            return True
    return False

def main():
    token = get_token()
    if not token:
        print("❌ GH_TOKEN not found")
        sys.exit(1)

    # 验证 token
    r = requests.get("https://api.github.com/user", headers={"Authorization": f"token {token}"}, timeout=30)
    if r.status_code != 200:
        print(f"❌ Token invalid: {r.status_code}")
        sys.exit(1)
    print(f"✅ Token valid: {r.json().get('login')}")

    # 获取仓库根目录
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"📁 Uploading from: {repo_root}")

    success = 0
    failed = 0

    for root, dirs, files in os.walk(repo_root):
        # 跳过 .git 目录
        dirs[:] = [d for d in dirs if not d.startswith('.git') and d not in IGNORED]

        for file in files:
            if file.endswith('.zip') or file in IGNORED:
                continue

            local_path = os.path.join(root, file)
            rel_path = os.path.relpath(local_path, repo_root).replace('\\', '/')

            if should_ignore(rel_path):
                continue

            print(f"⬆️  {rel_path} ...", end='', flush=True)
            if upload_file(local_path, rel_path, token):
                success += 1
            else:
                failed += 1
            time.sleep(0.5)  # 避免速率限制

    print(f"\n🎉 Done! Success: {success}, Failed: {failed}")

if __name__ == '__main__':
    main()
