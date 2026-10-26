#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OAS 日常配置記錄 生成器

用法:
    python3 build.py --version v1 --date 2026-10-26

輸入:
    <version>/daily-template.json   pair.html 的 DAILY 模板（按鈕任務的意圖態）
    <version>/raw/qingcui.json      清脆真機 config 原文
    <version>/raw/suolong.json      索隆真機 config 原文

輸出（每台獨立）:
    <version>/qingcui/daily.json    該台的日常唯一真源
    <version>/qingcui/daily.html    該台的報告
    <version>/qingcui/drift.json    該台 日常 vs 真機 差異
    <version>/qingcui/deployed.json 該台真機實測快照

規則:
    1. 按鈕任務（DAILY 模板裡有的）→ 取模板值（還原按鈕寫回什麼，日常就是什麼）
    2. 其餘任務 → 取真機值（還原按鈕不碰它們）
    3. next_run 一律抹掉（滾動值，每天不同）
"""
import json, os, sys, html, argparse

MACHINES = {
    'qingcui': {'name': '清脆', 'vm': 'VM106', 'ip': '192.168.250.241',
                'phone': 'OnePlus5', 'serial': '823c342e'},
    'suolong': {'name': '索隆', 'vm': 'VM103', 'ip': '192.168.250.240',
                'phone': 'K30U', 'serial': 'jzypu4mbbum79lyh'},
}
OAS = {
    'head': 'cc65d55dae353c810b1733dd59d692bff514fc0f',
    'patches': {
        'tasks/BondlingFairyland/battle.py': 'C86A1F9884BECF0A',
        'module/config/config_manual.py':    '0EC24F60508A7E30',
        'module/device/method/droidcast.py': '099B0B80B0F7A3DA',
        'tasks/ActivityShikigami/assets.py': '0FDD42A0B3524088',
    }
}
ROLL = '<滚動，不記錄>'

TASK_CN = {
    'ryou_toppa': '寮突破', 'orochi': '御魂', 'bondling_fairyland': '契靈',
    'realm_raid': '個人突破', 'goryou_realm': '御靈', 'demon_encounter': '逢魔',
    'area_boss': '地域鬼王', 'daily_trifles': '每日瑣事', 'gold_youkai': '金幣妖怪',
    'talisman_pass': '符咒通行', 'restart': '重啟', 'hunt': '狩獵', 'duel': '鬥技',
    'wanted_quests': '懸賞', 'exploration': '探索', 'evo_zone': '進化',
    'souls_tidy': '御魂整理', 'script': '腳本全局', 'global_game': '全局遊戲',
    'rich_man': '大富翁', 'kekkai_activation': '結界卡', 'kekkai_utilize': '結界寄養',
    'mystery_shop': '神秘商店', 'guild_banquet': '寮宴', 'true_orochi': '真御魂',
}

def load_json(p):
    raw = open(p, 'rb').read()
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'latin-1'):
        try:
            return json.loads(raw.decode(enc))
        except Exception:
            continue
    raise RuntimeError('cannot parse %s' % p)

def snake(n):
    return ''.join(('_' if ch.isupper() and i else '') + ch.lower() for i, ch in enumerate(n))

def build_daily(cfg, real, tpl_all):
    """把真機 config + 模板 合成該台的日常"""
    tpl = tpl_all.get(cfg, {})
    tpl_by_seg = {snake(t): t for t in tpl}
    out = {}
    for seg, data in real.items():
        if not isinstance(data, dict):
            out[seg] = data
            continue
        d = json.loads(json.dumps(data))
        if seg in tpl_by_seg:
            spec = tpl[tpl_by_seg[seg]]
            d.setdefault('scheduler', {})
            for k, v in spec.items():
                if k == 'slot':
                    continue
                if k == 'enable':
                    d['scheduler']['enable'] = v
                elif k == 'next_run':
                    d['scheduler']['next_run'] = v
                elif isinstance(v, dict):
                    d.setdefault(k, {})
                    for f, fv in v.items():
                        d[k][f] = fv
        else:
            if 'scheduler' in d and 'next_run' in d['scheduler']:
                d['scheduler']['next_run'] = ROLL
        out[seg] = d
    return out

def drift_of(daily, real):
    rows = []
    for seg, want in daily.items():
        if not isinstance(want, dict):
            continue
        got = real.get(seg, {})
        if not isinstance(got, dict):
            continue
        ws, gs = want.get('scheduler') or {}, got.get('scheduler') or {}
        for f in ('enable', 'server_update'):
            if f in ws and ws[f] != gs.get(f):
                rows.append({'task': seg, 'field': 'scheduler.' + f,
                             'should_be': ws[f], 'actually': gs.get(f)})
        for grp, fields in want.items():
            if grp == 'scheduler' or not isinstance(fields, dict):
                continue
            ggrp = got.get(grp) or {}
            for f, v in fields.items():
                if ggrp.get(f) != v:
                    rows.append({'task': seg, 'field': '%s.%s' % (grp, f),
                                 'should_be': v, 'actually': ggrp.get(f)})
    return rows

# ---------------- HTML ----------------
def esc(x):
    return html.escape(str(x))

def vcell(v):
    if v is True:
        return '<span class="t">開</span>'
    if v is False:
        return '<span class="f">關</span>'
    s = str(v)
    if s == ROLL:
        return '<span class="dim">滾動</span>'
    if s in ('-1,-1', '', 'None', 'null'):
        return '<span class="dim">%s</span>' % esc(s or '空')
    return esc(s)

CSS = """
:root{--bg:#0f1115;--card:#171a21;--line:#252a34;--tx:#e6e9ef;--dim:#8b93a7;
--on:#3fb950;--off:#6e7681;--warn:#d29922;--bad:#f85149;--acc:#58a6ff}
*{box-sizing:border-box}
body{margin:0;padding:26px;background:var(--bg);color:var(--tx);
font:14px/1.65 -apple-system,"Segoe UI","PingFang TC","Microsoft JhengHei",sans-serif}
h1{font-size:23px;margin:0 0 4px}
h1 .v{color:var(--acc)}
h2{font-size:16px;margin:28px 0 10px;padding-left:9px;border-left:3px solid var(--acc)}
.sub{color:var(--dim);font-size:12.5px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:16px;margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:7px 9px;color:var(--dim);font-weight:600;
border-bottom:1px solid var(--line);font-size:12px;white-space:nowrap}
td{padding:7px 9px;border-bottom:1px solid #1d2129;vertical-align:top}
tr:hover td{background:#1c2028}
code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;color:#9aa4b8}
.tn{white-space:nowrap;font-weight:600}
.t{color:var(--on);font-weight:700}.f{color:var(--off)}
.dim{color:var(--dim)}
.badge{display:inline-block;font-size:10px;padding:1px 6px;border-radius:4px;
margin-left:5px;vertical-align:middle;font-weight:600;background:#1f3a5f;color:#79c0ff}
.kv{display:inline-block;background:#12151b;border:1px solid #222831;border-radius:5px;
padding:1px 6px;margin:2px 3px 2px 0;font-size:11.5px}
.kv b{color:var(--tx)}
.rowdiff td:first-child{border-left:3px solid var(--warn)}
.ext{font-size:11.5px;color:#b9c0cf}
.warn{color:var(--warn);font-size:12.5px;margin-top:10px}
.ok{color:var(--on);font-size:13px}
.want{color:#79c0ff;font-weight:600}.got{color:var(--bad);font-weight:600}
.mono{font-family:ui-monospace,monospace;font-size:12px;color:#9aa4b8}
.note{background:#12151b;border-left:3px solid var(--acc);padding:11px 13px;
border-radius:0 6px 6px 0;font-size:12.5px;color:#b9c0cf;line-height:1.8}
.stat{display:inline-block;margin-right:22px;font-size:13px;color:var(--dim)}
.stat b{color:var(--tx);font-size:17px;font-weight:700}
"""

def render(cfg, daily, meta, drift, version, date, captured):
    m = MACHINES[cfg]
    segs = sorted(daily)
    btn_segs = set(snake(t) for t in meta['button_tasks'])

    en = [s for s in segs if isinstance(daily[s], dict)
          and (daily[s].get('scheduler') or {}).get('enable') is True]

    rows = []
    cnt_task = 0
    for seg in segs:
        t = daily[seg]
        if not isinstance(t, dict):
            continue
        cnt_task += 1
        sch = t.get('scheduler') or {}
        fields = set()
        for grp, fs in t.items():
            if grp == 'scheduler' or not isinstance(fs, dict):
                continue
            for f in fs:
                fields.add('%s.%s' % (grp, f))
        parts = []
        for fp in sorted(fields):
            grp, f = fp.split('.', 1)
            val = (t.get(grp) or {}).get(f)
            parts.append('<span class="kv">%s=<b>%s</b></span>' % (esc(f), vcell(val)))
        badge = '<span class="badge">按鈕</span>' if seg in btn_segs else ''
        cn = TASK_CN.get(seg)
        label = ('%s<br><code>%s</code>' % (esc(cn), esc(seg))) if cn else '<code>%s</code>' % esc(seg)
        rows.append(
            '<tr><td class="tn">%s%s</td><td>%s</td><td>%s</td><td class="dim">%s</td>'
            '<td class="ext">%s</td></tr>' % (
                label, badge, vcell(sch.get('enable')),
                vcell(sch.get('server_update')) or '<span class="dim">—</span>',
                vcell(sch.get('priority')) or '—',
                ' '.join(parts) or '<span class="dim">—</span>'))

    if drift:
        drows = ''.join(
            '<tr><td>%s</td><td><code>%s</code></td><td class="want">%s</td>'
            '<td class="got">%s</td></tr>' % (
                esc(TASK_CN.get(d['task'], d['task'])), esc(d['field']),
                esc(d['should_be']), esc(d['actually'])) for d in drift)
        drift_html = ('<table><thead><tr><th>任務</th><th>欄位</th>'
                      '<th>應該是（日常）</th><th>實際是（真機）</th></tr></thead>'
                      '<tbody>%s</tbody></table>'
                      '<p class="warn">以上為抓取時真機偏離日常的項目。'
                      '按鈕任務的漂移屬預期（按「還原」後恢復）。</p>' % drows)
    else:
        drift_html = '<p class="ok">✓ 無差異，真機與日常完全一致</p>'

    patches = ''.join('<tr><td><code>%s</code></td><td><code>%s</code></td></tr>' % (esc(k), esc(v))
                      for k, v in OAS['patches'].items())

    return """<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OAS 日常 · %(name)s · %(version)s</title><style>%(css)s</style></head><body>

<h1>OAS 日常配置 · <span style="color:var(--acc)">%(name)s</span> <span class="v">%(version)s</span></h1>
<div class="sub">記錄日期 %(date)s　·　抓取 %(cap)s　·　%(vm)s · %(ip)s · %(phone)s · <code>%(serial)s</code></div>

<div class="card"><div class="note">
本檔只記 <b>%(name)s 這一台</b>。取值規則：<br>
① 標 <span class="badge">按鈕</span> 的任務 → 取 <code>pair.html</code> 的 DAILY 模板值（還原按鈕寫回什麼，日常就是什麼）<br>
② 其餘任務 → 取真機值（還原按鈕不碰它們，真機即日常）<br>
③ <b>next_run 一律不記錄</b> —— 滾動值，每天不同
</div></div>

<h2>一、摘要</h2>
<div class="card">
<span class="stat">任務 <b>%(cnt_task)d</b></span>
<span class="stat">啟用 <b>%(enabled)d</b></span>
<span class="stat">停用 <b>%(disabled)d</b></span>
<p class="note" style="margin-top:12px">啟用中的任務：%(enlist)s<br><span class="dim">（另有 %(extra)d 個非任務鍵：config_name / running_task，不列入）</span></p>
</div>

<h2>二、全量任務（%(cnt_task)d 個）</h2>
<div class="card" id="alltasks">
<table><thead><tr><th>任務</th><th>啟用</th><th>時刻</th><th>優先</th><th>關鍵參數</th></tr></thead>
<tbody>%(rows)s</tbody></table></div>

<h2>三、抓取時偏離（drift）</h2>
<div class="card">%(drift)s</div>

<h2>四、版本資訊</h2>
<div class="card">
<p class="mono">OAS HEAD　%(head)s</p>
<table style="margin-top:8px"><thead><tr><th>本地補丁</th><th>sha256（前16）</th></tr></thead>
<tbody>%(patches)s</tbody></table></div>

<p class="dim" style="margin-top:26px;font-size:11.5px;text-align:center">
OAS 日常配置 · %(name)s · %(version)s · 由 daily.json 渲染生成
</p></body></html>""" % {
        'name': m['name'], 'version': version, 'date': date, 'cap': captured,
        'vm': m['vm'], 'ip': m['ip'], 'phone': m['phone'], 'serial': m['serial'],
        'css': CSS, 'total': len(segs), 'cnt_task': cnt_task,
        'enabled': len(en), 'disabled': cnt_task - len(en),
        'enlist': esc('、'.join(TASK_CN.get(x, x) for x in en)) or '<span class="dim">無</span>',
        'rows': ''.join(rows), 'drift': drift_html, 'head': esc(OAS['head']),
        'patches': patches, 'extra': len(segs) - cnt_task,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', required=True)
    ap.add_argument('--date', required=True)
    ap.add_argument('--captured', default='')
    a = ap.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    vdir = os.path.join(base, a.version)
    tpl_all = load_json(os.path.join(vdir, 'daily-template.json'))
    captured = a.captured or (a.date + 'T16:16:00+08:00')

    for cfg in MACHINES:
        raw = load_json(os.path.join(vdir, 'raw', '%s.json' % cfg))
        daily = build_daily(cfg, raw, tpl_all)
        drift = drift_of(daily, raw)

        outd = os.path.join(vdir, cfg)
        os.makedirs(outd, exist_ok=True)

        # 該台的 meta
        bt = sorted(tpl_all.get(cfg, {}))
        meta = {
            'version': a.version, 'date': a.date, 'captured_at': captured,
            'machine': MACHINES[cfg], 'oas': OAS,
            'button_tasks': bt,
            'source_of_truth': {
                'button_tasks': 'pair.html 的 DAILY 模板',
                'other_tasks': '真機 config（還原按鈕不碰）',
                'next_run': '不記錄（滾動值）',
            },
            'summary': {
                'total_task_segments': len(daily),
                'enabled': sum(1 for s, v in daily.items() if isinstance(v, dict)
                               and (v.get('scheduler') or {}).get('enable') is True),
            },
        }
        open(os.path.join(outd, 'meta.json'), 'w', encoding='utf-8').write(
            json.dumps(meta, ensure_ascii=False, indent=2))
        open(os.path.join(outd, 'daily.json'), 'w', encoding='utf-8').write(
            json.dumps(daily, ensure_ascii=False, indent=2))
        open(os.path.join(outd, 'drift.json'), 'w', encoding='utf-8').write(
            json.dumps({'checked_at': captured, 'machine': cfg, 'diffs': drift},
                       ensure_ascii=False, indent=2))
        open(os.path.join(outd, 'deployed.json'), 'w', encoding='utf-8').write(
            json.dumps({seg: (v.get('scheduler') or {}) for seg, v in raw.items()
                        if isinstance(v, dict)}, ensure_ascii=False, indent=2))
        open(os.path.join(outd, 'daily.html'), 'w', encoding='utf-8').write(
            render(cfg, daily, meta, drift, a.version, a.date, captured))

        print('%-8s 任務段=%d  啟用=%d  drift=%d  -> %s/%s/' % (
            MACHINES[cfg]['name'], len(daily), meta['summary']['enabled'],
            len(drift), a.version, cfg))
        for d in drift:
            print('         DRIFT %s %s  應該=%r 實際=%r' % (
                d['task'], d['field'], d['should_be'], d['actually']))

if __name__ == '__main__':
    main()
