"""Narrow Phase 4 acceptance helpers; not part of the installed VIB package."""
from tools import install, session


def ensure_recovery_ref(api, prefix, final):
    """Create once, or reuse an exact prior recovery ref. Never overwrite or retry a POST."""
    install.require(install.SHA, final, "recovery revision")
    name = "archive/vib-recovery/" + final
    existing = install.read_ref(api, prefix, name)
    if existing is None:
        api.request("POST", prefix + "/git/refs", {"ref": "refs/heads/" + name, "sha": final})
        install.wait_ref(api, prefix, name, final)
    elif existing != final:
        raise ValueError("Recovery ref is occupied by another revision")
    if install.read_ref(api, prefix, name) != final:
        raise ValueError("Recovery ref changed; inspect before resuming")
    return name


def verify_self_install(api, target, source):
    """Read-only plan on an empty slot, or verify an existing pinned installation."""
    prefix = install.repo_path(target)
    before = install.read_ref(api, prefix, "main")
    if before is None:
        raise ValueError("Product main is missing")
    installed = install.read_ref(api, prefix, install.BRANCH)
    candidate_paths = sorted(set(install.source_files(api, source)) |
                             {"vib-install.json", session.LEDGER, session.HANDOFF})
    if installed is None:
        plan = install.install(api, target, source, "v0.0.0")
        if (plan["status"] != "planned" or plan["manifest"]["product_baseline_sha"] != before
                or plan["manifest"]["enforcement"] != "disabled" or plan["paths"] != candidate_paths):
            raise ValueError("Unexpected self-install plan")
        report = {"mode": "read_only_plan", "installed_sha": None,
                  "installed_source": None, "install_plan_paths": plan["paths"]}
    else:
        state = session.load(api, target, installed)
        if state["manifest"]["enforcement"] != "disabled" or state["product_sha"] != before:
            raise ValueError("Unexpected self-install state")
        try:
            install.install(api, target, source, "v0.0.0")
        except ValueError as exc:
            if "Install branch already exists" not in str(exc):
                raise
        else:
            raise ValueError("Occupied self-install was not refused")
        report = {"mode": "existing_install_verified", "installed_sha": installed,
                  "installed_source": state["manifest"]["source_sha"],
                  "install_plan_paths": None, "duplicate_install_refused": True}
    if install.read_ref(api, prefix, install.BRANCH) != installed or install.read_ref(api, prefix, "main") != before:
        raise ValueError("Self-install or product main changed; inspect before resuming")
    return {**report, "candidate_package_paths": candidate_paths, "product_sha": before}
