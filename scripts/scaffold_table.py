#!/usr/bin/env python3
"""
新增业务表脚手架：根据表名生成 Model + Repository。

用法（在项目根目录）::

    python scripts/scaffold_table.py c_admin
    python scripts/scaffold_table.py c_admin --dry-run
    python scripts/scaffold_table.py c_admin --force
    python scripts/scaffold_table.py c_admin --no-introspect
    python scripts/scaffold_table.py c_admin --sql

流程建议
--------
1. 在 MySQL 中 CREATE TABLE c_admin (...)
2. 执行本脚本（默认从数据库反射字段生成 Model）
3. 检查 app/db/models/、app/db/repositories/ 生成结果
4. 按需手动在 app/db/deps.py 注册 XxxRepo
"""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PYTHON_TYPE_MAP = {
    "Integer": "int",
    "BigInteger": "int",
    "String": "str",
    "Text": "str",
    "DateTime": "datetime",
    "Date": "date",
    "Numeric": "Decimal",
    "Boolean": "bool",
    "Float": "float",
}

SENSITIVE_COLUMNS = {"password", "password_hash", "secret", "token", "access_token"}


@dataclass
class TableMeta:
    table_name: str
    stem: str
    module: str
    class_name: str
    repo_class: str


def derive_table_meta(table_name: str) -> TableMeta:
    """c_admin -> Admin / admin；c_messages -> Messages / messages。"""
    table_name = table_name.strip()
    stem = table_name[2:] if table_name.startswith(("c_", "o_")) else table_name
    class_name = "".join(part.capitalize() for part in stem.split("_"))
    module = stem.lower()

    if stem.endswith("s") and len(stem) > 1 and not stem.endswith("ss"):
        singular = stem[:-1]
    else:
        singular = stem
    singular_pascal = "".join(p.capitalize() for p in singular.split("_"))

    return TableMeta(
        table_name=table_name,
        stem=stem,
        module=module,
        class_name=class_name,
        repo_class=f"{singular_pascal}Repository",
    )


def introspect_columns(table_name: str) -> list[dict]:
    from sqlalchemy import create_engine, inspect

    from app.config import get_settings

    settings = get_settings()
    url = settings.database_url.replace("mysql+aiomysql", "mysql+pymysql")
    engine = create_engine(url, pool_pre_ping=True)

    try:
        inspector = inspect(engine)
        if table_name not in inspector.get_table_names():
            raise RuntimeError(f"表不存在: {table_name}，请先在 MySQL 中 CREATE TABLE")

        pk_cols = set(inspector.get_pk_constraint(table_name).get("constrained_columns") or [])
        result: list[dict] = []

        for col in inspector.get_columns(table_name):
            type_name, type_args = _map_column_type(col["type"])
            result.append(
                {
                    "name": col["name"],
                    "sa_type": type_name,
                    "sa_args": type_args,
                    "python_type": PYTHON_TYPE_MAP.get(type_name, "Any"),
                    "nullable": col.get("nullable", True),
                    "primary_key": col["name"] in pk_cols,
                }
            )
        return result
    finally:
        engine.dispose()


def _map_column_type(col_type: object) -> tuple[str, dict]:
    type_str = col_type.__class__.__name__.upper()
    if "INT" in type_str and "BIG" in type_str:
        return "BigInteger", {}
    if "INT" in type_str or "TINYINT" in type_str or "SMALLINT" in type_str:
        return "Integer", {}
    if "VARCHAR" in type_str or "CHAR" in type_str:
        return "String", {"length": getattr(col_type, "length", None) or 255}
    if "TEXT" in type_str or "BLOB" in type_str:
        return "Text", {}
    if "DATETIME" in type_str or "TIMESTAMP" in type_str:
        return "DateTime", {}
    if "DATE" in type_str and "TIME" not in type_str:
        return "Date", {}
    if "DECIMAL" in type_str or "NUMERIC" in type_str:
        return "Numeric", {}
    if "FLOAT" in type_str or "DOUBLE" in type_str:
        return "Float", {}
    if "BOOL" in type_str:
        return "Boolean", {}
    return "String", {"length": 255}


