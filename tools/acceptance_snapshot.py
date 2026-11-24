"""Read-only stable-snapshot recovery for the independent-process acceptance harness."""
import json
import subprocess
import sys
from tools import install, session

def recover_stable(api, target, requested=None, attempts=3):
    if type(attempts) is not int or not 1 <= attempts <= 3:
        raise ValueError("Acceptance attempts must be between 1 and 3")
    prefix = install.repo_path(target)
    for _ in range(attempts):
        state = session.load(api, target)
        report = session.inspect(api, state, requested=requested)
        args = [sys.executable,"-m","tools.session","--target",target,"--expected-sha",state["ref"],"inspect"]
        if requested is not None:
            args += ["--issue",str(requested)]
        result = subprocess.run(args,capture_output=True,text=True,check=False)
        if result.returncode:
            # Never suppress other failures or accept a stale snapshot.
            if ("Installed branch has advanced; reload before acting" in result.stderr
                    and install.read_ref(api,prefix,install.BRANCH) != state["ref"]):
                continue
            raise RuntimeError(result.stderr.strip())
        second = json.loads(result.stdout)
        if second != report:
            # Product or issue metadata may also move. Only a demonstrated installed-ref
            # advance permits a reload here; other discrepancies fail closed.
            if install.read_ref(api,prefix,install.BRANCH) != state["ref"]:
                continue
            raise ValueError("Independent process did not agree at the same installed revision")
        if install.read_ref(api,prefix,install.BRANCH) != state["ref"]:
            continue
        return state,report
    raise ValueError("Adopter state did not stabilize within the bounded acceptance attempts")
