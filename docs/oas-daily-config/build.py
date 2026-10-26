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

輸出:
    <version>/qingcui-daily.json    清脆日常（獨立一份）
    <version>/suolong-daily.json    索隆日常（獨立一份）
    <version>/daily.html            單一報告，左右並列對比兩台（淺色）

規則:
    1. 按鈕任務（DAILY 模板裡有的）→ 取模板值
    2. 其餘任務 → 取真機值
    3. next_run 一律抹掉（滾動值）
"""
import json, os, html, argparse

MACHINES = {
    'qingcui': {'name': '清脆', 'vm': 'VM106', 'ip': '192.168.250.241',
                'phone': 'OnePlus5', 'serial': '823c342e'},
    'suolong': {'name': '索隆', 'vm': 'VM103', 'ip': '192.168.250.240',
                'phone': 'K30U', 'serial': 'jzypu4mbbum79lyh'},
}
ORDER = ['qingcui', 'suolong']
OAS = {
    'head': 'cc65d55dae353c810b1733dd59d692bff514fc0f',
    'patches': {
        'tasks/BondlingFairyland/battle.py': 'C86A1F9884BECF0A',
        'module/config/config_manual.py':    '0EC24F60508A7E30',
        'module/device/method/droidcast.py': '099B0B80B0F7A3DA',
        'tasks/ActivityShikigami/assets.py': '0FDD42A0B3524088',
    }
}
ROLL = '<滾動，不記錄>'

TASK_CN = {
    'abyss_shadows': '狭间暗域', 'activity_shikigami': '当期爬塔', 'area_boss': '地域鬼王',
    'auto_checkin_big_god': '大神签到', 'bondling_fairyland': '契灵之境',
    'budokai_tournament': '武道大会', 'collective_missions': '集体任务',
    'daily_trifles': '每日琐事', 'delegation': '式神委派', 'demon_encounter': '逢魔之时',
    'demon_retreat': '首领退治', 'dokan': '道馆', 'duel': '斗技',
    'dye_trials': '灵染试炼', 'eternity_sea': '永生之海', 'evo_zone': '觉醒副本',
    'experience_youkai': '经验妖怪', 'exploration': '探索', 'fallen_sun': '日轮之陨',
    'find_jade': '寻找协作任务', 'float_parade': '花车巡游', 'frog_boss': '对弈竞猜',
    'global_game': '全局配置', 'gold_youkai': '金币妖怪', 'goryou_realm': '御灵之境',
    'guild_activity_monitor': '寮活动监控', 'guild_banquet': '寮宴会',
    'hero_test': '英杰试炼', 'hunt': '狩猎战', 'hyakkiyakou': '百鬼夜行',
    'kekkai_activation': '结界挂卡', 'kekkai_utilize': '结界蹭卡',
    'kitty_shop': '猫咪铺子', 'memory_scrolls': '绘卷', 'meta_demon': '超鬼王',
    'mystery_shop': '神秘商店', 'nian': '年兽', 'orochi': '八岐大蛇',
    'orochi_moans': '御魂·悲鸣（占位段）',
    'other_world_twilight': '彼世逢魔', 'pets': '小猫咪', 'quiz': '智力竞赛',
    'realm_raid': '个人突破', 'restart': '重启', 'rich_man': '大富翁',
    'ryou_toppa': '寮突破', 'script': '脚本', 'secret': '秘闻副本',
    'six_realms': '六道之门', 'sougenbi': '业原火', 'souls_tidy': '御魂整理',
    'tako': '石距', 'talisman_pass': '花合战', 'true_orochi': '真八岐大蛇',
    'wanted_quests': '悬赏封印', 'weekly_trifles': '每周琐事',
}
# 空佔位段：無配置、不在 script_menu，只留 scheduler
PLACEHOLDER_SEGS = {'orochi_moans'}

# 參數欄位中文標籤（取自 OAS 官方 i18n，僅列常用）
FIELD_CN = {
    'user_status': '身份', 'limit_count': '次數', 'limit_time': '限時',
    'layer': '層', 'layer_limit': '層限', 'number_attack': '攻打次數',
    'number_base': '額外基礎', 'exit_four': '打九退四',
    'order_attack': '攻打順序', 'three_refresh': '三次刷新',
    'when_attack_fail': '失敗處理', 'skip_difficult': '跳過困難',
    'ryou_access': '突破權限', 'random_delay': '隨機延遲',
    'next_ryoutoppa_time': '下次時刻', 'soul_buff_enable': '御魂加成',
    'bondling_mode': '模式', 'bondling_stone_class': '式盤',
    'bondling_stone_enable': '用式盤', 'bondling_search_enable': '探查',
    'check_enable': '檢查契憶', 'limit_num': '契憶上限',
    'goryou_class': '類型', 'kirin_type': '麒麟類型',
    'kirin_group_team': '麒麟陣容', 'netherworld_group_team': '陰界陣容',
    'preset_enable': '切換預設', 'preset_group': '預設組',
    'preset_team': '預設隊', 'green_enable': '綠標',
    'green_mark': '綠標位置', 'green_mark_type': '綠標方式',
    'green_mark_name': '綠標式神', 'random_click_swipt_enable': '隨機點擊',
    'lock_team_enable': '鎖定隊伍', 'switch_soul_enable': '切換御魂',
    'exploration_level': '探索層數', 'explore_level': '探索層數',
    'choose_rarity': '稀有度', 'auto_rotate': '自動旋轉',
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


# ---------------- HTML（淺色） ----------------
def esc(x):
    return html.escape(str(x))


def vcell(v):
    if v is True:
        return '<span class="on">開</span>'
    if v is False:
        return '<span class="off">關</span>'
    s = str(v)
    if s == ROLL:
        return '<span class="dim">滾動</span>'
    if s in ('-1,-1', '', 'None', 'null'):
        return '<span class="dim">%s</span>' % esc(s or '空')
    return esc(s)


CSS = """
:root{
  --bg:#f5f6f8; --card:#fff; --line:#e2e5eb; --line2:#eef0f4;
  --tx:#1f2430; --tx2:#4a5568; --dim:#8a94a6;
  --on:#1a7f37; --onbg:#e8f5ec;
  --off:#8b95a5;
  --warnbg:#fff9e8; --bad:#b42318;
  --acc:#2563eb; --accbg:#eff4ff;
}
*{box-sizing:border-box}
body{margin:0;padding:26px 30px 40px;background:var(--bg);color:var(--tx);
font:14px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Microsoft JhengHei",sans-serif}
h1{font-size:23px;margin:0 0 6px;font-weight:700;letter-spacing:-.2px}
h1 .v{color:var(--acc);font-weight:600;font-size:18px;margin-left:8px;
  background:var(--accbg);padding:2px 10px;border-radius:6px}
h2{font-size:16px;margin:30px 0 12px;font-weight:700}
h2 .cnt{color:var(--dim);font-weight:400;font-size:12.5px;margin-left:8px}
.sub{color:var(--dim);font-size:12.5px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:15px 17px;margin-bottom:14px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 10px;color:var(--tx2);font-weight:600;background:#fafbfc;
border-bottom:1px solid var(--line);font-size:11.5px;white-space:nowrap}
td{padding:6px 10px;border-bottom:1px solid var(--line2);vertical-align:top;font-size:12.5px}
tbody tr:hover td{background:#fafbfc}
tr:last-child td{border-bottom:none}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11px;
color:#5a6577;background:#f2f4f7;padding:1px 5px;border-radius:3px}
.tn{white-space:nowrap;font-weight:600;font-size:12.5px}
.on{color:var(--on);font-weight:700;background:var(--onbg);padding:0 6px;border-radius:4px;font-size:12px}
.off{color:var(--off);font-size:12px}
.dim{color:var(--dim)}
.badge{display:inline-block;font-size:10px;padding:1px 6px;border-radius:10px;
margin-left:5px;vertical-align:middle;font-weight:600;background:var(--accbg);color:var(--acc)}
.badge.ph{background:#f1f3f6;color:#8a94a6}
.kv{display:inline-block;background:#f8f9fb;border:1px solid var(--line);
border-radius:4px;padding:0 5px;margin:1px 2px 1px 0;font-size:11px;color:var(--tx2);
white-space:nowrap}
.kv b{color:var(--tx);font-weight:600}
.ext{font-size:11px;line-height:2}
.note{background:var(--accbg);border-left:3px solid var(--acc);padding:11px 14px;
border-radius:0 7px 7px 0;font-size:12.5px;color:var(--tx2);line-height:1.85}
.ok{color:var(--on);font-size:13px;font-weight:600;margin:0}
.mono{font-family:ui-monospace,monospace;font-size:12px;color:var(--tx2)}

.split{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}
@media(max-width:1100px){.split{grid-template-columns:1fr}}
.pane{background:var(--card);border:1px solid var(--line);border-radius:10px;
overflow:hidden;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.pane-h{padding:12px 15px;border-bottom:1px solid var(--line);background:#fbfcfd}
.pane-h .nm{font-size:15px;font-weight:700}
.pane-h .nm .id{color:var(--dim);font-weight:400;font-size:11.5px;margin-left:6px}
.pane-h .meta{font-size:11.5px;color:var(--tx2);margin-top:6px;line-height:1.75}
.pane-h .meta b{font-size:12.5px}
.pane-b{padding:10px 12px 14px}
.pane-b table{font-size:12px}
.pane-b th{padding:6px 7px;font-size:11px}
.pane-b td{padding:5px 7px;font-size:12px}
.pane-b .kv{font-size:10.5px}
.drift-h{font-size:12px;font-weight:600;color:var(--tx2);margin:14px 0 7px;
padding-top:12px;border-top:1px dashed var(--line)}

/* ★ 摺叠任務列表 —— 表頭與每一行共用同一套格線，保證對齊 */
.list-h,details.task>summary{
  display:grid;
  grid-template-columns:12px minmax(96px,150px) 58px 1fr;
  align-items:center;gap:0 10px;
}
.list-h{padding:0 10px 7px;font-size:11px;color:var(--dim);font-weight:600;
border-bottom:1px solid var(--line);margin-bottom:2px}
.list-h .h-cn{padding-left:0}
.list-h .h-dot{display:block;width:12px;min-width:12px}
.list-h .h-time{text-align:right}
.list-h .h-quick{text-align:left}
.tasklist{max-height:none}
details.task{border-bottom:1px solid var(--line2);margin:0;padding:0}
details.task:last-child{border-bottom:none}
details.task>summary{
  padding:7px 10px;cursor:pointer;list-style:none;
  font-size:12.5px;border-radius:5px;transition:background .12s}
details.task>summary::-webkit-details-marker{display:none}
details.task>summary:hover{background:#f8f9fb}
.s-dot{width:9px;height:9px;border-radius:50%;display:inline-block;
justify-self:center}
details.task.on .s-dot{background:var(--on);box-shadow:0 0 0 3px rgba(26,127,55,.12)}
details.task.off .s-dot{background:#c9d0da}
.s-cn{display:flex;align-items:center;gap:0;min-width:0}
.s-cn .nm-txt{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
details.task.on .s-cn .nm-txt{color:var(--tx);font-weight:600}
details.task.off .s-cn .nm-txt{color:#a0a8b6;font-weight:500}
details.task.on>summary{background:linear-gradient(90deg,rgba(26,127,55,.045),transparent 42%)}
.s-time{font-size:11.5px;color:var(--tx2);text-align:right;
font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
details.task.off .s-time{color:#b8bfc9}
.s-quick{font-size:11px;color:var(--dim);text-align:left;
white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.grp-sep{margin:10px 0 3px;padding:5px 10px 4px;font-size:10.5px;font-weight:700;
color:var(--dim);letter-spacing:.5px;background:#f3f5f8;border-radius:5px;
border-left:3px solid #ccd3dd}
.grp-sep.on{color:var(--on);background:#eef7f0;border-left-color:var(--on)}
details.task[open]>summary{background:#f2f6ff;border-bottom:1px solid var(--line)}
.dt-wrap{padding:8px 10px 12px 26px;background:#fcfdfe}
.dt-cap{font-size:10.5px;font-weight:700;color:var(--dim);letter-spacing:.4px;
text-transform:uppercase;margin:6px 0 4px}
table.dt{font-size:11.5px;width:100%}
table.dt td{padding:3px 8px 3px 0;border-bottom:1px dotted #eef0f4;vertical-align:top}
table.dt td.dn{color:var(--dim);width:44%;white-space:nowrap;font-family:ui-monospace,monospace;font-size:10.5px}
.dn-cn{font-family:inherit;color:var(--tx2);font-size:11px;margin-left:5px;font-weight:500}
table.dt td.dv{color:var(--tx);font-weight:500}
table.dt tr:last-child td{border-bottom:none}
details.task.off .dt-wrap{opacity:.82}
/* 展開/收起按鈕 */
button.mini{font-size:11px;padding:3px 10px;margin-left:8px;border:1px solid var(--line);
background:#fff;color:var(--tx2);border-radius:6px;cursor:pointer;font-weight:500;
vertical-align:middle;transition:all .12s}
button.mini:hover{background:var(--accbg);border-color:#c7d9fb;color:var(--acc)}
button.mini:active{transform:translateY(1px)}
"""


def pane_html(cfg, daily, drift, tpl_tasks):
    m = MACHINES[cfg]
    tasks = [s for s in sorted(daily) if isinstance(daily[s], dict)]
    # 啟用的排上面（同組內按原字母序）
    tasks.sort(key=lambda s: (0 if (daily[s].get('scheduler') or {}).get('enable') is True else 1, s))
    btn_segs = set(snake(t) for t in tpl_tasks)
    en = [s for s in tasks if (daily[s].get('scheduler') or {}).get('enable') is True]

    rows = []
    printed_off_header = False
    for seg in tasks:
        t = daily[seg]
        sch = t.get('scheduler') or {}
        is_on = sch.get('enable') is True
        # 未啟用區段加一條分界提示（只加一次）
        if not is_on and not printed_off_header:
            printed_off_header = True
            rows.append('<div class="grp-sep">未啟用（%d）</div>' % (len(tasks) - len(en)))
        elif is_on and not rows:
            rows.append('<div class="grp-sep on">已啟用（%d）</div>' % len(en))
        fields = []
        for grp, fs in t.items():
            if grp == 'scheduler' or not isinstance(fs, dict):
                continue
            for f in fs:
                fields.append((grp, f))
        badge = '<span class="badge">按鈕</span>' if seg in btn_segs else ''
        if seg in PLACEHOLDER_SEGS:
            badge += '<span class="badge ph">空佔位</span>'
        cn = TASK_CN.get(seg, seg)

        # 收起時可見的參數摘要：優先序 + 最有代表性的 1-2 個參數
        quick = []
        pri = sch.get('priority')
        if pri is not None:
            quick.append('優先 %s' % pri)

        # 按代表性挑第一個存在的關鍵欄位
        PICK = [
            ('limit_count', '次數'),
            ('number_attack', '攻打'),
            ('limit_time', '限時'),
            ('layer', '層'),
            ('goryou_class', '類型'),
            ('bondling_mode', '模式'),
            ('bondling_stone_class', '式盤'),
            ('explore_level', '關卡'),
            ('exploration_level', '關卡'),
            ('layer_limit', '層限'),
            ('kirin_type', '麒麟'),
            ('when_attack_fail', '失敗'),
        ]
        shown = 0
        for grp, fs in t.items():
            if grp == 'scheduler' or not isinstance(fs, dict):
                continue
            for field, label in PICK:
                v = fs.get(field)
                if v is None or v == '' or v == '-1,-1':
                    continue
                s = str(v)
                if s in ('False', 'false') or s == ROLL:
                    continue
                if len(s) > 12:
                    s = s[:12] + '…'
                quick.append('%s %s' % (label, s))
                shown += 1
                break
            if shown >= 2:
                break
        quick_txt = '　'.join(quick)

        # 展開後的完整參數表（欄位名附中文）
        detail_rows = ''.join(
            '<tr><td class="dn">%s%s</td><td class="dv">%s</td></tr>' % (
                esc(f),
                ('<span class="dn-cn">%s</span>' % esc(FIELD_CN[f])) if f in FIELD_CN else '',
                vcell((t.get(grp) or {}).get(f)))
            for grp, f in sorted(fields))
        detail = (
            '<div class="dt-wrap">'
            '<div class="dt-cap">排程</div>'
            '<table class="dt"><tbody>'
            '<tr><td class="dn">啟用</td><td class="dv">%s</td></tr>'
            '<tr><td class="dn">時刻 server_update</td><td class="dv">%s</td></tr>'
            '<tr><td class="dn">優先序 priority</td><td class="dv">%s</td></tr>'
            '<tr><td class="dn">next_run</td><td class="dv"><span class="dim">不記錄（滾動值）</span></td></tr>'
            '</tbody></table>%s</div>'
        ) % (vcell(sch.get('enable')),
             vcell(sch.get('server_update')) or '<span class="dim">—</span>',
             vcell(sch.get('priority')) or '—',
             ('<div class="dt-cap">參數</div><table class="dt"><tbody>' + detail_rows + '</tbody></table>')
             if detail_rows else '')

        rows.append(
            '<details class="task %s">'
            '<summary>'
            '<span class="s-dot"></span>'
            '<span class="s-cn"><span class="nm-txt">%s</span>%s</span>'
            '<span class="s-time">%s</span>'
            '<span class="s-quick">%s</span>'
            '</summary>'
            '%s'
            '</details>' % (
                'on' if is_on else 'off',
                esc(cn), badge,
                vcell(sch.get('server_update')) or '<span class="dim">—</span>',
                esc(quick_txt),
                detail))

    if drift:
        drows = ''.join(
            '<tr><td>%s</td><td><code>%s</code></td>'
            '<td style="color:#2563eb;font-weight:600">%s</td>'
            '<td style="color:#b42318;font-weight:600">%s</td></tr>' % (
                esc(TASK_CN.get(d['task'], d['task'])), esc(d['field']),
                esc(d['should_be']), esc(d['actually'])) for d in drift)
        drift_html = ('<table><thead><tr><th>任務</th><th>欄位</th><th>應是</th><th>實際</th>'
                      '</tr></thead><tbody>%s</tbody></table>' % drows)
    else:
        drift_html = '<p class="ok">✓ 無差異</p>'

    return """<div class="pane">
  <div class="pane-h">
    <div class="nm">%(name)s<span class="id">%(cfg)s</span></div>
    <div class="meta"><code>%(cfg)s-daily.json</code><br>
      %(vm)s　<code>%(ip)s</code>　%(phone)s　<code>%(serial)s</code><br>
      任務 <b>%(total)d</b>　啟用 <b style="color:var(--on)">%(enabled)d</b>　停用 %(disabled)d</div>
  </div>
  <div class="pane-b">
    <div class="list-h"><span class="h-dot"></span><span class="h-cn">任務</span><span class="h-time">時刻</span><span class="h-quick">參數</span></div>
    <div class="tasklist">%(rows)s</div>
    <div class="drift-h">抓取時偏離（drift）</div>
    %(drift)s
  </div>
</div>""" % {
        'name': m['name'], 'cfg': cfg, 'vm': m['vm'], 'ip': m['ip'],
        'phone': m['phone'], 'serial': m['serial'],
        'total': len(tasks), 'enabled': len(en), 'disabled': len(tasks) - len(en),
        'rows': ''.join(rows), 'drift': drift_html,
    }


def render_all(data, version, date, captured, tpl_all):
    panes = []
    for cfg in ORDER:
        panes.append(pane_html(cfg, data[cfg]['daily'], data[cfg]['drift'],
                               sorted(tpl_all.get(cfg, {}))))

    common = None
    for cfg in ORDER:
        segs = {s for s, v in data[cfg]['daily'].items() if isinstance(v, dict)}
        common = segs if common is None else (common & segs)

    diff_rows = []
    for seg in sorted(common):
        a = data['qingcui']['daily'][seg].get('scheduler') or {}
        b = data['suolong']['daily'][seg].get('scheduler') or {}
        if a.get('enable') != b.get('enable'):
            diff_rows.append((TASK_CN.get(seg, seg), seg, 'scheduler.enable',
                              '開' if a.get('enable') else '關',
                              '開' if b.get('enable') else '關'))
        if a.get('server_update') != b.get('server_update'):
            diff_rows.append((TASK_CN.get(seg, seg), seg, 'scheduler.server_update',
                              a.get('server_update') or '—', b.get('server_update') or '—'))
        # 關鍵 config 欄位差異（只挑幾個常看的）
        for grp in ('raid_config', 'orochi_config', 'bondling_config', 'goryou_config',
                    'hunt_config', 'duel_config'):
            ga = data['qingcui']['daily'][seg].get(grp)
            gb = data['suolong']['daily'][seg].get(grp)
            if not isinstance(ga, dict) or not isinstance(gb, dict):
                continue
            for f in ('user_status', 'limit_count', 'layer', 'number_attack'):
                if f in ga or f in gb:
                    if ga.get(f) != gb.get(f):
                        diff_rows.append((TASK_CN.get(seg, seg), seg, '%s.%s' % (grp, f),
                                          str(ga.get(f)), str(gb.get(f))))

    if diff_rows:
        drows = ''.join(
            '<tr><td class="tn">%s<br><code>%s</code></td><td><code>%s</code></td>'
            '<td>%s</td><td>%s</td></tr>' % (
                esc(cn), esc(seg), esc(f), esc(va), esc(vb))
            for cn, seg, f, va, vb in diff_rows)
        diff_html = ('<table><thead><tr><th>任務</th><th>欄位</th><th>清脆</th><th>索隆</th>'
                     '</tr></thead><tbody>%s</tbody></table>' % drows)
        diff_cnt = len(diff_rows)
    else:
        diff_html = '<p class="ok">✓ 兩台設定完全一致</p>'
        diff_cnt = 0

    patches = ''.join('<tr><td><code>%s</code></td><td><code>%s</code></td></tr>' % (esc(k), esc(v))
                      for k, v in OAS['patches'].items())

    total_drift = sum(len(data[c]['drift']) for c in ORDER)
    grand = sum(len([s for s, v in data[c]['daily'].items() if isinstance(v, dict)]) for c in ORDER)

    return """<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OAS 日常配置記錄 · %(version)s</title><style>%(css)s</style></head><body>

<h1>OAS 日常配置記錄<span class="v">%(version)s</span></h1>
<div class="sub">記錄日期 %(date)s　·　抓取 %(captured)s　·　兩台合計 %(grand)d 個任務段</div>

<div class="card"><div class="note">
<b>取值規則</b>　① 標 <span class="badge">按鈕</span> 的任務 → 取 <code>pair.html</code> 的 DAILY 模板值（還原按鈕寫回什麼，日常就是什麼）
　② 其餘任務 → 取真機值（還原按鈕不碰它們，真機即日常）
　③ <b>next_run 一律不記錄</b>（滾動值，每天不同）
<br><span class="dim">兩台的 JSON 各自獨立存放（<code>qingcui-daily.json</code> / <code>suolong-daily.json</code>），互不含對方設定。
頁面上 <code>friend_1</code> 出現另一台的名字是跨號好友名，屬本機真實值。</span>
</div></div>

<h2>一、兩台並列對照<span class="cnt">點任務名展開參數　灰＝未啟用　綠＝已啟用</span>
<button id="expandAll" class="mini">全部展開</button>
<button id="collapseAll" class="mini">全部收起</button></h2>
<div class="split">
%(panes)s
</div>

<h2>二、兩台差異<span class="cnt">%(diff_cnt)d 項：啟用狀態 / 日常時刻 / 關鍵參數</span></h2>
<div class="card">%(diff)s</div>

<h2>三、版本資訊</h2>
<div class="card">
<p class="mono" style="margin:0 0 10px">OAS HEAD　%(head)s</p>
<table><thead><tr><th>本地補丁</th><th>sha256（前16）</th></tr></thead><tbody>%(patches)s</tbody></table>
<p class="mono" style="margin:12px 0 0;color:var(--dim)">
JSON：<code>qingcui-daily.json</code> · <code>suolong-daily.json</code>　｜　drift 合計 %(tdrift)d 條</p>
</div>

<p class="dim" style="margin-top:26px;font-size:11.5px;text-align:center">
OAS 日常配置記錄 · %(version)s · 由兩份 daily.json 渲染生成
</p>
<script>
(function(){
  var ea=document.getElementById('expandAll'), ca=document.getElementById('collapseAll');
  if(ea) ea.addEventListener('click', function(){
    document.querySelectorAll('details.task').forEach(function(d){ d.open=true; });
  });
  if(ca) ca.addEventListener('click', function(){
    document.querySelectorAll('details.task').forEach(function(d){ d.open=false; });
  });
})();
</script>
</body></html>""" % {
        'version': version, 'date': date, 'captured': captured, 'css': CSS,
        'panes': ''.join(panes), 'diff': diff_html, 'diff_cnt': diff_cnt,
        'head': esc(OAS['head']), 'patches': patches,
        'tdrift': total_drift, 'grand': grand,
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
    captured = a.captured or (a.date + 'T00:00:00+08:00')

    data = {}
    for cfg in ORDER:
        raw = load_json(os.path.join(vdir, 'raw', '%s.json' % cfg))
        daily = build_daily(cfg, raw, tpl_all)
        drift = drift_of(daily, raw)
        data[cfg] = {'daily': daily, 'drift': drift}

        tasks = len([s for s, v in daily.items() if isinstance(v, dict)])
        en = sum(1 for s, v in daily.items() if isinstance(v, dict)
                 and (v.get('scheduler') or {}).get('enable') is True)

        # ★ JSON 分開，檔名帶機器前綴
        open(os.path.join(vdir, '%s-daily.json' % cfg), 'w', encoding='utf-8').write(
            json.dumps(daily, ensure_ascii=False, indent=2))
        open(os.path.join(vdir, '%s-drift.json' % cfg), 'w', encoding='utf-8').write(
            json.dumps({'checked_at': captured, 'machine': cfg, 'diffs': drift},
                       ensure_ascii=False, indent=2))
        open(os.path.join(vdir, '%s-deployed.json' % cfg), 'w', encoding='utf-8').write(
            json.dumps({seg: (v.get('scheduler') or {}) for seg, v in raw.items()
                        if isinstance(v, dict)}, ensure_ascii=False, indent=2))
        open(os.path.join(vdir, '%s-meta.json' % cfg), 'w', encoding='utf-8').write(
            json.dumps({
                'version': a.version, 'date': a.date, 'captured_at': captured,
                'machine': MACHINES[cfg], 'oas': OAS,
                'button_tasks': sorted(tpl_all.get(cfg, {})),
                'source_of_truth': {
                    'button_tasks': 'pair.html 的 DAILY 模板',
                    'other_tasks': '真機 config（還原按鈕不碰）',
                    'next_run': '不記錄（滾動值）',
                },
                'summary': {'total_task_segments': tasks, 'enabled': en},
            }, ensure_ascii=False, indent=2))

        print('%-4s (%s)  任務=%d  啟用=%d  drift=%d' % (
            MACHINES[cfg]['name'], cfg, tasks, en, len(drift)))
        for d in drift:
            print('        DRIFT %s %s  應=%r 實際=%r' % (
                d['task'], d['field'], d['should_be'], d['actually']))

    # ★ 單一 HTML
    open(os.path.join(vdir, 'daily.html'), 'w', encoding='utf-8').write(
        render_all(data, a.version, a.date, captured, tpl_all))
    print('\n-> %s/daily.html（單一頁面，左右並列）' % a.version)


if __name__ == '__main__':
    main()