def default_columns() -> list[dict]:
    return [
        {
            "name": "id",
            "sa_type": "Integer",
            "sa_args": {},
            "python_type": "int",
            "nullable": False,
            "primary_key": True,
        },
        {
            "name": "name",
            "sa_type": "String",
            "sa_args": {"length": 64},
            "python_type": "str",
            "nullable": False,
            "primary_key": False,
        },
        {
            "name": "created_at",
            "sa_type": "DateTime",
            "sa_args": {},
            "python_type": "datetime",
            "nullable": False,
            "primary_key": False,
        },
    ]


def list_columns_for_repo(columns: list[dict]) -> list[str]:
    names = [c["name"] for c in columns]
    safe = [n for n in names if n not in SENSITIVE_COLUMNS]
    if "id" in safe:
        picked = ["id"]
        for name in safe:
            if name != "id" and len(picked) < 5:
                picked.append(name)
        return picked
    return safe[:5]


def _model_imports(columns: list[dict]) -> str:
    sa_types = {col["sa_type"] for col in columns}
    py_types = {
        col["python_type"]
        for col in columns
        if col["python_type"] in ("datetime", "date", "Decimal")
    }

    lines: list[str] = []
    if "datetime" in py_types:
        lines.append("from datetime import datetime")
    if "date" in py_types:
        lines.append("from datetime import date")
    if "Decimal" in py_types:
        lines.append("from decimal import Decimal")

    lines.extend(
        [
            f"from sqlalchemy import {', '.join(sorted(sa_types))}",
            "from sqlalchemy.orm import Mapped, mapped_column",
            "",
            "from app.db.base import Base",
        ]
    )
    return "\n".join(lines)


def _render_column(col: dict) -> str:
    sa = col["sa_type"]
    args = col["sa_args"]
    py = col["python_type"]
    optional = " | None" if col["nullable"] and not col["primary_key"] else ""
    default = " = None" if optional else ""

    col_args: list[str] = []
    if sa == "String":
        col_args.append(f"String({args.get('length', 255)})")
    elif sa == "Numeric":
        col_args.append("Numeric(10, 2)")
    else:
        col_args.append(sa)

    if col["primary_key"]:
        col_args.append("primary_key=True")
        if sa == "Integer":
            col_args.append("autoincrement=True")

    return (
        f"    {col['name']}: Mapped[{py}{optional}]"
        f" = mapped_column({', '.join(col_args)}){default}"
    )


def render_model(meta: TableMeta, columns: list[dict]) -> str:
    body = "\n".join(_render_column(col) for col in columns)
    return (
        f"{_model_imports(columns)}\n\n\n"
        f"class {meta.class_name}(Base):\n"
        f'    """{meta.table_name} 表。"""\n\n'
        f'    __tablename__ = "{meta.table_name}"\n\n'
        f"{body}\n"
    )


def render_repository(meta: TableMeta, list_cols: list[str]) -> str:
    cols_repr = ", ".join(f'"{col}"' for col in list_cols)
    return textwrap.dedent(
        f"""\
        from app.db.models.{meta.module} import {meta.class_name}
        from app.db.repositories.base import BaseRepository


        class {meta.repo_class}(BaseRepository):
            \"\"\"{meta.table_name} 数据访问。\"\"\"

            model = {meta.class_name}

            # 列表查询默认返回字段，可按需修改
            ALL_LIST_COLUMNS = [{cols_repr}]
        """
    )


def render_create_sql(meta: TableMeta) -> str:
    return textwrap.dedent(
        f"""\
        -- 示例建表 SQL（请按实际业务修改字段）
        CREATE TABLE IF NOT EXISTS `{meta.table_name}` (
          `id` INT NOT NULL AUTO_INCREMENT,
          `name` VARCHAR(64) NOT NULL COMMENT '名称',
          `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{meta.class_name}';
        """
    )


def write_file(path: Path, content: str, *, force: bool, dry_run: bool) -> str:
    rel = path.relative_to(ROOT)
    if path.exists() and not force:
        return f"SKIP  {rel} (已存在，加 --force 覆盖)"
    if dry_run:
        return f"DRY   {rel}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"WRITE {rel}"


