"""查询实际运行依赖版本的 PyPI 漏洞元数据，不读取应用凭证。"""

import concurrent.futures
import importlib.metadata
import json
from pathlib import Path
from urllib.request import urlopen

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def dependencies():
    roots = []
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            roots.append(Requirement(line).name)
    versions = {"waitress": "3.0.2"}
    pending = roots[:]
    while pending:
        name = pending.pop().lower().replace("_", "-")
        if name in versions:
            continue
        distribution = importlib.metadata.distribution(name)
        versions[name] = distribution.version
        for item in distribution.requires or []:
            requirement = Requirement(item)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
    return versions


def check(item):
    name, version = item
    try:
        with urlopen(f"https://pypi.org/pypi/{name}/{version}/json", timeout=20) as response:
            data = json.load(response)
        return {
            "name": name,
            "version": version,
            "vulnerabilities": data.get("vulnerabilities", []),
        }
    except Exception as exc:
        return {"name": name, "version": version, "error": type(exc).__name__}


if __name__ == "__main__":
    versions = dependencies()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check, sorted(versions.items())))
    destination = ROOT / ".test-artifacts" / "python-security.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    vulnerable = [item for item in results if item.get("vulnerabilities")]
    failed = [item for item in results if item.get("error")]
    print(
        json.dumps(
            {
                "checked": len(results),
                "vulnerable": [
                    {
                        "name": item["name"],
                        "version": item["version"],
                        "advisories": [
                            {
                                "id": entry["id"],
                                "fixed_versions": entry.get("fixed_in", []),
                                "summary": entry.get("summary", ""),
                            }
                            for entry in item["vulnerabilities"]
                        ],
                    }
                    for item in vulnerable
                ],
                "failed": failed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
