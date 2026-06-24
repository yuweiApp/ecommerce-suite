---
name: ecommerce-suite
description: Use when the user wants to generate a set of e-commerce product images (套图 / Listing 主图集 / 多角度细节图 / 场景穿搭图 / 卖点图) from one or more product photo URLs or data:image Base64 inputs. Returns per-scene results with each image name, success flag, generated URL, or error.
version: 1.0.15
author: Fotor
license: MIT
platforms: [ linux, macos, windows ]
tags: [ ecommerce, aigc, product-images, 套图, amazon, listing, image-generation ]
related_skills: [ ]
prerequisites:
  env_vars: [ FOTOR_ECOMMERCE_SUITE_API ]
required_environment_variables:
  - name: FOTOR_ECOMMERCE_SUITE_API
    prompt: Fotor e-commerce suite API key
    help: Set this to your Fotor Business OpenAPI key.
    required_for: generating e-commerce listing images
metadata:
  openclaw:
    emoji: "🛍️"
    primaryEnv: FOTOR_ECOMMERCE_SUITE_API
    requires:
      anyBins: [ "python3", "python" ]
---

# 电商套图生成（E-commerce Suite）

## When to Use

用户给了商品图片 URL 或 `data:image/...` Base64，想生成整组电商套图（Amazon/电商主图、Listing 主图集、
多角度细节图、场景穿搭图、卖点图等）。

**Don't use for**：单纯改图内文字（OCR/文字编辑）、非电商的通用 AI 生图。

## 调用流程（重要）

业务内容参数需要你按下方推荐值显式传入；用户未提供的可选信息不要编造。

底层接口使用 **Fotor Business OpenAPI 电商套图异步任务**：
- 查询积分：`GET /v1/credits`
- 提交任务：`POST /v1/aiart/ecommercelistingset`
- 查询任务：`GET /v1/aiart/tasks/{taskId}`
- 默认 provider 为 `skill`，提交任务不要在 URL 中额外拼 provider；兼容路径由服务端处理。
- 任务状态：`0` 进行中，`1` 成功，`2` 失败；脚本会自动轮询到成功、失败或超时。

> 🚦 **硬性规则：运行脚本前【必须】先让用户确认设置。** 这是一道阻塞闸门——
> 在用户回复确认（如「按这个生成」「OK」「可以」）之前，**绝不允许**调用 `terminal`
> 运行 `generate_suite.py`。哪怕用户只说「生成亚马逊套图」「帮我出套图」这类话，
> 那也只是**发起请求**、不是确认，仍要先走完下面三步、等用户拍板。违反此规则即为错误。

按下面三步走：

1. **抽取**：从用户需求里抽取已明确的参数。商品图 URL 是硬性前提——没有就先向用户要。
   同时留意用户有没有顺带说出【商品关键信息】（产品名称/核心卖点/目标受众/使用场景），有就记下。
2. **补全 + 推荐**：对用户【没说】的参数，用下表推荐值补全。**商品关键信息是可选项、不推荐默认值**：
   用户提供了就用，没提供就【留空、不要编造】（系统会纯按商品图分析）。
3. **确认后再执行**：把【完整设置】（用户给的 + 你推荐的）汇总给用户，**含商品关键信息这一项**
   （用户给了就回显，没给就标「未提供，按商品图自动分析」），**等用户确认或调整后，才运行脚本**。
   用户改了哪项就用哪项。

> 免确认（满足任一即可，跳过等待、直接生成；但执行前仍要把最终设置打印告知用户）：
> 1. 用户【用原话明确表示】不需要确认——例如「不用确认直接出」「别问了直接生成」「你看着办，直接跑」。
> 2. 用户输入里【已经把这 4 项关键设置全部说清】：图片地址、平台/市场、图内文案语言、套图比例。
>    这 4 项都齐了，说明用户意图明确，可直接生成（生成张数、商品关键信息等其余项缺了
>    就用推荐值/留空，不必为它们再追问）。只要 4 项里缺任意一项，就【照常走三步、必须确认】。
>
> 注意：「生成亚马逊套图」「帮我做套图」这类只给了图片、没说全 4 项的普通请求，【不算】免确认，照常确认。

**向用户描述时一律用自然语言，不要出现 `--num`、`--platform`、`--language` 这类命令行参数名**
（这些只在你内部拼命令时用）。