def register_model(meta: TableMeta, *, dry_run: bool) -> str:
    path = ROOT / "app/db/models/__init__.py"
    text = path.read_text(encoding="utf-8")
    import_line = f"from app.db.models.{meta.module} import {meta.class_name}"

    if import_line in text:
        return f"SKIP  {path.relative_to(ROOT)}"

    if dry_run:
        return f"PATCH {path.relative_to(ROOT)} (+ {meta.class_name})"

    if "__all__" in text:
        text = re.sub(
            r"__all__ = \[(.*?)\]",
            lambda m: (
                f'__all__ = [{m.group(1)}, "{meta.class_name}"]'
                if meta.class_name not in m.group(1)
                else m.group(0)
            ),
            text,
            count=1,
        )
    else:
        text += f'\n__all__ = ["{meta.class_name}"]\n'

    if import_line not in text:
        lines = text.splitlines()
        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith("from app.db.models."):
                insert_at = i + 1
        lines.insert(insert_at, import_line)
        text = "\n".join(lines) + "\n"

    path.write_text(text, encoding="utf-8")
    return f"PATCH {path.relative_to(ROOT)} (+ {meta.class_name})"


def register_repository(meta: TableMeta, *, dry_run: bool) -> str:
    path = ROOT / "app/db/repositories/__init__.py"
    text = path.read_text(encoding="utf-8")
    import_line = f"from app.db.repositories.{meta.module} import {meta.repo_class}"

    if import_line in text:
        return f"SKIP  {path.relative_to(ROOT)}"

    if dry_run:
        return f"PATCH {path.relative_to(ROOT)} (+ {meta.repo_class})"

    lines = text.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("from app.db.repositories."):
            insert_at = i + 1
    lines.insert(insert_at, import_line)
    text = "\n".join(lines)

    if f'"{meta.repo_class}"' not in text:
        text = re.sub(
            r"(__all__ = \[.*?)(\])",
            lambda m: f'{m.group(1)}\n    "{meta.repo_class}",{m.group(2)}',
            text,
            count=1,
            flags=re.DOTALL,
        )

    path.write_text(text + "\n", encoding="utf-8")
    return f"PATCH {path.relative_to(ROOT)} (+ {meta.repo_class})"


def main() -> None:
    parser = argparse.ArgumentParser(description="新增业务表：生成 Model + Repository")
    parser.add_argument("table", nargs="?", help="表名，如 c_admin")
    parser.add_argument("--table", dest="table_opt", help="表名（与位置参数二选一）")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写文件")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的生成文件")
    parser.add_argument(
        "--no-introspect",
        action="store_true",
        help="不连接数据库，使用占位字段（id/name/created_at）",
    )
    parser.add_argument("--sql", action="store_true", help="仅输出建表 SQL 示例")
    args = parser.parse_args()

    table_name = args.table_opt or args.table
    if not table_name:
        parser.error("请指定表名，例如: python scripts/scaffold_table.py c_admin")

    meta = derive_table_meta(table_name)

    if args.sql:
        print(render_create_sql(meta))
        return

    if args.no_introspect:
        columns = default_columns()
        print(f"[提示] 未连接数据库，使用占位字段，请手动修改 app/db/models/{meta.module}.py")
    else:
        try:
            columns = introspect_columns(table_name)
            print(f"[OK] 已从数据库反射 {table_name}，共 {len(columns)} 个字段")
        except Exception as exc:
            print(f"[警告] 数据库反射失败: {exc}")
            columns = default_columns()
            print(f"[提示] 已回退占位字段，可用 --sql 查看建表示例")

    list_cols = list_columns_for_repo(columns)
    model_path = ROOT / f"app/db/models/{meta.module}.py"
    repo_path = ROOT / f"app/db/repositories/{meta.module}.py"

    print(f"\n表名: {meta.table_name}")
    print(f"Model: {meta.class_name}  Repository: {meta.repo_class}\n")

    print(write_file(model_path, render_model(meta, columns), force=args.force, dry_run=args.dry_run))
    print(
        write_file(
            repo_path,
            render_repository(meta, list_cols),
            force=args.force,
            dry_run=args.dry_run,
        )
    )
    print(register_model(meta, dry_run=args.dry_run))
    print(register_repository(meta, dry_run=args.dry_run))

    singular_pascal = meta.repo_class.removesuffix("Repository")
    repo_dep = f"{singular_pascal}Repo"
    print(
        textwrap.dedent(
            f"""
            完成。下一步（需手动）：
            1. 检查 app/db/models/{meta.module}.py
            2. 调整 {meta.repo_class}.ALL_LIST_COLUMNS
            3. 在 app/db/deps.py 注册依赖，例如：
               get_{meta.module}_repository = repository_factory({meta.repo_class})
               {repo_dep} = Annotated[{meta.repo_class}, Depends(get_{meta.module}_repository)]
            """
        ).strip()
    )


if __name__ == "__main__":
    main()
