# [{repo} (By {owner})](https://github.com/{owner}/{repo})

Unfortunately the way GitHub triggers workflows doesn't allow them to run on a schedule on a non-default branch. So this branch ({workflow_branch}) has to be the default. Switch to a different branch to see the source code of the mod (for ex. master -> the master branch of the mod)

To recover lost commits, use the commit hashes from [GitHub's reflog](https://api.github.com/repos/{fullrepo}/events) (add `?per_page=#&page=#` to the log URL to increase the page size (maximum is 100, default is 30) and/or specify the page number (default is 1)).
