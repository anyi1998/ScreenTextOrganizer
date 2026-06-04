# 图片文字整理工具 v1 实施计划

## Summary

在 `H:\project\tools\pic_text_pull` 从零搭建一个本地 Web 工具，用来整理手机截图、书摘、前端面试题图片。

v1 工作流：

`选择图片目录 -> 扫描入库 -> PaddleOCR 提取文字 -> Ollama 可选分析 -> 表格审阅 -> 复制文字/放大图片/保留/移入回收站 -> 导出结果`

## Key Changes

- 后端：Python 3.12 + FastAPI + SQLite。
- 前端：Vite + React + TypeScript。
- OCR：PaddleOCR first, RapidOCR fallback, Ollama vision fallback.
- 本地 AI 增强：Ollama `qwen3.5:2b-q4_K_M`，可选。
- 删除：`send2trash` 移入 Windows 回收站。
- 数据持久化：`data/pic_text_pull.db`。
- 缩略图：`data/thumbnails/`。

## Backend API

- `POST /api/scan`：扫描图片目录并入库。
- `POST /api/ocr/run`：批量 OCR。
- `POST /api/analyze/run`：规则分析 + 可选 Ollama 分析。
- `GET /api/items`：分页、筛选、搜索图片记录。
- `GET /api/items/{id}/image`：返回原图。
- `GET /api/items/{id}/thumbnail`：返回缩略图。
- `PATCH /api/items/{id}`：更新状态、标签、备注、OCR 文本。
- `POST /api/items/{id}/trash`：移动原图到系统回收站。
- `GET /api/export`：导出 CSV/JSON。

## Test Plan

- 重复扫描不重复入库。
- 缩略图生成成功。
- OCR 成功/失败状态正确。
- 规则分析字段完整。
- Ollama 不可用时能降级。
- 删除接口只移动到回收站。
- 表格分页、搜索、筛选、预览、复制、状态更新可用。

## Assumptions

- 原图不复制进项目，只记录路径并生成缩略图。
- v1 不接入云端 AI。
- PaddleOCR、RapidOCR 和 Ollama 依赖安装需要网络。
- 删除失败时不永久删除。
