"""語言目錄共用工具；保護路徑與插值規則與 validate.py 一致。"""
import json
import re
from pathlib import Path

MAX_STRING_LENGTH = 8192
MAX_CATALOG_ENTRIES = 50000
PROTECTED_ROOT = "auto.components.settings."
PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}|(?<!\{)\{[A-Za-z_][A-Za-z0-9_]*\}(?!\})")


def is_protected(key, exempt):
    if any(key.startswith(prefix) for prefix in getattr(exempt, "protected_prefixes", ())):
        return True
    candidate = key
    protected_keys = getattr(exempt, "protected_keys", set())
    while candidate:
        if candidate in protected_keys or re.sub(r"_(?:zero|one|two|few|many|other)$", "", candidate) in protected_keys:
            return True
        candidate = candidate.rpartition(".")[0]
    if not key.startswith(PROTECTED_ROOT) or key in exempt:
        return False
    return key[len(PROTECTED_ROOT):].lower().startswith("plugin")


def flatten(tree, prefix="", depth=1, stats=None):
    if stats is not None:
        stats["depth"] = max(stats["depth"], depth)
    out = {}
    for key, value in tree.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, path, depth + 1, stats))
        else:
            out[path] = value
    return out


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, tree):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tree, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ChromeExemptions(set):
    """舊版 chrome 例外清單，加上新版獨立的保護文案清單。"""

    def __init__(self, values, protected_keys=(), protected_prefixes=()):
        super().__init__(values)
        self.protected_keys = set(protected_keys)
        self.protected_prefixes = tuple(protected_prefixes)


def read_exempt(path):
    path = Path(path)
    values = re.findall(r"'(auto\.components\.settings\.[^']+)'", path.read_text(encoding="utf-8"))
    protected_path = path.with_name("protected-copy-keys.json")
    protected = read_json(protected_path) if protected_path.is_file() else {}
    return ChromeExemptions(values, protected.get("keys", ()), protected.get("prefixes", ()))


def put(tree, key, value, reference):
    """保留既有順序；新鍵放在英文中下一個既有同層鍵之前。"""
    parts = key.split(".")
    node, source = tree, reference
    for index, part in enumerate(parts):
        if not isinstance(node, dict):
            raise ValueError("路徑與既有字串衝突")
        last = index == len(parts) - 1
        if part not in node:
            order = list(source) if isinstance(source, dict) else []
            following = order[order.index(part) + 1:] if part in order else []
            anchor = next((k for k in following if k in node), None)
            items = list(node.items())
            node.clear()
            for name, old in items:
                if name == anchor:
                    node[part] = value if last else {}
                node[name] = old
            if part not in node:
                node[part] = value if last else {}
        elif last:
            if isinstance(node[part], dict):
                raise ValueError("路徑與既有物件衝突")
            node[part] = value
        if not last:
            node = node[part]
            source = source.get(part, {}) if isinstance(source, dict) else {}


def remove(tree, key):
    parts = key.split(".")
    node = tree
    parents = []
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node:
            return
        parents.append((node, part))
        node = node[part]
    if not isinstance(node, dict):
        return
    node.pop(parts[-1], None)
    for parent, part in reversed(parents):
        if parent[part]:
            break
        del parent[part]
