#!/bin/bash

git config user.name $USERNAME
git config user.email $EMAIL
git config checkout.defaultRemote origin
git fetch origin
git checkout master
git remote add upstream https://github.com/{owner}/{repo}
git fetch upstream
if [ $? -ne 0 ]; then
	echo "Failed to fetch the original repo, exiting..."
	exit 128
fi

containsElement () {
  local e match="$1"
  shift
  for e; do [[ "$e" == "$match" ]] && return 1; done
  return 0
}

ORIGIN=()
UPSTREAM=()

for branch in $(git branch -r | tr "\n" "\n"); do
  if [[ "$branch" != "->" && "$branch" != "origin/HEAD" && "$branch" != "upstream/{workflow_branch}" ]]; then
    ARR=($(echo "$branch" | tr "/" " "))
    if [[ "${ARR[0]}" == "origin" ]]; then
        ORIGIN+=("${ARR[1]}")
    else
        UPSTREAM+=("${ARR[1]}")
    fi
  fi
done

for branch in "${UPSTREAM[@]}"; do
    echo "Preparing $branch"
    containsElement "$branch" "${ORIGIN[@]}"
    if [ $? -eq 0 ]; then
        git switch --orphan $branch
    else
        git checkout $branch
    fi
    echo "Pushing $branch"
    git reset --hard upstream/$branch
    git push -f https://$USERNAME:$TOKEN@github.com/$REPOSITORY.git $branch
done
