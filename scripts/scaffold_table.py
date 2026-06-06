#!/usr/bin/env python3
"""
新增业务表脚手架：根据表名生成 MVC 各层默认文件，并自动注册路由 / 依赖注入。

用法（在项目根目录）::

    python scripts/scaffold_table.py c_admin
    python scripts/scaffold_table.py --table c_admin --dry-run
    python scripts/scaffold_table.py c_admin --force
    python scripts/scaffold_table.py c_admin --no-introspect
    python scripts/scaffold_table.py c_admin --sql

流程建议
--------
1. 在 MySQL 中 CREATE TABLE c_admin (...)
2. 执行本脚本（默认从数据库反射字段生成 Model）
3. 检查生成文件，按需修改 ALL_LIST_COLUMNS、Schema 字段等
4. 重启服务，访问 /docs 验证
"""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# --------------------------------------------------------------------------- #
# 命名推导
# --------------------------------------------------------------------------- #


@dataclass
class TableMeta:
    table_name: str
    stem: str
    module: str
    class_name: str
    singular: str
    route_segment: str
    repo_class: str
    service_class: str
    id_param: str
    repo_dep: str
    service_dep: str
    columns: list[dict] = field(default_factory=list)


def derive_table_meta(table_name: str) -> TableMeta:
    """c_admin -> Admin / admin / admins；c_users -> Users / user / users。"""
    table_name = table_name.strip()
    stem = table_name[2:] if table_name.startswith(("c_", "o_")) else table_name

    class_name = "".join(part.capitalize() for part in stem.split("_"))
    module = stem.lower()

    if stem.endswith("s") and len(stem) > 1:
        singular = stem[:-1] if stem.endswith("s") and not stem.endswith("ss") else stem
        route_segment = stem
    else:
        singular = stem
        route_segment = f"{stem}s"

    singular_parts = singular.split("_")
    singular_pascal = "".join(p.capitalize() for p in singular_parts)

    return TableMeta(
        table_name=table_name,
        stem=stem,
        module=module,
        class_name=class_name,
        singular=singular,
        route_segment=route_segment,
        repo_class=f"{singular_pascal}Repository",
        service_class=f"{singular_pascal}Service",
        id_param=f"{singular}_id",
        repo_dep=f"{singular_pascal}Repo",
        service_dep=f"{singular_pascal}ServiceDep",
    )


# --------------------------------------------------------------------------- #
# 数据库反射
# --------------------------------------------------------------------------- #

SA_TYPE_IMPORTS: dict[str, str] = {
    "Integer": "Integer",
    "String": "String",
    "Text": "Text",
    "DateTime": "DateTime",
    "Date": "Date",
    "Numeric": "Numeric",
    "Boolean": "Boolean",
    "Float": "Float",
    "BigInteger": "BigInteger",
}

