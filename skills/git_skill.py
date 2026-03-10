from git import Repo, exc
import os

class GitSkill:
    def __init__(self):
        self.name = "git_skill"
        
    def clone(self, url: str, target_dir: str) -> str:
        try:
            Repo.clone_from(url, target_dir)
            return f"Successfully cloned {url} to {target_dir}"
        except exc.GitCommandError as e:
            return f"Error cloning repo: {str(e)}"
            
    def commit_and_push(self, repo_path: str, message: str) -> str:
        try:
            repo = Repo(repo_path)
            if not repo.is_dirty(untracked_files=True):
                return "No changes to commit."
                
            repo.git.add('.')
            repo.index.commit(message)
            origin = repo.remote(name='origin')
            origin.push()
            return "Successfully committed and pushed changes."
        except Exception as e:
            return f"Error in commit/push: {str(e)}"
