from dotenv import load_dotenv
from threading import Thread
import subprocess
import requests
import asyncio
import base64
import json
import os
import re

load_dotenv()

API_TOKEN = os.environ["API_TOKEN"]
USERNAME = os.environ["USERNAME"]
EMAIL = os.environ["EMAIL"]
ORGANIZATION_NAME = os.environ["ORGANIZATION_NAME"]
WORKFLOW_BRANCH = os.environ["WORKFLOW_BRANCH"]

def modify_text(text, **kwargs):
	kwargs |= {
		"workflow_branch": WORKFLOW_BRANCH
	}
	for key in kwargs:
		text = text.replace("{" + key + "}", kwargs[key])
	return text

def write_text(path, text, **kwargs):
	with open(path, "w") as f:
		f.write(modify_text(text, **kwargs))

self_module = __import__(__name__)

def read_text(path, name):
	with open(path, "r") as f:
		setattr(self_module, name, f.read())
	if not hasattr(self_module, name):
		raise Exception(f"Failed to read {name}")

def read_list(path, name):
	try:
		with open(path, "r") as f:
			setattr(self_module, name, [l.strip() for l in f.readlines()])
	except FileNotFoundError:
		pass

read_text("workflow_files/cloneupdate.yml", "cloneupdate")
read_text("workflow_files/update.sh", "updater")
read_text("workflow_files/README.md", "readme")

API_HEADERS = {
	"Accept": "application/vnd.github+json",
	"Authorization": f"token {API_TOKEN}"
}

UPDATE_DATA = json.dumps({
	"default_branch": WORKFLOW_BRANCH
})

WORKFLOW_DATA = {
	"message": "Adding workflow",
}

WORKFLOW_DISPATCH_DATA = json.dumps({
	"ref": WORKFLOW_BRANCH
})

forked_repos = []
error_repos = []
auto_restart = False
running = False

read_list("forks.txt", "forked_repos")
read_list("errors.txt", "error_repos")

async def wait(seconds):
	await asyncio.sleep(seconds)

def RunWait(seconds=2):
	asyncio.run(wait(seconds))

def fork(owner, repo, description = None):
	print("Waiting 1 minute")
	RunWait(50)
	print(f"Forking {owner}/{repo}")
	RunWait()
	newname = f"{repo}-{owner}"
	body = {
		"name": newname if len(newname) <= 100 else repo,
		"description": f"Clone of https://github.com/{owner}/{repo}{(' - '+description) if description else ''}"
	}
	r = requests.post(f"https://api.github.com/orgs/KtaneModules/repos", data=json.dumps(body), headers=API_HEADERS)
	if not r:
		print("Failed to create fork: " + str(r.content))
		return False
	fork = json.loads(r.content)
	print("Adding workflow branch")
	fork_name = fork["name"]
	full_name = fork["full_name"]
	os.system(f'git clone https://github.com/{owner}/{repo} {fork_name} && cd {fork_name} && git remote add newfork https://github.com/{full_name} && git switch --orphan {WORKFLOW_BRANCH} && mkdir .github && cd .github && mkdir workflows')
	print(full_name)
	KWARGS = {
		"owner": owner,
		"repo": repo,
		"fullrepo": full_name
	}
	write_text(fork_name + "/update.sh", updater, **KWARGS)
	write_text(fork_name + "/README.md", readme, **KWARGS)
	os.system(f'cd {fork_name} && git config user.name {USERNAME} && git config user.email {EMAIL} && git add update.sh && git add README.md && git commit -m "Add workflow branch files" && git push https://{USERNAME}:{API_TOKEN}@github.com/KtaneModules/{fork["name"]}.git {WORKFLOW_BRANCH}')
	for branch in [l.split("/")[1] for l in [b.strip() for b in subprocess.check_output(f"cd {fork_name} && git branch -r", shell=True).decode("utf-8").split("\n") if b]][1:]:
		if branch==WORKFLOW_BRANCH or branch.startswith("HEAD"):
			continue
		print("Pushing " + branch)
		os.system(f'cd {fork_name} && git checkout {branch} && git push https://{USERNAME}:{API_TOKEN}@github.com/KtaneModules/{fork["name"]}.git {branch}')
	os.system(f'rm -rf {fork_name}')
	print("Setting default branch")
	RunWait()
	r = requests.patch(f'https://api.github.com/repos/{full_name}', data=UPDATE_DATA, headers=API_HEADERS)
	if not r:
		print("Failed to set default branch: " + str(r.content))
		return False
	print("Adding workflow")
	RunWait(10)
	r = requests.put(f'https://api.github.com/repos/{full_name}/contents/.github/workflows/cloneupdate.yml', data=json.dumps(WORKFLOW_DATA | {"content": base64.b64encode(bytes(modify_text(cloneupdate, **KWARGS), "utf-8")).decode("utf-8")}), headers=API_HEADERS)
	if not r:
		print("Failed to add workflow: " + str(r.content))
		return False
	print("Fork successful")
	return True

def fork_all():
	global running, auto_restart
	print("Forking repos")
	running = True
	while auto_restart:
		auto_restart = False
		r = requests.get("https://ktane.timwi.de/json/raw")
		if not r:
			print("Failed to fetch mods: " + str(r.content))
			return
		mods = json.loads(r.content)["KtaneModules"]
		for mod in mods:
			if "SourceUrl" in mod:
				for match in re.finditer(r"^https?:\/\/github\.com\/([^\/]+)\/([^\/\?]+)([\/\?].*?)?$", mod["SourceUrl"], re.I):
					owner = match.group(1)
					repo = match.group(2)
					if repo.lower().endswith(".git"):
						repo = repo[:-4]
					repo_name = f"{owner}/{repo}"
					repo_name_lower = repo_name.lower()
					print("Checking " + repo_name)
					if not repo_name_lower in forked_repos:
						RunWait()
						print("Checking if repo exists")
						r = requests.get(f"https://api.github.com/repos/{repo_name}", headers=API_HEADERS)
						if not r:
							print(f"Repo {repo_name} doesn't seem to exist: " + str(r.content))
							break
						RunWait()
						create_fork = True
						if create_fork and fork(owner, repo, json.loads(r.content)["description"]):
							forked_repos.append(repo_name_lower)
							with open("forks.txt", "a") as f:
								f.write(repo_name_lower+"\n")
						elif create_fork and repo_name_lower not in error_repos:
							error_repos.append(repo_name_lower)
							with open("errors.txt", "a") as f:
								f.write(repo_name_lower+"\n")
					else:
						print(f"Skiping {repo_name}")
					break
	running = False
	print("Forking complete")

def on_webhook():
	global auto_restart
	auto_restart = True
	if not running:
		Thread(target=fork_all).start()
