# 电商套图生成（E-commerce Suite）

> **版本**：1.0.7 ｜ **作者**：Fotor ｜ **License**：MIT ｜ **平台**：Linux / macOS / Windows

根据一张或多张商品图片，一键生成整组电商套图——Amazon/电商主图、Listing 主图集、
A+ 模块图、多角度细节图、场景穿搭图、卖点图等。给定商品图 URL，最终返回每张图的
生成图片 URL。

## 功能特性

- **整组套图一次生成**：第 1 张固定为主图，其余按商品自动推荐画面（1–8 张）。
- **多市场适配**：按销售国家决定模特种族，按 i18n 代码控制图内文案语言。
- **品牌风格套用**：可选传入品牌风格描述与 logo，统一非主图的视觉调性。

## 环境要求

- Python 3.13（脚本以 `uv run` 调用，依赖 `httpx`、`python-dotenv`）
- 一个有效的生图 apikey（配置见下方「配置」）

## 安装

```bash
# 安装 uv（若尚未安装）：https://docs.astral.sh/uv/
uv --version

# 克隆仓库
git clone <repo-url>
cd ecommerce-suite
```

依赖由 `uv run` 自动解析；如需手动安装：`uv pip install httpx`。

## 配置

生图所需的 apikey 通过环境变量提供。脚本会自动从【与 `skills` 同级目录】的 `.env`
文件加载（文件不存在则跳过）：

```bash
# .env
FOTOR_ECOMMERCE_SUITE_API=你的生图apikey
```

也可在运行时用 `--api_key` 直接传入（优先级高于环境变量）。后端接口地址已内置默认值，
如需指向其它环境再用 `--api` 覆盖。

## 使用方法

基础调用（自动推荐画面，生成 4 张）：

```bash
uv run python skills/ecommerce-suite/scripts/generate_suite.py \
  --image-url "https://.../product.jpeg" \
  --num 4 --platform Amazon --country American \
  --language en_US --aspect-ratio 1:1
```

带品牌信息：

```bash
uv run python skills/ecommerce-suite/scripts/generate_suite.py \
  --image-url "https://.../product.jpeg" \
  --num 4 --platform Amazon --country American \
  --language en_US --aspect-ratio 1:1 \
  --brand-info "主色深蓝配少量金色，整体高级简约，字体偏现代无衬线" \
  --brand-logo "https://.../logo.png"
```

> 多张参考图：重复传 `--image-url` 即可。
> 纯净无文字图：`--language ""`。

## 参数说明

| 参数 | 必填 | 含义 |
|---|---|---|
| `--image-url` | ✅ | 商品参考图 URL，可重复传多次 |
| `--num` | 建议 | 生成张数（1–8，推荐 4）；第 1 张固定主图 |
| `--platform` | 建议 | 目标平台（如 `Amazon`） |
| `--country` | 建议 | 销售国家，**决定模特种族**（如 `American`、`Japanese`） |
| `--language` | 建议 | 图内文案语言 i18n 代码（`en_US`、`de_DE`、`ja_JP`…）；传 `""` 表示整组不加文字 |
| `--aspect-ratio` | 建议 | 图片比例：`1:1` `2:3` `3:2` `3:4` `4:3` `16:9` `9:16` |
| `--scenes` | 可选 | 自定义套图类型，逗号分隔；不传 = 自动推荐 |
| `--key-info` | 可选 | 商品关键信息（产品名/卖点/受众/场景），自由文本；用户提供才传 |
| `--brand-info` | 可选 | 自然语言描述的品牌信息（配色/字体/调性），自由文本 |
| `--brand-logo` | 可选 | 品牌 logo 的完整图片 URL；仅出现在品牌故事图上（且仅无图内文案时） |
| `--api_key` | 可选 | 生图 apikey；默认取环境变量 `FOTOR_ECOMMERCE_SUITE_API` |
| `--api` | 可选 | 后端接口地址；已内置默认值，可覆盖 |

## 输出

运行结束后输出结构化 JSON：

```json
{
  "productName": "...",
  "productDescription": "...",
  "items": [
    { "name": "...", "aspectRatio": "1:1", "imageUrls": ["..."] }
  ]
}
```

## 目录结构

```
ecommerce-suite/
├── README.md                           # 项目说明
└── skills/
    └── ecommerce-suite/
        ├── SKILL.md                    # 技能定义（Hermes Agent Skill 元数据与调用规范）
        └── scripts/
            └── generate_suite.py       # 套图生成脚本（命令行入口）
```

## License

MIT
