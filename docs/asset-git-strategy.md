# 资产 Git 上传方案

## 决策：模型统一使用 LFS

2026-10-19 本地盘点：24 个 GLB 共 22.55 MB，24 个 `.blend` 共 11.54 MB，最大文件 `assets/city/model.glb` 约 3.98 MB（十进制）。2026-10-20 起通过 `.gitattributes` 对所有 `.blend`、`.glb` 启用 LFS；本机已安装 Git LFS 3.8.0，并初始化本仓库过滤器与 pre-push hook。

当前体积可以直接提交普通 Git，但模型频繁迭代会累积二进制历史。因此从首次提交起统一使用 LFS，避免后续再迁移；不按单个模型大小混用两种策略。

| 内容 | 存储方式 |
| --- | --- |
| `assets/*/model.blend` | LFS，可编辑源文件，贴图打包在内 |
| `assets/*/model.glb` | LFS，已验收的运行时资产 |
| 代码、脚本、文档、配置及 `.gitattributes` | 普通 Git |
| 备份、预览、评审截图、日志、缓存、构建包 | 不提交，遵循[资产工作流](blender-asset-workflow.md) |

同一次模型修改应一起提交源文件、对应 GLB 和契约变更。稳定路径只保留最新产物，历史由版本控制保存；不建版本目录，也不把 GLB 作为必须现场运行 Blender 才能获得的构建依赖。

## 免费额度与规模

按 2026-10-19 [GitHub 官方说明](https://docs.github.com/en/billing/concepts/product-billing/git-lfs)，Free、Pro 和 Free organization 均包含 **10 GiB 存储＋每月 10 GiB 下载带宽**；Team/Enterprise Cloud 为 250 GiB。额度属于账户，不是每个仓库单独享有。

当前全套约 **32.51 MiB（0.0318 GiB）**，占 10 GiB 的 **0.32%**。假设无其他仓库占用、文件大小不变，即使全套每次都变化，100 份也约 3.18 GiB；月下载额度约可承担 300 次全套无缓存下载。当前小团队开发足够，但 CI 下载、他人克隆和历史迭代均需计入。

这里评估的是项目规模，不是账户剩余额度；尚未访问账户账单。存储历史不会每月清空；下载带宽按计费周期重置。建议在 GitHub 设置 LFS 预算上限并关注用量通知，超额可能阻断下载或产生费用，取决于账户预算配置。

## 提交与检查

跟踪规则已提交到 `.gitattributes`，无需每次重新配置。在仓库根目录检查模型提交：

```sh
git add assets
git lfs ls-files
git lfs status
git diff --cached --stat
git show :assets/forest-tile/model.glb
```

最后一条应显示以 `version https://git-lfs.github.com/spec/v1` 开头的短指针，而不是模型二进制。检查暂存内容后再提交、推送；正常 `git push` 通过 LFS hook 上传模型实体。之后用新目录完整克隆、执行 `git lfs pull` 和 `pnpm test`，验证远端资产可用。

模型从首次提交起使用 LFS，无需迁移历史。若后续发现模型误按普通 Git 提交，应另行评估；不要直接运行 `git lfs migrate` 或强推改写共享历史。

## 协作与 CI

- 协作者先安装 LFS，再克隆；已有检出执行 `git lfs install --local`、`git lfs pull`。加载或打包前必须取得真实 GLB，不能把 LFS 指针当模型发布。
- GitHub Actions 检出时启用 `actions/checkout` 的 `lfs: true`；开发、测试及发布构建均在取得 LFS 资产后进行。Electron 最终安装包仍内置真实 GLB，不要求玩家安装 LFS。
- 普通 Git 记录指针，LFS 保存实体；同一路径覆盖新版本**不会删除远端旧版本**。每次变更按完整文件计算新增存储，下载消耗带宽；只提交验收后的模型，不推送每轮临时草稿。
- 不把 ZIP 下载视为可靠的资产获取流程，优先使用 Git + LFS 克隆。无需同时维护网盘/CDN 副本作为运行时依赖。

依据：[GitHub 大文件限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)、[LFS 存储与带宽计费](https://docs.github.com/en/billing/concepts/product-billing/git-lfs)、[Git LFS 官方使用说明](https://github.com/git-lfs/git-lfs#readme)。配额以仓库所有者账户实时显示为准。
