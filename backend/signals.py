"""Turn a submission into DesignSignals. New formats plug in here."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Protocol

from backend.models import Submission


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


@dataclass
class DesignSignals:
    text: str
    class_names: list[str]
    base_classes: dict[str, list[str]]  # child -> bases
    methods: dict[str, list[str]]  # class -> methods
    uses_abc: bool
    uses_enum: bool
    uses_abstract_method: bool
    exception_classes: list[str]
    parsed_code: bool
    parse_error: str | None = None
    method_counts: dict[str, int] = field(default_factory=dict)

    def all_identifiers(self) -> set[str]:
        names = {_norm(c) for c in self.class_names}
        for methods in self.methods.values():
            names.update(_norm(m) for m in methods)
        return names

    def text_blob(self) -> str:
        return self.text.lower()

    def has_class(self, name: str) -> bool:
        target = _norm(name)
        return any(_norm(c) == target for c in self.class_names)

    def mentions(self, keywords: list[str]) -> bool:
        blob = self.text_blob()
        ident = self.all_identifiers()
        for kw in keywords:
            n = _norm(kw)
            if kw.lower() in blob or n in ident:
                return True
            if n and n in _norm(blob):
                return True
        return False


class SignalExtractor(Protocol):
    def extract(self, submission: Submission) -> DesignSignals: ...


class CombinedExtractor:
    """Notes + outline + Python AST. A diagram extractor would merge into the same signals."""

    def extract(self, submission: Submission) -> DesignSignals:
        text = "\n".join(
            [
                submission.design_notes or "",
                submission.class_outline or "",
                submission.code or "",
            ]
        )
        signals = DesignSignals(
            text=text,
            class_names=[],
            base_classes={},
            methods={},
            uses_abc=False,
            uses_enum=False,
            uses_abstract_method=False,
            exception_classes=[],
            parsed_code=False,
        )
        outline_classes = _classes_from_outline(submission.class_outline or "")
        signals.class_names.extend(outline_classes)

        code = (submission.code or "").strip()
        if not code:
            return signals
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            signals.parse_error = str(exc)
            return signals

        signals.parsed_code = True
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module in {"abc", "enum"}:
                    if node.module == "abc":
                        signals.uses_abc = True
                    if node.module == "enum":
                        signals.uses_enum = True
            if isinstance(node, ast.Name) and node.id in {"ABC", "abstractmethod", "Enum", "Protocol"}:
                if node.id in {"ABC", "abstractmethod", "Protocol"}:
                    signals.uses_abc = True
                if node.id == "Enum":
                    signals.uses_enum = True
            if isinstance(node, ast.ClassDef):
                if node.name not in signals.class_names:
                    signals.class_names.append(node.name)
                bases = [_base_name(b) for b in node.bases]
                signals.base_classes[node.name] = bases
                methods = [
                    n.name
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                signals.methods[node.name] = methods
                signals.method_counts[node.name] = len(methods)
                if any(b in {"Exception", "BaseException"} or b.endswith("Error") for b in bases):
                    signals.exception_classes.append(node.name)
                if "Enum" in bases:
                    signals.uses_enum = True
                if "ABC" in bases or "Protocol" in bases:
                    signals.uses_abc = True
                for n in node.body:
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for dec in n.decorator_list:
                            if _base_name(dec) == "abstractmethod":
                                signals.uses_abstract_method = True
                                signals.uses_abc = True
        return signals


def _base_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Call):
        return _base_name(node.func)
    return ""


def _classes_from_outline(outline: str) -> list[str]:
    found: list[str] = []
    for raw in outline.splitlines():
        line = raw.strip()
        if not line:
            continue
        # "class Foo" or "Foo" or "Foo:" or "Foo extends"
        m = re.match(r"(?:class\s+)?([A-Z][A-Za-z0-9_]+)", line)
        if m:
            found.append(m.group(1))
    return found