**⚠️ 套图画面默认由服务端自动推荐——确认环节【绝不要】自己列出/预测每张是什么画面**
（如「1 张白底主图、1 张模特上身图、1 张细节图、1 张场景图」这类清单一律不要写）。
具体每张拍什么是流水线运行时才决定的，你提前编一份只会与实际结果不符、误导用户。
确认时只说「共几张，按商品自动推荐画面」即可；真实场景在脚本输出里。
只有当用户明确指定场景/套图类型（如「主图、场景图、卖点图、模特穿搭图」）时，才在确认里回显这些场景，
并在执行时传 `--scenes`；不要替用户自行补一组场景。

**追问/确认请用 Markdown 列表格式化输出**（不要用表格）：
加小标题、用列表逐项列出设置，让用户一眼看清。例如：

> **请确认本次套图设置** 👇
>
> - **生成张数**：4 张（按商品自动推荐画面）
> - **平台 / 市场**：亚马逊 · 美国（欧美模特）
> - **图内文案**：英文
> - **套图比例**：1:1 方形
> - **图片类型**：Listing
> - **商品关键信息**（可选，未提供则按商品图自动分析）：
>   - 产品名称：未提供
>   - 核心卖点：未提供
>   - 目标受众：未提供
>   - 使用场景：未提供
> - **品牌信息**（可选，未提供则不套用品牌风格）：
>   - 品牌风格描述：未提供
>   - 品牌 logo：未提供
>
> 商品关键信息、品牌信息你有哪些就告诉我，能让套图更贴合；没有也行。
> 没问题就回 **「按这个生成」**；想改直接说，例如「出 5 张」「不要文字」
> 「面向日本市场」「主打显瘦、约会穿搭」「套上我的品牌色和 logo」。

用户确认后，再把这些设置翻成对应命令行参数去调用脚本。

### 推荐值（供第 2 步补全缺失项）

| 参数 | 推荐值 | 说明 |
|---|---|---|
| `--num` | `4` | 自动推荐模式下生成 4 张（第 1 张固定主图） |
| `--platform` | `Amazon` | 目标平台 |
| `--country` | `American` | 决定模特种族；按目标市场调整（如日本 `Japanese`） |
| `--language` | `en_US` | 图内文案语言 i18n 代码；按目标市场调整（德国 `de_DE`、日本 `ja_JP`）；要纯净无文字图则用 `""` |
| `--aspect-ratio` | `1:1` | Amazon 主图常用方图 |
| `--image-type` | `listing` | 图片类型；通常为 `listing` / `aplus` |

生成张数 → `--num`（推荐 4，合法范围 1–8）。`num` 表示本次生成的图片张数，计费按 `num × 8` 积分，
与 `scenes` 数量无关。

**套图场景（可选）**：用户明确指定套图类型/场景时，把这些名称按逗号拼成 `--scenes` 传入，
例如 `--scenes "主图,场景图,卖点图,模特穿搭图"`。用户没指定就【不要传】或传空，使用服务端自动推荐模式。

**商品关键信息（可选）**：若用户提供了产品名称、核心卖点、目标受众、使用场景等信息，
整理成一段文本通过 `--key-info` 传入，能让分析更贴合卖家意图。用户没提供就【不要传】，
也【不要自己编造】——系统会纯按商品图智能分析。

**品牌信息（可选）**：用户想让套图带上自己的品牌风格时才用，两项各自独立、能传几样传几样，
没提供就【一律不传】，也【不要自己编造】：
- `--brand-info`：用户【用自然语言】描述的品牌信息，原话整理成一段文本传入即可（不用拆成
  结构化的色值/字段）。比如用户说「主色是深蓝配少量金色、整体高级简约、字体偏现代无衬线」，
  就把这段描述原样传进去。非主图会据此统一营造该品牌的视觉调性；主图保持干净不套。
- `--brand-logo`：品牌 logo 的【完整图片 URL】或 `data:image/...` Base64。用户给的链接/内容原样传入，
  【不要】自己臆造地址或转写图片内容。用户提供了就传，没提供就不传。

## 前置环境变量（必需）

运行脚本前，【必须】确保运行环境中已配置 `FOTOR_ECOMMERCE_SUITE_API`
（Fotor Business OpenAPI apikey）。脚本会把该 key 放在请求头
`Authorization: Bearer <key>` 中。

