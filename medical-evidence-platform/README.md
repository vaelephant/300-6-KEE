# 医疗多模态证据平台 · 后端数据层 V0.1

本次在数据契约 V1.0 上实现 SQLAlchemy 模型、Alembic 初始迁移，以及资产、来源锚点和事实的事务内写入仓储。还不是完整平台，也尚无 HTTP API、前端或大模型接入。

## 目录

- contracts/：继承的六份契约、示例及规则说明。
- back/app/models.py：患者、就诊、资产、资产版本、锚点、事实、事实版本、事实证据关联、查询定义、查询运行和证据包，共12张表及对应ORM模型。
- back/app/repository.py：契约验证、租户上下文检查、患者/就诊归属检查、锚点范围检查、前序版本检查；提供 add_asset/add_anchor/add_fact。
- back/migrations/：冻结的初始元数据、升级和降级迁移。
- back/tests/：正常写入、版本更正、跨租户/患者、重复写入和无效引用测试。

## 本地验证

```bash
cd back
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m alembic upgrade head
python3 -m pytest -q
```

不设置 DATABASE_URL 时使用本地 SQLite development.db，仅供开发验证。测试使用独立内存库并打开外键。

PostgreSQL部署使用环境变量（凭证由本地密钥配置，勿写入版本库）：

```bash
export DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/medical_evidence'
python3 -m alembic upgrade head
```

降级会删除本次创建的表与数据，仅用于空的开发环境。不要在生产运行 downgrade base。

## 事务使用

```python
from sqlalchemy import create_engine
from app.repository import Repository
engine = create_engine(database_url)
with engine.begin() as connection:
    repo = Repository(connection, authenticated_tenant_id)
    repo.add_asset(asset_payload)
    repo.add_anchor(anchor_payload)
    repo.add_fact(fact_payload)
```

患者及就诊应由已核验的主索引服务先写入，仓储不会根据未知患者ID自动创建身份。异常必须传播到事务边界以回滚，不要捕获后继续提交半套资料。租户参数必须来自认证上下文，本版仓储自身不执行登录或用户级授权。

## 已实现的约束

- 主键和引用带 tenant_id；资产—锚点—事实引用额外绑定 patient_id，数据库复合外键阻止跨患者关联。
- 资产和事实的患者/就诊归属由写入仓储固定；版本序号唯一。
- 第2版起必须引用同一实体的上一版；重复版本数据库拒绝，重试返回策略留待接入层实现。
- 发布事实必须具有锚点；仓储核验锚点和输入事实存在。修订新增行，旧payload不覆盖。
- 查询定义、查询运行、证据包已建立持久化表；相应发布、执行和封装服务尚未实现。

## 实现边界与下一步

这是初版持久化基础。严格不可变由仓储的新增接口约束，数据库尚未配置更新禁止触发器或专用只读角色；具有直接写库权限者仍可能修改payload。生产前必须补充最小权限角色和不可变约束。

JSON payload 的完整约束依赖仓储验证；任意直接SQL可绕过Schema。尚待实现RLS、用户与用途授权、审计、Outbox、输入事实关联表、加工运行实体、源资产哈希验证、媒体实际页数/帧数核验、查询快照一致性和当前版本选择。当前JSON列为跨数据库的JSON类型，PostgreSQL的JSONB/索引及类型化检验明细留待下一轮；不要将此版本直接用于患者生产数据。

迁移支持PostgreSQL方言，但本轮无PostgreSQL实例；仅本地SQLite迁移与测试实跑，生成PostgreSQL DDL用于检查并不等同于实机验证。测试不会证明完整权限安全，只覆盖所列数据关联场景。

下一步：PostgreSQL集成环境及权限加固 → 首个检验接入服务 → 注册查询与证据API → 前端证据核对页面。
