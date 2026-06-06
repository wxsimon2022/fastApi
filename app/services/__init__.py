"""
Service 层：业务逻辑。

MVC 分层说明
------------
- controllers/   控制器 (C)：HTTP 入参 / ApiResponse 出参，不写业务逻辑
- services/      业务逻辑 (本目录)
- db/models/     数据模型 (M)
- db/repositories/  数据访问
- schemas/       视图对象 (V)：Request / Response DTO
"""
