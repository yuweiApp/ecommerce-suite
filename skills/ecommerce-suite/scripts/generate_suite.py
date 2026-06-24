import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# Windows 控制台默认 GBK，中文/德语等非 GBK 字符直接 print 会 UnicodeEncodeError
sys.stdout.reconfigure(encoding='utf-8')

# 配置（FOTOR_ECOMMERCE_SUITE_API 等）从【与 skills 同级】目录读取——即本技能 SKILL.md 目录
# （skills/ecommerce-suite）的【上 2 级】、本脚本所在 scripts/ 的上 3 级。按顺序加载该目录下的
# .env（基础配置，可选）与 .env.local（本地私有覆盖，FOTOR_ECOMMERCE_SUITE_API 写在这里）：
# 二者都【只加载、不创建】（文件不存在就跳过）；override=True 表示文件里的值会【覆盖】当前进程
# 已有的同名环境变量，且后加载的 .env.local 覆盖 .env。必须在读取环境变量之前完成加载。
_CONFIG_DIR = Path(__file__).resolve().parents[1].parents[1]  # SKILL.md 目录的上 2 级
_ENV_LOCAL_PATH = _CONFIG_DIR / '.env.local'  # FOTOR_ECOMMERCE_SUITE_API 期望写入/读取的文件
for _env_path in (_CONFIG_DIR / '.env', _ENV_LOCAL_PATH):
    if _env_path.is_file():
        try:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=_env_path, override=True)
        except ImportError:
            break  # 未安装 python-dotenv 时，退化为仅使用进程已有的环境变量


def _read_skill_version() -> str:
    """从同技能的 SKILL.md frontmatter 里读取 version；读不到返回 ''。"""
    skill_md = Path(__file__).resolve().parents[1] / 'SKILL.md'  # scripts/ 的上一级
    try:
        lines = skill_md.read_text(encoding='utf-8').splitlines()
    except OSError:
        return ''
    if not lines or lines[0].strip() != '---':
        return ''
    for line in lines[1:]:
        if line.strip() == '---':
            break
        if line.startswith('version:'):
            return line.split(':', 1)[1].strip().strip('"\'')
    return ''


def _parse_args() -> argparse.Namespace:
    # 内容参数均【不设默认值】：应由调用方（agent，按 SKILL.md 的引导与推荐）显式传入；
    # 未传的参数不会进入请求体，由服务端默认值或自动推荐模式处理。
    ap = argparse.ArgumentParser(description='电商套图生成客户端')
    ap.add_argument('--image-url', action='append', default=[], dest='image_urls', required=True,
                    help='商品参考图 URL 或 data:image/... Base64（可重复多次）')
    ap.add_argument('--scenes', help='自定义套图类型，逗号分隔；不传或传空=自动推荐')
    ap.add_argument('--num', type=int, help='生成图片张数（1-8）')
    ap.add_argument('--platform', help='目标平台（如 Amazon）')
    ap.add_argument('--country', help='销售国家（影响模特地域表达，如 American）')
    ap.add_argument('--language', help='图内文案语言 i18n 代码（如 en_US）；传 "" 表示整组不加文字')
    ap.add_argument('--aspect-ratio', dest='aspect_ratio', help='图片比例（如 1:1）')
    ap.add_argument('--image-type', dest='image_type', help='图片类型（通常为 listing / aplus）')
    ap.add_argument('--key-info', dest='key_info',
                    help='商品关键信息（可选）：产品名称/核心卖点/目标受众/使用场景，自由文本')
    ap.add_argument('--brand-info', dest='brand_info',
                    help='用户用自然语言描述的品牌信息（配色/字体/调性/氛围等），自由文本')
    ap.add_argument('--brand-logo', dest='brand_logo',
                    help='品牌 logo 的完整图片 URL 或 data:image/... Base64；用于品牌故事类场景')
    ap.add_argument('--api', default='https://api-b-sandbox.fotor.com',
                    help='Fotor Business OpenAPI Base URL')
    ap.add_argument('--api-key', '--api_key', dest='api_key', default=os.getenv('FOTOR_ECOMMERCE_SUITE_API'),
                    help='Fotor Business OpenAPI apikey（默认取环境变量 FOTOR_ECOMMERCE_SUITE_API）')
    ap.add_argument('--poll-interval', type=float, default=3.0, help='任务轮询间隔秒数')
    ap.add_argument('--timeout', type=float, default=600.0, help='单任务等待超时秒数')
    return ap.parse_args()


def _api_headers(api_key: str) -> dict[str, str]:
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }


def _parse_json_response(resp: httpx.Response) -> dict[str, Any]:
    try:
        body = resp.json()
    except json.JSONDecodeError:
        text = resp.text[:500]
        raise RuntimeError(f'接口返回非 JSON 响应：{text}') from None
    if not isinstance(body, dict):
        raise RuntimeError('接口返回格式异常：Body 不是 JSON object')
    return body


