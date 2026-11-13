# Agents Anywhere Docker 镜像（非官方）

从 [anywhere-labs/Agents-Anywhere](https://github.com/anywhere-labs/Agents-Anywhere) 正式版源码构建服务端镜像，包含官方 Web 前端。本仓库不修改应用代码；仅添加镜像元信息，并把上游 LICENSE / NOTICE 复制到镜像的 `/usr/share/licenses/agents-anywhere/`。

## 自动发布

- 每小时第 17 分钟检查上游最新正式 Release。GitHub 定时任务可能排队延迟，并非发布后立即触发。
- 仅构建正式版，不跟随开发主线或预发布版本。构建前解析为具体 Git commit。
- 支持 `linux/amd64` 和 `linux/arm64`，分别在原生架构 runner 构建。
- 每个架构先验证空数据库迁移、API 就绪检查和 Web 首页响应，成功后上传候选镜像。
- 两个架构全部通过才发布版本标签，并更新 `latest`。失败不会覆盖已有 `latest`。
- 已存在的版本标签不会自动重建覆盖。手动输入历史版本也不会让 `latest` 降级。
- 正式镜像不包含部署账号、密码、数据库或业务数据。CI 候选标签以 `ci-` 开头，部署请使用版本标签或 `latest`。
- GitHub 对长期无活动的公开仓库可能暂停定时任务；请留意 Actions 状态。标准公共 runner 当前不收费，以 GitHub 实际政策为准。

## 首次配置

1. 本仓库发布到 Docker Hub 公开仓库 `yxyu258/agents-anywhere`。如需自行维护，请创建自己的公开仓库。
2. 在 Docker Hub 创建有该仓库写权限的 Access Token。
3. 在本仓库 Settings → Secrets and variables → Actions 中设置：
   - Repository variable `DOCKERHUB_USERNAME`：Docker Hub 用户名（或组织 namespace）。
   - Repository secret `DOCKERHUB_TOKEN`：Docker Hub Access Token。
4. 在 Actions → Build and publish Agents Anywhere → Run workflow 手动运行一次。版本留空表示最新正式版。

不要把 Token 写入代码、日志或 Issue。该流程假设镜像仓库公开；检查版本时使用匿名拉取接口，遇到异常会失败，而非误判为新版本。

## NAS 使用

全新安装可下载本仓库的 `compose.yaml` 和 `.env.example`，把 `.env.example` 复制为 `.env`，为两个密钥分别运行 `openssl rand -hex 32` 并填写结果，将 `AGENT_SERVER_PUBLIC_ORIGIN` 改为实际访问地址，然后执行 `docker compose up -d`。首次初始化令牌可在主服务日志中查看。此配置使用独立数据卷，已有部署应继续使用原有数据目录、数据库密码和服务密钥。

在原有 Compose 的 `server-next` 和 `migrate-next` 两个服务中，移除 `build`，都改用相同镜像：

```yaml
image: yxyu258/agents-anywhere:2.1.0
```

替换上面的用户名和版本为实际发布值。数据库、Redis、环境变量、卷和网络保持原有设置。Agent 在接入的工作设备上运行；此镜像只托管服务端。

推荐固定版本升级。先备份 PostgreSQL、Redis、附件和现有密钥，再停止旧主服务，拉取新镜像、迁移、启动；不要让不同 schema 版本的服务同时写同一个数据库。详见[官方升级指南](https://github.com/anywhere-labs/Agents-Anywhere/blob/main/docs/upgrading.md)。

```bash
docker compose stop server-next
docker compose pull server-next migrate-next
docker compose up -d
```

NAS 拉取镜像无需构建。本仓库自动发布不等于 NAS 自动升级。

## 许可

Agents Anywhere 使用 Apache-2.0；上游历史 MIT 声明保留在 NOTICE 中。此处保留上游 LICENSE、NOTICE，并在每次构建时嵌入对应版本的声明。镜像是社区构建，与上游官方无隶属关系。第三方依赖保留其原有许可。
