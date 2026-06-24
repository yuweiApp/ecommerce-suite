# 电商套图生成（E-commerce Suite）

> **版本**：1.0.14 ｜ **作者**：Fotor ｜ **License**：MIT ｜ **平台**：Linux / macOS / Windows

基于一张或多张商品参考图，通过 **Fotor Business OpenAPI** 的电商套图能力
（`ecommercelistingset`）生成 Listing / A+ 套图。支持公网图片 URL 与
`data:image/...` Base64 输入，可按平台、销售国家、图内文案语言、图片比例、商品卖点、
品牌风格和自定义场景生成整组电商图。

## 功能特性

- **异步套图生成**：提交任务后自动轮询 `GET /v1/aiart/tasks/{taskId}`，直到成功、失败或超时。
- **自动/自定义场景**：不传 `scenes` 时由服务端自动推荐；也可指定 `主图`、`场景图`、`卖点图`、`模特穿搭图` 等场景。
- **多市场适配**：按销售国家影响模特地域表达，按 i18n 代码控制图内文案语言；`language=""` 表示无文案。
- **品牌风格套用**：可选传入品牌描述与品牌 logo，统一套图视觉调性。
- **积分预检查**：提交前查询 `GET /v1/credits`，按 `num × 8` 估算本次消耗。

## API 概览

| 环境 | Base URL |
|---|---|
| 沙盒 | `https://api-b-sandbox.fotor.com` |
| 正式 | `https://api-b.fotor.com` |

| 能力 | 方法 | 路径 |
|---|---|---|
| 查询积分 | `GET` | `/v1/credits` |
| 提交任务 | `POST` | `/v1/aiart/ecommercelistingset` |
| 查询任务 | `GET` | `/v1/aiart/tasks/{taskId}` |

默认 provider 为 `skill`，提交任务无需在 URL 中指定 provider。接口鉴权使用：

```http
Authorization: Bearer <your_api_key>
Content-Type: application/json
```

任务状态：

| status | 含义 |
|---|---|
| `0` | 进行中 |
| `1` | 已完成，可能包含部分场景失败 |
| `2` | 失败 |

建议轮询间隔 3-5 秒，单任务超时约 10 分钟。

## 环境要求

- Python 3.13
- `uv`
- 有效的 Fotor Business OpenAPI key

脚本依赖 `httpx` 与 `python-dotenv`，推荐用 `uv run --with` 临时带依赖运行。

## 安装

```bash
git clone <repo-url>
cd ecommerce-suite
uv --version
```

## 配置

API key 通过环境变量 `FOTOR_ECOMMERCE_SUITE_API` 提供。脚本会自动加载与 `skills/`
同级目录下的 `.env` 与 `.env.local`，且 `.env.local` 覆盖 `.env`：

```bash
# .env.local
FOTOR_ECOMMERCE_SUITE_API=你的_fotor_business_openapi_key
```

也可以在命令行中用 `--api-key` / `--api_key` 直接传入。生产环境请把 `--api` 设置为
`https://api-b.fotor.com`；默认使用沙盒 `https://api-b-sandbox.fotor.com`。

## 使用方法

基础调用（服务端自动推荐场景，生成 4 张）：

```bash
uv run --with httpx --with python-dotenv python skills/ecommerce-suite/scripts/generate_suite.py \
  --image-url "https://example.com/product.jpeg" \
  --num 4 \
  --platform Amazon \
  --country American \
  --language en_US \
  --aspect-ratio 1:1 \
  --image-type listing
```

指定场景：

```bash
uv run --with httpx --with python-dotenv python skills/ecommerce-suite/scripts/generate_suite.py \
  --image-url "https://example.com/product-1.jpg" \
  --image-url "https://example.com/product-2.jpg" \
  --scenes "主图,场景图,卖点图,模特穿搭图" \
  --num 4 \
  --platform Amazon \
  --country American \
  --language en_US \
  --aspect-ratio 1:1 \
  --image-type listing
```

带商品卖点与品牌信息：

```bash
uv run --with httpx --with python-dotenv python skills/ecommerce-suite/scripts/generate_suite.py \
  --image-url "https://example.com/product.jpeg" \
  --num 4 \
  --platform Amazon \
  --country American \
  --language en_US \
  --aspect-ratio 1:1 \
  --image-type listing \
  --key-info "便携式榨汁杯，核心卖点是轻量、易清洗、户外可用" \
  --brand-info "品牌风格年轻、清爽，主色为薄荷绿和白色" \
  --brand-logo "https://example.com/logo.png"
```

