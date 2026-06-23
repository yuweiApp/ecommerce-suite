import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

# Windows 控制台默认 GBK，中文/德语等非 GBK 字符直接 print 会 UnicodeEncodeError
sys.stdout.reconfigure(encoding='utf-8')

# 配置（FOTOR_ECOMMERCE_SUITE_API 等）从【与 skills 同级】的 .env 读取——即本技能 SKILL.md 目录
# （skills/ecommerce-suite）的【上 2 级】、本脚本所在 scripts/ 的上 3 级。该 .env 由使用者自行
# 维护：脚本【只加载、不创建】（文件不存在则直接跳过）；若其中定义了 FOTOR_ECOMMERCE_SUITE_API，
# 则【覆盖】当前进程已有的同名环境变量（override=True）。必须在读取环境变量之前完成加载。
_ENV_PATH = Path(__file__).resolve().parents[1].parents[1] / '.env'  # SKILL.md 目录的上 2 级
if _ENV_PATH.is_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=_ENV_PATH, override=True)
    except ImportError:
        pass  # 未安装 python-dotenv 时，退化为仅使用进程已有的环境变量

def _parse_args() -> argparse.Namespace:
    # 内容参数均【不设默认值】：应由调用方（agent，按 SKILL.md 的引导与推荐）显式传入；
    # 未传的参数不会进入请求体，由服务端决定如何处理。
    ap = argparse.ArgumentParser(description='电商套图生成客户端')
    ap.add_argument('--image-url', action='append', default=[], dest='image_urls', required=True,
                    help='商品参考图 URL（可重复多次）')
    ap.add_argument('--scenes', help='自定义套图类型，逗号分隔；不传=自动推荐')
    ap.add_argument('--num', type=int, help='自动模式推荐张数（1-8）')
    ap.add_argument('--platform', help='目标平台（如 Amazon）')
    ap.add_argument('--country', help='销售国家（决定模特种族，如 American）')
    ap.add_argument('--language', help='图内文案语言 i18n 代码（如 en_US）；传 "" 表示整组不加文字')
    ap.add_argument('--aspect-ratio', dest='aspect_ratio', help='图片比例（如 1:1）')
    ap.add_argument('--key-info', dest='key_info',
                    help='商品关键信息（可选）：产品名称/核心卖点/目标受众/使用场景，自由文本')
    # 品牌信息（均可选）：自然语言描述 + 完整 logo URL
    ap.add_argument('--brand-info', dest='brand_info',
                    help='用户用自然语言描述的品牌信息（配色/字体/调性/氛围等），自由文本')
    ap.add_argument('--brand-logo', dest='brand_logo',
                    help='品牌 logo 的完整图片 URL；仅会出现在品牌故事图上（且仅无图内文案时）')
    ap.add_argument('--api', default='http://192.168.84.54:8077', help='后端套图接口地址')
    ap.add_argument('--api_key', dest='api_key', default=os.getenv('FOTOR_ECOMMERCE_SUITE_API'),
                    help='FotorClient 生图 apikey（默认取环境变量 FOTOR_ECOMMERCE_SUITE_API），随请求传给后端')
    return ap.parse_args()


def _handle_event(ev: dict, state: dict) -> None:
    t = ev.get('type')
    if t == 'step':
        # 不暴露内部各阶段名称，只给一次性的通用进度提示（避免泄露流水线实现细节）。
        if ev.get('status') == 'start' and not state.get('progress_shown'):
            state['progress_shown'] = True
            print('… 正在生成套图，请稍候')
    elif t == 'scenes':
        d = ev['data']
        print('   套图场景（{}，共 {} 张）:'.format(
            '自动推荐' if d['mode'] == 'auto' else '自定义', len(d['scenes'])))
        for i, s in enumerate(d['scenes'], 1):
            desc = '：' + s['description'] if s.get('description') else ''
            print('     {}. {}{}'.format(i, s['name'], desc))
    elif t == 'image':
        if ev.get('error'):
            print('   ⚠️ 生图失败 [{}]: {}'.format(ev.get('name'), ev['error']))
        else:
            print('   🖼️ 生图完成 [{}] {}'.format(ev.get('name'), ev.get('url')))
    elif t == 'done':
        state['final'] = ev['data']
    elif t == 'error':
        print('❌ 出错: {}'.format(ev.get('msg')))
        state['error'] = ev.get('msg')