## 如何调用

脚本路径用当前技能安装位置下的 `skills/ecommerce-suite/scripts/generate_suite.py`。

脚本依赖 `httpx`，统一用 `uv run --with httpx python`
运行（这样无论当前环境是否已装该依赖，都能临时备齐、稳定运行）。

脚本会在提交任务前调用 `GET /v1/credits` 查询积分，并按 `num × 8` 估算本次消耗：
- 若识别到余额且余额不足，脚本会直接停止，不提交生成任务。
- 若积分响应的余额字段无法识别，脚本会打印 `data` 内容并继续提交；提交接口仍会按标准错误返回
  `No enough credits` / `code=510` 等积分不足信息。

确认后调用（张数用 `--num`，不传 `--scenes` 表示按商品自动推荐画面）：

```bash
uv run --with httpx python skills/ecommerce-suite/scripts/generate_suite.py \
  --image-url "https://.../product.jpeg" \
  --num 4 --platform Amazon --country American --language en_US --aspect-ratio 1:1 --image-type listing
```

用户明确指定场景时，追加 `--scenes`（没有指定就不加）：

```bash
uv run --with httpx python skills/ecommerce-suite/scripts/generate_suite.py \
  --image-url "https://.../product.jpeg" \
  --num 4 --platform Amazon --country American --language en_US --aspect-ratio 1:1 --image-type listing \
  --scenes "主图,场景图,卖点图,模特穿搭图"
```

用户提供了品牌信息时，按需追加品牌参数（没有的就不加）：

```bash
uv run --with httpx python skills/ecommerce-suite/scripts/generate_suite.py \
  --image-url "https://.../product.jpeg" \
  --num 4 --platform Amazon --country American --language en_US --aspect-ratio 1:1 --image-type listing \
  --brand-info "主色深蓝配少量金色，整体高级简约，字体偏现代无衬线" \
  --brand-logo "https://.../logo.png"
```

## 参数

| 参数 | 必填 | 含义 |
|---|---|---|
| `--image-url` | ✅ | 商品参考图 URL 或 `data:image/...` Base64；有多张就重复传多次 |
| `--scenes` | 可选 | 自定义套图场景，逗号分隔；不传或空数组时使用服务端自动推荐 |
| `--num` | 建议传 | 生成几张（1–8，推荐 4）。图片张数与场景数量无关 |
| `--platform` | 建议传 | 目标平台（如 `Amazon`） |
| `--country` | 建议传 | 销售国家，**决定图中模特的种族** |
| `--language` | 建议传 | 图内文案语言 i18n 代码（如 `en_US`）。**传 `""` 表示整组图都不加任何文字** |
| `--aspect-ratio` | 建议传 | 图片比例：`1:1` `2:3` `3:2` `3:4` `4:3` `16:9` `9:16` |
| `--image-type` | 建议传 | 图片类型，通常为 `listing` 或 `aplus` |
| `--key-info` | 可选 | 商品关键信息：产品名称/核心卖点/目标受众/使用场景，自由文本。用户提供才传，别编造 |
| `--brand-info` | 可选 | 用户【自然语言】描述的品牌信息（配色/字体/调性等），原话整理成文本传入，别拆字段、别编造 |
| `--brand-logo` | 可选 | 品牌 logo 的【完整 URL】或 `data:image/...` Base64。用户提供才传，别编造地址 |
| `--poll-interval` | 可选 | 轮询间隔秒数，默认 3 秒 |
| `--timeout` | 可选 | 单任务等待超时秒数，默认 600 秒 |

## 返回结构

脚本会先逐步打印中文进度，任务成功后最后输出一段符合
`GET /v1/aiart/tasks/{taskId}` 查询接口标准格式的 JSON：

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

- `data.resultUrl` 是首张成功成图 URL。
- `data.result` 是分场景对象数组。每项包含 `name`、`success`，成功时有 `url`，失败时有 `error`。
- `status=1` 可能包含部分失败场景；请遍历 `data.result` 判断每个场景的成败，不要只看顶层状态。
- 若脚本提示「无法连接接口 / 任务失败 / 等待超时 / 任务完成但未返回成图 URL」，说明生成失败或服务未就绪，如实告知用户并可稍后重试，**不要编造图片地址**。