> 多张参考图：重复传 `--image-url`。
>
> Base64 输入：`--image-url "data:image/png;base64,..."`。
>
> 纯净无文字图：传 `--language ""`。

## 参数说明

| 参数 | 必填 | 默认/约束 | 含义 |
|---|---:|---|---|
| `--image-url` | 是 | 至少 1 个 | 商品参考图 URL 或 `data:image/...` Base64，可重复传多次 |
| `--scenes` | 否 | 不传=自动推荐 | 自定义套图场景，逗号分隔 |
| `--num` | 否 | 默认 4，范围 1-8 | 生成图片张数；计费与场景数量无关 |
| `--platform` | 否 | `Amazon` | 电商平台 |
| `--country` | 否 | `American` | 销售国家，影响模特地域表达 |
| `--language` | 否 | `en_US` | 图内文案语言 i18n 代码；空字符串表示无文案 |
| `--aspect-ratio` | 否 | `1:1` | 输出比例，如 `1:1`、`3:4`、`4:3`、`16:9`、`9:16` |
| `--image-type` | 否 | `listing` | 图片类型，通常为 `listing` 或 `aplus` |
| `--key-info` | 否 | 空 | 商品关键信息：名称、卖点、受众、使用场景等 |
| `--brand-info` | 否 | 空 | 品牌描述：配色、字体、调性等 |
| `--brand-logo` | 否 | 空 | 品牌 logo 图片 URL 或 Base64 |
| `--api` | 否 | 沙盒地址 | Fotor Business OpenAPI Base URL |
| `--api-key` / `--api_key` | 否 | 环境变量 | Fotor Business OpenAPI key |
| `--poll-interval` | 否 | 3 秒 | 查询任务状态的轮询间隔 |
| `--timeout` | 否 | 600 秒 | 单任务等待超时时间 |

`num` 表示本次生成的图片张数，积分消耗为 `creditsIncrement = num × 8`。例如
`num=4` 预计消耗 32 积分，`num=8` 预计消耗 64 积分。

## 输出

脚本运行时会先打印积分、任务提交和轮询进度。成功后最后输出标准查询结果 JSON：

```json
{
  "code": "000",
  "msg": "success",
  "data": {
    "taskId": "9f4f0a6d0e9f41e4a87ad862cda3c9ad",
    "status": 1,
    "type": "ecommercelistingset",
    "resultUrl": "https://pub-static.fotor.com/aigc/business/.../9f4f0a6d0e9f41e4a87ad862cda3c9ad_0.jpg",
    "result": [
      {
        "name": "主图",
        "success": true,
        "url": "https://pub-static.fotor.com/aigc/business/.../9f4f0a6d0e9f41e4a87ad862cda3c9ad_0.jpg"
      },
      {
        "name": "场景图",
        "success": false,
        "error": "生图失败 401"
      }
    ],
    "hasHsfw": false,
    "creditsIncrement": 32,
    "createTime": 1730000000000,
    "updateTime": 1730000300000,
    "businessId": "70c48bfd1c65434892de977ba881ca6a"
  }
}
```

- `data.resultUrl` 是首张成功成图 CDN URL。
- `data.result` 是分场景结果数组；成功项包含 `url`，失败项包含 `error`。
- `status=1` 可能仍有部分场景失败，请遍历 `data.result` 判断每个场景。

## 常见错误

| 现象/错误 | 可能原因 | 建议 |
|---|---|---|
| `image_urls is required` | 未传参考图，或 URL 过滤后为空 | 至少传 1 个有效 URL/Base64 |
| `num must be between 1 and 8` | 生成张数越界 | 把 `--num` 调整到 1-8 |
| `upload base64 image failed` | Base64 图片上传失败 | 检查 Base64 格式和请求体大小 |
| `No enough credits` / `code=510` | 积分不足 | 充值后重试 |
| `Rate limit` | 并发过高 | 降低提交频率 |
| 长时间 `status=0` | 生成排队或下游繁忙 | 继续轮询至超时 |
| `status=2` + `msg` | 生成失败或无有效成图 | 检查参考图质量与参数 |

## 目录结构

```text
ecommerce-suite/
├── README.md
└── skills/
    └── ecommerce-suite/
        ├── SKILL.md
        └── scripts/
            └── generate_suite.py
```

## License

MIT