PYTHON_TYPE_IMPORTS: dict[str, str] = {
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


def introspect_columns(table_name: str) -> list[dict]:
    """从 MySQL 反射表结构。"""
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
            name = col["name"]
            col_type = col["type"]
            type_name, type_args = _map_column_type(col_type)

            result.append(
                {
                    "name": name,
                    "sa_type": type_name,
                    "sa_args": type_args,
                    "python_type": PYTHON_TYPE_IMPORTS.get(type_name, "Any"),
                    "nullable": col.get("nullable", True),
                    "primary_key": name in pk_cols,
                    "default": col.get("default"),
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
        length = getattr(col_type, "length", None) or 255
        return "String", {"length": length}
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


def default_columns(meta: TableMeta) -> list[dict]:
    """无数据库反射时的占位字段。"""
    return [
        {
            "name": "id",
            "sa_type": "Integer",
            "sa_args": {},
            "python_type": "int",
            "nullable": False,
            "primary_key": True,
            "default": None,
        },
        {
            "name": "name",
            "sa_type": "String",
            "sa_args": {"length": 64},
            "python_type": "str",
            "nullable": False,
            "primary_key": False,
            "default": None,
        },
        {
            "name": "created_at",
            "sa_type": "DateTime",
            "sa_args": {},
            "python_type": "datetime",
            "nullable": False,
            "primary_key": False,
            "default": None,
        },
    ]


def list_columns_for_repo(columns: list[dict]) -> list[str]:
    names = [c["name"] for c in columns]
    safe = [n for n in names if n not in SENSITIVE_COLUMNS]
    if "id" in safe:
        picked = ["id"]
        for n in safe:
            if n != "id" and len(picked) < 5:
                picked.append(n)
        return picked
    return safe[:5]


# --------------------------------------------------------------------------- #
# 代码生成
# --------------------------------------------------------------------------- #


def _model_imports(columns: list[dict]) -> str:
    sa_types = {"Integer"}
    py_types: set[str] = set()
    for col in columns:
        sa_types.add(col["sa_type"])
        if col["python_type"] in ("datetime", "date", "Decimal"):
            py_types.add(col["python_type"])

    py_imports: list[str] = []
    if "datetime" in py_types:
        py_imports.append("from datetime import datetime")
    if "date" in py_types:
        py_imports.append("from datetime import date")
    if "Decimal" in py_types:
        py_imports.append("from decimal import Decimal")

    sa_import = ", ".join(sorted(sa_types))
    lines = py_imports + [
        f"from sqlalchemy import {sa_import}",
        "from sqlalchemy.orm import Mapped, mapped_column",
        "",
        "from app.db.base import Base",
    ]
    return "\n".join(lines)


def _render_column(col: dict) -> str:
    sa = col["sa_type"]
    args = col["sa_args"]
    py = col["python_type"]
    optional = " | None" if col["nullable"] and not col["primary_key"] else ""
    default = " = None" if optional else ""

    col_args: list[str] = []
    if sa == "String":
        length = args.get("length", 255)
        col_args.append(f"String({length})")
    elif sa == "Numeric":
        col_args.append("Numeric(10, 2)")
    else:
        col_args.append(sa)

    if col["primary_key"]:
        col_args.append("primary_key=True")
        if sa == "Integer":
            col_args.append("autoincrement=True")

    arg_str = ", ".join(col_args)
    return f"    {col['name']}: Mapped[{py}{optional}] = mapped_column({arg_str}){default}"


def _render_model(meta: TableMeta, columns: list[dict]) -> str:
    body = "\n".join(_render_column(col) for col in columns)
    return (
        _model_imports(columns)
        + "\n\n\n"
        + f'class {meta.class_name}(Base):\n'
        + f'    """{meta.table_name} 表。"""\n\n'
        + f'    __tablename__ = "{meta.table_name}"\n\n'
        + body
        + "\n"
    )


def render_repository(meta: TableMeta, list_cols: list[str]) -> str:
    cols_repr = ", ".join(f'"{c}"' for c in list_cols)
    return textwrap.dedent(
        f'''\
        from app.db.models.{meta.module} import {meta.class_name}
        from app.db.repositories.base import BaseRepository


        class {meta.repo_class}(BaseRepository):
            """{meta.table_name} 数据访问。"""

            model = {meta.class_name}

            # 列表 /all 接口默认返回字段，可按需修改
            ALL_LIST_COLUMNS = [{cols_repr}]
        '''
    )


def render_schema(meta: TableMeta, columns: list[dict]) -> str:
    py_types: set[str] = set()
    for col in columns:
        if col["primary_key"]:
            continue
        if col["python_type"] in ("datetime", "date", "Decimal"):
            py_types.add(col["python_type"])

    import_lines = ["from pydantic import BaseModel, Field"]
    if "datetime" in py_types:
        import_lines.insert(0, "from datetime import datetime")
    if "date" in py_types:
        import_lines.insert(0, "from datetime import date")
    if "Decimal" in py_types:
        import_lines.insert(0, "from decimal import Decimal")

    lines = import_lines + [
        "",
        "",
        f"class {meta.class_name}Update(BaseModel):",
        f'    """更新 {meta.table_name} 表，仅传需要修改的字段。"""',
        "",
    ]
    for col in columns:
        if col["primary_key"]:
            continue
        name = col["name"]
        py = col["python_type"]
        optional = " | None" if col["nullable"] else " | None"
        extra = ""
        if py == "str":
            extra = ", min_length=1"
        elif py == "int":
            extra = ""
        lines.append(
            f"    {name}: {py}{optional} = Field(None{extra})"
        )
    if len(lines) == 5:
        lines.append("    pass")
    lines.append("")
    return "\n".join(lines)


def render_service(meta: TableMeta) -> str:
    return textwrap.dedent(
        f'''\
        """{meta.table_name} 业务逻辑。"""

        from __future__ import annotations

        from typing import Any

        from app.core.exceptions import AppException
        from app.db.field_query import FieldQuery, FieldQueryMode
        from app.db.repositories.{meta.module} import {meta.repo_class}
        from app.schemas.pagination import PageResult


        class {meta.service_class}:
            """{meta.class_name} 模块业务逻辑。"""

            def __init__(self, *, repo: {meta.repo_class}) -> None:
                self._repo = repo

            async def list_paginated(
                self,
                *,
                page: int,
                page_size: int,
                columns: list[str] | None = None,
            ) -> PageResult[dict[str, Any]]:
                return await self._repo.get_list(
                    page=page,
                    page_size=page_size,
                    columns=columns,
                )

            async def list_all(self) -> list[dict[str, Any]]:
                return await self._repo.get_all(columns={meta.repo_class}.ALL_LIST_COLUMNS)

            async def lookup(self, query: FieldQuery) -> Any:
                result = await self._repo.query_field(query)
                if query.mode == FieldQueryMode.ONE:
                    if result is None:
                        raise AppException("记录不存在", code=404)
                    return result
                if query.mode == FieldQueryMode.ID:
                    if result is None:
                        raise AppException("记录不存在", code=404)
                    return {{"id": result}}
                if query.mode in (FieldQueryMode.LIST, FieldQueryMode.ALL):
                    return result
                raise AppException(f"不支持的查询类型: {{query.mode}}", code=400)

            async def get_by_id(
                self,
                record_id: int,
                *,
                columns: list[str] | None = None,
            ) -> dict[str, Any]:
                item = await self._repo.get_one_by_id(record_id, columns=columns)
                if item is None:
                    raise AppException("记录不存在", code=404)
                return item

            async def update(self, record_id: int, data: dict[str, Any]) -> dict[str, Any]:
                item = await self._repo.update_by_id(record_id, data)
                if item is None:
                    raise AppException("记录不存在", code=404)
                return item
        '''
    )


def render_controller(meta: TableMeta) -> str:
    schema_update = f"{meta.class_name}Update"
    return textwrap.dedent(
        f'''\
        """Controller：{meta.table_name} 接口入参 / 出参。"""

        from typing import Any

        from fastapi import APIRouter

        from app.schemas.common import ApiResponse, success
        from app.schemas.{meta.module} import {schema_update}
        from app.schemas.pagination import PageResult
        from app.schemas.query import ColumnsQuery, FieldParams, PageParams, build_field_query
        from app.services.deps import {meta.service_dep}

        router = APIRouter(prefix="/{meta.route_segment}", tags=["{meta.route_segment}"])


        @router.get("", response_model=ApiResponse[PageResult[dict]])
        async def list_{meta.route_segment}(
            pagination: PageParams,
            columns: ColumnsQuery,
            service: {meta.service_dep},
        ) -> ApiResponse[PageResult[dict]]:
            result = await service.list_paginated(
                page=pagination.page,
                page_size=pagination.page_size,
                columns=columns.columns,
            )
            return success(data=result)


        @router.get("/all", response_model=ApiResponse[list])
        async def list_all_{meta.route_segment}(service: {meta.service_dep}) -> ApiResponse[list]:
            items = await service.list_all()
            return success(data=items)


        @router.get("/lookup", response_model=ApiResponse[Any])
        async def lookup_{meta.singular}(
            lookup: FieldParams,
            pagination: PageParams,
            service: {meta.service_dep},
        ) -> ApiResponse[Any]:
            query = build_field_query(lookup, pagination)
            data = await service.lookup(query)
            return success(data=data)


        @router.get("/{{{meta.id_param}}}", response_model=ApiResponse[dict])
        async def get_{meta.singular}(
            {meta.id_param}: int,
            columns: ColumnsQuery,
            service: {meta.service_dep},
        ) -> ApiResponse[dict]:
            item = await service.get_by_id({meta.id_param}, columns=columns.columns)
            return success(data=item)


        @router.put("/{{{meta.id_param}}}", response_model=ApiResponse[dict])
        async def update_{meta.singular}(
            {meta.id_param}: int,
            body: {schema_update},
            service: {meta.service_dep},
        ) -> ApiResponse[dict]:
            data = body.model_dump(exclude_unset=True)
            item = await service.update({meta.id_param}, data)
            return success(data=item, message="更新成功")
        '''
    )


def render_create_sql(meta: TableMeta) -> str:
    return textwrap.dedent(
        f'''\
        -- 示例建表 SQL（请按实际业务修改字段）
        CREATE TABLE IF NOT EXISTS `{meta.table_name}` (
          `id` INT NOT NULL AUTO_INCREMENT,
          `name` VARCHAR(64) NOT NULL COMMENT '名称',
          `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (`id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{meta.class_name}';
        '''
    )


# --------------------------------------------------------------------------- #
# 文件写入与注册
# --------------------------------------------------------------------------- #


@dataclass
class GeneratedFile:
    path: Path
    content: str


def collect_files(meta: TableMeta, columns: list[dict]) -> list[GeneratedFile]:
    list_cols = list_columns_for_repo(columns)
    return [
        GeneratedFile(ROOT / f"app/db/models/{meta.module}.py", _render_model(meta, columns)),
        GeneratedFile(ROOT / f"app/db/repositories/{meta.module}.py", render_repository(meta, list_cols)),
        GeneratedFile(ROOT / f"app/schemas/{meta.module}.py", render_schema(meta, columns)),
        GeneratedFile(ROOT / f"app/services/{meta.module}_service.py", render_service(meta)),
        GeneratedFile(ROOT / f"app/controllers/v1/{meta.module}.py", render_controller(meta)),
        GeneratedFile(ROOT / f"scripts/sql/{meta.table_name}.sql", render_create_sql(meta)),
    ]


def write_file(path: Path, content: str, *, force: bool, dry_run: bool) -> str:
    if path.exists() and not force:
        return f"SKIP  {path.relative_to(ROOT)} (已存在，加 --force 覆盖)"
    if dry_run:
        return f"DRY   {path.relative_to(ROOT)}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"WRITE {path.relative_to(ROOT)}"


def register_project(meta: TableMeta, *, dry_run: bool) -> list[str]:
    logs: list[str] = []

    models_init = ROOT / "app/db/models/__init__.py"
    text = models_init.read_text(encoding="utf-8")
    import_line = f"from app.db.models.{meta.module} import {meta.class_name}"
    if import_line not in text:
        if dry_run:
            logs.append(f"PATCH app/db/models/__init__.py (+ {meta.class_name})")
        else:
            if "from app.db.models.users import Users" in text:
                text = text.replace(
                    "from app.db.models.users import Users\n",
                    f"from app.db.models.users import Users\n{import_line}\n",
                )
            else:
                text = import_line + "\n" + text
            if "__all__" in text:
                text = re.sub(
                    r"__all__ = \[(.*?)\]",
                    lambda m: f'__all__ = [{m.group(1)}, "{meta.class_name}"]'
                    if meta.class_name not in m.group(1)
                    else m.group(0),
                    text,
                    count=1,
                )
            else:
                text += f'\n__all__ = ["{meta.class_name}"]\n'
            models_init.write_text(text, encoding="utf-8")
            logs.append(f"PATCH app/db/models/__init__.py (+ {meta.class_name})")
    else:
        logs.append("SKIP  app/db/models/__init__.py")

    deps_path = ROOT / "app/db/deps.py"
    deps_text = deps_path.read_text(encoding="utf-8")
    repo_import = f"from app.db.repositories.{meta.module} import {meta.repo_class}"
    if repo_import not in deps_text:
        block = textwrap.dedent(
            f'''\
            {repo_import}
            get_{meta.module}_repository = repository_factory({meta.repo_class})
            {meta.repo_dep} = Annotated[{meta.repo_class}, Depends(get_{meta.module}_repository)]
            '''
        )
        if not dry_run:
            deps_path.write_text(deps_text.rstrip() + "\n\n" + block, encoding="utf-8")
        logs.append(f"PATCH app/db/deps.py (+ {meta.repo_dep})")
    else:
        logs.append("SKIP  app/db/deps.py")

    svc_deps = ROOT / "app/services/deps.py"
    svc_text = svc_deps.read_text(encoding="utf-8")
    svc_import = f"from app.services.{meta.module}_service import {meta.service_class}"
    if svc_import not in svc_text:
        if f"{meta.repo_dep}" not in svc_text:
            svc_text = svc_text.replace(
                "from app.db.deps import UserRepo\n",
                f"from app.db.deps import UserRepo, {meta.repo_dep}\n",
            )
        block = textwrap.dedent(
            f'''\
            {svc_import}


            def get_{meta.module}_service(repo: {meta.repo_dep}) -> {meta.service_class}:
                return {meta.service_class}(repo=repo)


            {meta.service_dep} = Annotated[{meta.service_class}, Depends(get_{meta.module}_service)]
            '''
        )
        if not dry_run:
            svc_deps.write_text(svc_text.rstrip() + "\n\n" + block, encoding="utf-8")
        logs.append(f"PATCH app/services/deps.py (+ {meta.service_dep})")
    else:
        logs.append("SKIP  app/services/deps.py")

    router_path = ROOT / "app/controllers/v1/router.py"
    router_text = router_path.read_text(encoding="utf-8")
    import_part = f", {meta.module}"
    include_part = f"api_router.include_router({meta.module}.router)"
    if meta.module not in router_text:
        if not dry_run:
            router_text = router_text.replace(
                "from app.controllers.v1 import auth, demo, health, redis_demo, users",
                f"from app.controllers.v1 import auth, demo, health, redis_demo, users, {meta.module}",
            )
            router_text = router_text.replace(
                "api_router.include_router(users.router)",
                f"api_router.include_router(users.router)\n{include_part}",
            )
            router_path.write_text(router_text, encoding="utf-8")
        logs.append(f"PATCH app/controllers/v1/router.py (+ /{meta.route_segment})")
    else:
        logs.append("SKIP  app/controllers/v1/router.py")

    tables_path = ROOT / "app/db/tables.py"
    const_name = meta.table_name.upper()
    marker = f'{const_name} = "{meta.table_name}"'
    tables_text = tables_path.read_text(encoding="utf-8")
    if marker not in tables_text:
        if not dry_run:
            tables_path.write_text(tables_text.rstrip() + f"\n{marker}\n", encoding="utf-8")
        logs.append(f"PATCH app/db/tables.py (+ {const_name})")
    else:
        logs.append("SKIP  app/db/tables.py")

    repo_init = ROOT / "app/db/repositories/__init__.py"
    repo_init_text = repo_init.read_text(encoding="utf-8")
    ri = f"from app.db.repositories.{meta.module} import {meta.repo_class}"
    if ri not in repo_init_text:
        if not dry_run:
            repo_init.write_text(
                repo_init_text.replace(
                    "from app.db.repositories.user import UserRepository",
                    f"from app.db.repositories.user import UserRepository\n{ri}",
                ).replace(
                    '"UserRepository",',
                    f'"UserRepository",\n    "{meta.repo_class}",',
                ),
                encoding="utf-8",
            )
        logs.append(f"PATCH app/db/repositories/__init__.py (+ {meta.repo_class})")

    return logs


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main() -> None:
    parser = argparse.ArgumentParser(description="新增业务表 MVC 脚手架")
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
        columns = default_columns(meta)
        print(f"[提示] 未连接数据库，使用占位字段，请手动修改 app/db/models/{meta.module}.py")
    else:
        try:
            columns = introspect_columns(table_name)
            print(f"[OK] 已从数据库反射 {table_name}，共 {len(columns)} 个字段")
        except Exception as exc:
            print(f"[警告] 数据库反射失败: {exc}")
            columns = default_columns(meta)
            print(f"[提示] 已回退占位字段，可先执行 scripts/sql/{table_name}.sql 建表后重新运行")

    files = collect_files(meta, columns)

    print(f"\n表名: {meta.table_name}")
    print(f"Model: {meta.class_name}  路由: /api/v1/{meta.route_segment}\n")

    for gf in files:
        if gf.path.suffix == ".sql" and not args.no_introspect and columns != default_columns(meta):
            # 表已存在时可跳过 SQL 文件
            if gf.path.exists() and not args.force:
                print(f"SKIP  {gf.path.relative_to(ROOT)}")
                continue
        print(write_file(gf.path, gf.content, force=args.force, dry_run=args.dry_run))

    print()
    for line in register_project(meta, dry_run=args.dry_run):
        print(line)

    print(
        textwrap.dedent(
            f"""
            完成。下一步：
            1. 检查 app/db/models/{meta.module}.py 字段是否正确
            2. 调整 {meta.repo_class}.ALL_LIST_COLUMNS
            3. 重启服务，访问 /docs 查看 /{meta.route_segment} 接口
            """
        ).strip()
    )


if __name__ == "__main__":
    main()
