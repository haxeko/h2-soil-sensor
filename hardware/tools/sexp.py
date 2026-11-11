"""Minimal S-expression reader/writer for KiCad files.

Quoted strings are returned as QStr so they can be written back with quotes;
bare atoms are plain str.  Lists are Python lists.
"""
from __future__ import annotations


class QStr(str):
    """A string that must be quoted when serialised."""


def _tokenize(text: str):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == "(" or c == ")":
            yield c
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                ch = text[j]
                if ch == "\\" and j + 1 < n:
                    nxt = text[j + 1]
                    buf.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, "\\" + nxt))
                    j += 2
                    continue
                if ch == '"':
                    break
                buf.append(ch)
                j += 1
            yield QStr("".join(buf))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n()":
                j += 1
            yield text[i:j]
            i = j


def loads(text: str):
    stack: list[list] = []
    root = None
    for tok in _tokenize(text):
        if tok == "(" and not isinstance(tok, QStr):
            stack.append([])
        elif tok == ")" and not isinstance(tok, QStr):
            node = stack.pop()
            if stack:
                stack[-1].append(node)
            else:
                root = node
        else:
            stack[-1].append(tok)
    return root


def _fmt_atom(a) -> str:
    if isinstance(a, QStr):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(a, float):
        s = f"{a:.6f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(a)


def dumps(node, indent: int = 0) -> str:
    """Serialise with a KiCad-like layout: short lists inline, long lists broken."""
    if not isinstance(node, list):
        return _fmt_atom(node)
    parts = [dumps(x, indent + 1) for x in node]
    inline = "(" + " ".join(parts) + ")"
    if len(inline) + indent * 2 <= 110 and "\n" not in inline:
        return inline
    head = []
    rest = []
    for idx, x in enumerate(node):
        if not rest and not isinstance(x, list):
            head.append(_fmt_atom(x))
        else:
            rest.append(x)
    out = "(" + " ".join(head)
    pad = "  " * (indent + 1)
    for x in rest:
        out += "\n" + pad + dumps(x, indent + 1)
    out += "\n" + "  " * indent + ")"
    return out


def find(node, key):
    """Return first child list whose head == key."""
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def find_all(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]