def _ensure_success_body(body: dict[str, Any]) -> None:
    code = body.get('code')
    if code not in (None, '000', 0):
        msg = body.get('msg') or body.get('message') or 'unknown error'
        raise RuntimeError(f'接口返回错误 code={code}: {msg}')


def _extract_credit_balance(data: Any) -> float | None:
    if isinstance(data, (int, float)):
        return float(data)
    if not isinstance(data, dict):
        return None

    keys = (
        'credits',
        'credit',
        'balance',
        'availableCredits',
        'available_credits',
        'remainingCredits',
        'remaining_credits',
        'totalCredits',
        'total_credits',
    )
    for key in keys:
        value = data.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return None


async def _query_credits(client: httpx.AsyncClient, base: str, api_key: str) -> dict[str, Any]:
    url = f'{base}/v1/credits'
    resp = await client.get(url, headers=_api_headers(api_key))
    if resp.status_code != 200:
        raise RuntimeError(f'查询积分失败 HTTP {resp.status_code}: {resp.text[:500]}')

    body = _parse_json_response(resp)
    _ensure_success_body(body)
    return body


async def _check_credits(
    client: httpx.AsyncClient,
    base: str,
    api_key: str,
    expected_cost: int,
) -> None:
    body = await _query_credits(client, base, api_key)
    data = body.get('data')
    balance = _extract_credit_balance(data)
    if balance is None:
        print('ℹ️ 已查询积分，但未识别余额字段，响应 data={}'.format(
            json.dumps(data, ensure_ascii=False)[:500]))
        return

    shown_balance = int(balance) if balance.is_integer() else balance
    print('💳 当前积分余额 {} | 本次预计消耗 {}'.format(shown_balance, expected_cost))
    if balance < expected_cost:
        raise RuntimeError(f'积分不足：余额 {shown_balance} < 本次预计消耗 {expected_cost}')


