# 把项目推到 GitHub：一步一步

> 目标：把本地 `lowalt-route-risk` 仓库推上 GitHub，得到一个能放进简历/申请材料的公开链接。
> 仓库已检查：63 个文件、约 1.7 MB（`.venv/` 与 `data/` 已忽略），不需要 Git LFS。
> 当前分支 `master`，已打 `v0.1` 标签。

## 0. 先确认两件事

- 有 GitHub 账号（没有就花 2 分钟注册：https://github.com/signup）。
- 网络能打开 github.com。国内网络可能连不上，见第 6 节「连不上怎么办」。

## 1. 在 GitHub 网页建一个空仓库

1. 登录后点右上角 **+** → **New repository**。
2. Repository name 填：`lowalt-route-risk`。
3. 选 **Public**（作品集要能给别人看；不想公开可以先 Private，之后再改）。
4. **不要**勾选 "Add a README file"、".gitignore"、"license"——本地已经有了，勾了会冲突。
5. 点 **Create repository**。

建好后页面会显示仓库地址，形如：

```
https://github.com/<你的用户名>/lowalt-route-risk.git
```

## 2. 在 PowerShell 里连上远程仓库

```powershell
cd "C:\Users\弋昊阳\OneDrive\文档\deepseek-harness\default-workspace\lowalt-route-risk"

# 把 <你的用户名> 换成自己的 GitHub 用户名
git remote add origin https://github.com/<你的用户名>/lowalt-route-risk.git

# 分支改名为 main（GitHub 默认叫 main）
git branch -M main

# 首次推送，并把 main 设为上游
git push -u origin main

# 把 v0.1 标签也推上去
git push origin v0.1
```

## 3. 第一次 push 会要密码——用 Token，不是登录密码

GitHub 从 2021 年起不接受账号密码，要 Personal Access Token（PAT）：

1. GitHub 右上角头像 → **Settings**。
2. 左侧最下 **Developer settings** → **Personal access tokens** → **Tokens (classic)**。
3. **Generate new token (classic)**：
   - Note 填 `lowalt-route-risk-push`
   - Expiration 选 90 days
   - 勾选 **repo**（整块）
4. 点 **Generate token**，复制 `ghp_...`（只显示一次）。
5. 回到 PowerShell 的 `git push`，提示 `Username` 填 GitHub 用户名，
   `Password` 粘贴刚才的 token（输入时不显示字符，正常）。

Windows 会把它存进「凭据管理器」，以后不用再输。

## 4. 验证

打开 `https://github.com/<你的用户名>/lowalt-route-risk`，应该看到：

- README 渲染出标题、结果表；
- `figures/` 里有 6 张图；
- 右上角 **Tags** 里有 `v0.1`；
- 提交记录从 `2b266ed` 到 `74911c2`。

## 5. 以后每天怎么推

```powershell
git add -A
git commit -m "feat: day8 ..."
git push
```

## 6. 连不上怎么办（国内网络常见）

按顺序试：

1. **开代理**（Clash/V2Ray 等），让 git 走代理：
   ```powershell
   git config --global http.proxy http://127.0.0.1:7890
   git config --global https.proxy http://127.0.0.1:7890
   ```
   端口按你代理软件的实际端口改（Clash 常见 7890，V2Ray 常见 10809）。
   用完想取消：`git config --global --unset http.proxy`（https 同理）。
2. **SSH 走 443**：GitHub 的 `ssh.github.com:443` 通常能通，配置见 GitHub 文档
   "Using SSH over the HTTPS port"。
3. **换 Gitee（码云）**：注册后建仓库，流程同上，只是地址变成
   `https://gitee.com/<用户名>/lowalt-route-risk.git`。作品集里放 Gitee 链接也可以，
   但 GitHub 在国际申请里更常见。

## 7. 常见报错

| 报错 | 原因 | 解决 |
|---|---|---|
| `remote origin already exists` | 之前加过 origin | `git remote set-url origin <新地址>` |
| `failed to push some refs` / `rejected` | 网页建仓库时勾了 README | `git pull --rebase origin main --allow-unrelated-histories` 再 push |
| `Authentication failed` | 用了账号密码 | 改用 PAT（第 3 节） |
| `Connection timed out` | 网络 | 见第 6 节 |
| `File ... is 105 MB` | 大文件 | 本项目没有；别把 `data/raw/*.tif` 加进来 |

## 8. 建议：公开前再确认一遍

- [ ] README 里的免责声明还在（不构成适航/合规结论）。
- [ ] 没有个人信息（电话、身份证、住址）。
- [ ] 航图 PDF 没有直接放进仓库（版权）；仓库只放引用信息，见 `docs/data_sources.md`。
- [ ] 合成数据说明清楚，不写「深圳真实人口」。

## 9. 本机已配置记录（2026-11-21，可跳过）

这台电脑当时 HTTPS 到 GitHub 被重置（`Recv failure: Connection was reset`），
但 `ssh.github.com:443` 能握手，所以最终走 **SSH over 443**。已做的配置：

1. 生成 Ed25519 密钥（**空口令**）：`~/.ssh/id_ed25519_github`
   （公钥已加到 GitHub → Settings → SSH and GPG keys）。
2. `~/.ssh/config`：
   ```
   Host github.com
       HostName ssh.github.com
       Port 443
       User git
       IdentityFile ~/.ssh/id_ed25519_github
       IdentitiesOnly yes
       StrictHostKeyChecking accept-new
   ```
3. `origin` = `git@github.com:yir97166/lowalt-route-risk.git`。
4. **关键坑**：git 自带的 MSYS ssh 处理不了中文用户名路径
   （报 `Could not create directory '/c/Users/337 256 352/...'`），
   所以让 git 改用 Windows 自带 OpenSSH：
   ```powershell
   git config --global core.sshCommand '"C:/Windows/System32/OpenSSH/ssh.exe" -F "C:/Users/弋昊阳/.ssh/config"'
   ```
5. 验证：`ssh -T git@github.com` → `Hi yir97166! ...`；
   `git push -u origin main`、`git push origin v0.1` 均成功；
   `git ls-remote origin` 能看到 `refs/heads/main` 和 `refs/tags/v0.1`。

以后每天只需要 `git add -A` → `git commit -m "..."` → `git push`，不再需要 token 或代理。

---

做完把仓库链接发我，我可以在 README 顶部补一行 GitHub 徽章和链接。