async def generate(base: str, payload: dict, state: dict) -> None:
    """异步发起生成请求，流式消费 NDJSON 事件。"""
    # 生图步骤可能数分钟无事件，read 不设超时；连接/写入给 30s
    timeout = httpx.Timeout(30.0, read=None)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream('POST', f'{base}/generate', json=payload) as r:
            if r.status_code != 200:
                body = (await r.aread()).decode('utf-8', 'replace')[:500]
                print('❌ 接口返回 {}：{}'.format(r.status_code, body))
                state['error'] = f'HTTP {r.status_code}'
                return
            async for line in r.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                try:
                    _handle_event(json.loads(line), state)
                except json.JSONDecodeError:
                    continue


async def main() -> None:
    args = _parse_args()
    image_urls = [u.strip() for u in args.image_urls if u and u.strip()]
    if not image_urls:
        print('❌ 至少需要一个 --image-url'); sys.exit(2)
    if not os.getenv('FOTOR_ECOMMERCE_SUITE_API'):
        print('❌ 未配置 FOTOR_ECOMMERCE_SUITE_API（FotorClient 生图 apikey）。请在与 skills 同级目录的 .env 中'
              '设置该变量后重试，预期路径：{}'.format(_ENV_PATH)); sys.exit(2)
    if not args.api_key:
        print('❌ 缺少生图 apikey：请设置环境变量 FOTOR_ECOMMERCE_SUITE_API 或传 --api_key'); sys.exit(2)

    base = args.api.rstrip('/')
    scenes = None
    if args.scenes is not None:
        scenes = [s.strip() for s in args.scenes.split(',') if s.strip()] or None

    # 只把【显式传入】的参数放进请求体；未传的不发送，交由服务端处理（不在客户端写死默认值）。
    payload: dict = {'image_urls': image_urls}
    if scenes is not None:
        payload['scenes'] = scenes
    if args.num is not None:
        payload['num'] = max(1, min(args.num, 8))
    if args.platform is not None:
        payload['platform'] = args.platform
    if args.country is not None:
        payload['country'] = args.country
    if args.language is not None:        # 传 "" 也算显式传入（=整组不加文字）
        payload['language'] = args.language
    if args.aspect_ratio is not None:
        payload['aspect_ratio'] = args.aspect_ratio
    if args.key_info is not None:
        payload['sell_points'] = args.key_info
    # 品牌信息（均可选）：传了才进请求体
    if args.brand_info is not None:
        payload['brand_info'] = args.brand_info
    if args.brand_logo is not None:
        payload['brand_logo'] = args.brand_logo
    # FotorClient 生图 apikey（来自环境变量 FOTOR_ECOMMERCE_SUITE_API / --api_key）随请求传给后端，后端不写死
    payload['fotor_api_key'] = args.api_key

    brand_on = any(getattr(args, k) for k in ('brand_info', 'brand_logo'))

    def _shown(v):
        return '未指定' if v is None else (v or '无')

    print('🛍️ 开始生成电商套图')
    print('   参考图 {} 张 | 模式 {} | 平台 {} | 国家 {} | 语言 {} | 比例 {} | 关键信息 {} | 品牌 {}'.format(
        len(image_urls), '自动推荐' if scenes is None else '自定义',
        _shown(args.platform), _shown(args.country), _shown(args.language),
        _shown(args.aspect_ratio),
        '有' if (args.key_info or '').strip() else '无',
        '有' if brand_on else '无'))
    print('-' * 60)

    state: dict = {'final': None, 'error': None}
    try:
        await generate(base, payload, state)
    except httpx.ConnectError:
        print('❌ 无法连接接口 {}：请确认服务已启动后重试。'.format(base)); sys.exit(3)
    except httpx.HTTPError as e:
        print('❌ 调用接口失败: {}'.format(e)); sys.exit(1)

    print('-' * 60)
    if state['error']:
        sys.exit(1)
    final = state['final']
    if not final or not final.get('commerceStyles'):
        print('❌ 未产出结构化套图结果'); sys.exit(1)

    style = final['commerceStyles'][0]
    print('🎉 完成！商品: {}'.format(style.get('productName', '')))
    result = {
        'productName': style.get('productName', ''),
        'productDescription': style.get('productDescription', ''),
        'items': [
            {'name': it.get('name'), 'aspectRatio': it.get('aspectRatio'),
             'imageUrls': it.get('imageUrls')}
            for it in style.get('items', [])
        ],
    }
    print('===RESULT_JSON===')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