async def _submit_task(client: httpx.AsyncClient, base: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f'{base}/v1/aiart/ecommercelistingset'
    resp = await client.post(url, headers=_api_headers(api_key), json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f'提交任务失败 HTTP {resp.status_code}: {resp.text[:500]}')

    body = _parse_json_response(resp)
    _ensure_success_body(body)
    data = body.get('data') or {}
    if not isinstance(data, dict):
        raise RuntimeError('提交任务响应格式异常：data 不是 object')
    task_id = data.get('taskId') or data.get('task_id')
    if not task_id:
        raise RuntimeError(f'提交任务响应缺少 taskId: {json.dumps(body, ensure_ascii=False)[:500]}')
    return data


async def _query_task(client: httpx.AsyncClient, base: str, api_key: str, task_id: str) -> dict[str, Any]:
    url = f'{base}/v1/aiart/tasks/{task_id}'
    resp = await client.get(url, headers=_api_headers(api_key))
    if resp.status_code != 200:
        raise RuntimeError(f'查询任务失败 HTTP {resp.status_code}: {resp.text[:500]}')

    body = _parse_json_response(resp)
    _ensure_success_body(body)
    data = body.get('data') or {}
    if not isinstance(data, dict):
        raise RuntimeError('查询任务响应格式异常：data 不是 object')
    return data


async def _wait_for_result(
    client: httpx.AsyncClient,
    base: str,
    api_key: str,
    task_id: str,
    poll_interval: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    started = time.monotonic()
    next_progress_at = 0.0

    while True:
        elapsed = time.monotonic() - started
        if elapsed > timeout_seconds:
            raise RuntimeError(f'任务等待超时（约 {int(timeout_seconds)} 秒），taskId={task_id}')

        data = await _query_task(client, base, api_key, task_id)
        status = data.get('status')
        if status in (1, '1'):
            return data
        if status in (2, '2'):
            msg = data.get('msg') or 'task failed'
            raise RuntimeError(f'任务失败：{msg}')
        if status not in (0, '0'):
            raise RuntimeError(f'未知任务状态 status={status}: {json.dumps(data, ensure_ascii=False)[:500]}')

        if elapsed >= next_progress_at:
            print('… 任务处理中，已等待约 {} 秒'.format(int(elapsed)))
            next_progress_at = elapsed + 15
        await asyncio.sleep(max(1.0, poll_interval))


def _build_payload(args: argparse.Namespace, image_urls: list[str], skill_version: str) -> tuple[dict[str, Any], list[str] | None]:
    scenes = None
    if args.scenes is not None:
        scenes = [s.strip() for s in args.scenes.split(',') if s.strip()] or None

    payload: dict[str, Any] = {'image_urls': image_urls}
    if scenes is not None:
        payload['scenes'] = scenes
    if args.num is not None:
        payload['num'] = args.num
    if args.platform is not None:
        payload['platform'] = args.platform
    if args.country is not None:
        payload['country'] = args.country
    if args.language is not None:
        payload['language'] = args.language
    if args.aspect_ratio is not None:
        payload['aspect_ratio'] = args.aspect_ratio
    if args.image_type is not None:
        payload['image_type'] = args.image_type
    if args.key_info is not None:
        payload['sell_points'] = args.key_info
    if args.brand_info is not None:
        payload['brand_info'] = args.brand_info
    if args.brand_logo is not None:
        payload['brand_logo'] = args.brand_logo
    if skill_version:
        payload['skill_version'] = skill_version
    return payload, scenes


def _shown(v: str | None) -> str:
    return '未指定' if v is None else (v or '无')


def _iter_result_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    result = data.get('result')
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    return []


def _successful_result_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    items = _iter_result_items(data)
    return [item for item in items if item.get('success') is True and item.get('url')]


def _fallback_result_urls(data: dict[str, Any]) -> list[str]:
    """兼容旧响应：result 曾经可能是 URL 列表；新版响应以对象数组为准。"""
    result = data.get('result')
    if isinstance(result, list):
        return [item for item in result if isinstance(item, str) and item]
    return []


def _print_result_summary(data: dict[str, Any]) -> None:
    items = _iter_result_items(data)
    if not items:
        legacy_urls = _fallback_result_urls(data)
        if legacy_urls:
            print('📷 成图 URL：')
            for idx, url in enumerate(legacy_urls, 1):
                print('   {}. {}'.format(idx, url))
        elif data.get('resultUrl'):
            print('📷 首张成图 URL：{}'.format(data['resultUrl']))
        return

    print('📷 分场景结果：')
    for item in items:
        name = item.get('name') or '未命名场景'
        if item.get('success') is True and item.get('url'):
            print('   ✅ {}: {}'.format(name, item['url']))
        else:
            print('   ⚠️ {}: {}'.format(name, item.get('error') or '生成失败'))


async def main() -> None:
    args = _parse_args()
    image_urls = [u.strip() for u in args.image_urls if u and u.strip()]
    if not image_urls:
        print('❌ 至少需要一个 --image-url')
        sys.exit(2)
    if args.num is not None and not 1 <= args.num <= 8:
        print('❌ --num must be between 1 and 8')
        sys.exit(2)
    if not args.api_key:
        print('❌ 未配置 FOTOR_ECOMMERCE_SUITE_API。请在与 skills 同级目录的 .env.local 中设置该变量后重试，'
              '预期路径：{}'.format(_ENV_LOCAL_PATH))
        sys.exit(2)

    base = args.api.rstrip('/')
    skill_version = _read_skill_version()
    payload, scenes = _build_payload(args, image_urls, skill_version)
    brand_on = any(getattr(args, k) for k in ('brand_info', 'brand_logo'))

    print('🛍️ 开始生成电商套图（技能版本 {}）'.format(skill_version or '未知'))
    print('   参考图 {} 张 | 模式 {} | 平台 {} | 国家 {} | 语言 {} | 比例 {} | 类型 {} | 关键信息 {} | 品牌 {}'.format(
        len(image_urls), '自动推荐' if scenes is None else '自定义',
        _shown(args.platform), _shown(args.country), _shown(args.language),
        _shown(args.aspect_ratio), _shown(args.image_type),
        '有' if (args.key_info or '').strip() else '无',
        '有' if brand_on else '无'))
    print('-' * 60)

    try:
        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            expected_num = int(payload.get('num') or 4)
            expected_cost = expected_num * 8
            await _check_credits(client, base, args.api_key, expected_cost)
            submitted = await _submit_task(client, base, args.api_key, payload)
            task_id = submitted.get('taskId') or submitted.get('task_id')
            credits = submitted.get('creditsIncrement')
            print('✅ 任务已提交 taskId={} | 预估消耗积分 {}'.format(task_id, _shown(str(credits) if credits is not None else None)))
            data = await _wait_for_result(client, base, args.api_key, task_id, args.poll_interval, args.timeout)
    except httpx.ConnectError:
        print('❌ 无法连接接口 {}：请确认网络和 API 地址后重试。'.format(base))
        sys.exit(3)
    except httpx.HTTPError as e:
        print('❌ 调用接口失败: {}'.format(e))
        sys.exit(1)
    except RuntimeError as e:
        print('❌ 出错: {}'.format(e))
        sys.exit(1)

    result_url = data.get('resultUrl')
    success_items = _successful_result_items(data)
    legacy_urls = _fallback_result_urls(data)
    if not result_url and not success_items and not legacy_urls:
        print('❌ 任务完成但未返回成图 URL')
        sys.exit(1)

    print('-' * 60)
    print('🎉 完成！')
    _print_result_summary(data)
    print(json.dumps({'code': '000', 'msg': 'success', 'data': data}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
