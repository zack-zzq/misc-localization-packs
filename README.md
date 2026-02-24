# Misc Localization Packs

综合本地化资源包 — 自动合并多个 Modrinth 上的本地化资源包为一个统一资源包。

**目标 Minecraft 版本**: 1.20.1
**Pack Format**: 15
**最后更新**: 2026-02-24 16:15 UTC

## 📦 包含的资源包

| 资源包 | 说明 | 版本 | 发布日期 | Modrinth 链接 |
| --- | --- | --- | --- | --- |
| AE2 指南中文翻译 | Applied Energistics 2 指南书简体中文翻译 | 2.0 | 2025-05-10 | [链接](https://modrinth.com/resourcepack/ae2-1.20.1-guide-zh_cn) |
| Explorer's Compass structure Translation | 探险者(探险家)指南针结构汉化材质包，可以让你的旅途更加愉快₍˄·͈༝·͈˄*₎◞ ̑̑ | v2.9 | 2026-02-02 | [链接](https://modrinth.com/resourcepack/ecst) |

## 🚀 使用方式

1. 前往 [Releases](../../releases) 页面下载最新的资源包 `.zip` 文件
2. 将 `.zip` 文件放入 Minecraft 的 `resourcepacks` 文件夹
3. 在游戏内启用资源包

## ➕ 添加新的资源包

编辑 `config/packs.json`，在 `packs` 数组中添加新条目：

```json
{
  "slug": "modrinth-project-slug",
  "name": "资源包显示名称",
  "description": "简短描述"
}
```

提交后，GitHub Actions 会自动拉取并合并新的资源包。

## ⚙️ 自动更新

本项目通过 GitHub Actions 每 6 小时自动检查各源资源包是否有更新。
如有新版本，会自动下载合并，更新本 README，并创建新的 Release。

也支持在 Actions 页面手动触发更新。

---

*本文件由 [merge_packs.py](scripts/merge_packs.py) 自动生成，最后更新于 2026-02-24 16:15 UTC*
