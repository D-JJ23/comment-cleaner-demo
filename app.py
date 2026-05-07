import re
from collections import Counter, defaultdict
import streamlit as st
import pandas as pd

st.set_page_config(page_title='闲语清屏', page_icon='🧹', layout='wide')

for k, v in {
    'page': '首页',
    'whitelist': ['感谢', '支持', '收藏', '学到了', '实用'],
    'spam_list': ['微信', '加我', '私信', '链接', '代理', '互关', '引流'],
    'neg_list': ['笑死', '垃圾', '滚', '废物', '骗', '水'],
    'min_keep_len': 5,
    'alert_threshold': 65,
    'clean_run_id': 0,
    'cleaned_df': pd.DataFrame(),
    'saved_batches': [],
    'review_items': [],
    'review_status': {},
    'review_decisions': {},
    'delete_target_batch': None,
    'delete_confirm_checked': False,
    'input_text': '',
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

sample_comments = [
    '太好了，学到了，感谢分享！',
    '加我微信 123456 领取免费资料',
    '内容不错，就是有点水',
    '哈哈哈',
    '这个方法太实用了，收藏了',
    '求互关，私信我',
    '你这也叫教程？笑死',
    '今天阳光很好',
    '链接在主页，低价代理',
    '作者讲得很清楚，支持',
    '哈哈哈哈哈哈哈',
    '同意',
    '1',
    '加群看主页',
    '这也太离谱了吧',
    '真的很实用，感谢',
    '看不懂',
    '私信我领资料',
    '垃圾内容',
    '顶顶顶',
    '哈哈',
    '主页有福利'
]

if not st.session_state.input_text:
    st.session_state.input_text = '\n'.join(sample_comments)

def page(name):
    st.session_state.page = name

def norm(t):
    return re.sub(r'\s+', '', str(t).strip())

def toks(t):
    s = norm(t)
    p = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}|\d+|[!?！？。.,，]+', s)
    return p if p else [s]

def classify(t):
    s = str(t).strip()
    n = norm(s)
    if not s:
        return '空白', '空行', 0.0
    if any(x in s for x in st.session_state.whitelist):
        return '优质保留', '命中白名单', 0.95
    if any(x in s for x in st.session_state.spam_list):
        return '广告引流', '命中广告词', 0.9
    if any(x in s for x in st.session_state.neg_list):
        return '杠精/负能量', '命中负面词', 0.86
    if len(n) < st.session_state.min_keep_len:
        return '无意义灌水', '过短', 0.8
    if re.fullmatch(r'[哈嘿哦啊嗯嘛~!！?.。，,。]+', s):
        return '无意义灌水', '纯情绪/口水', 0.82
    if re.search(r'\d{5,}', s):
        return '广告引流', '疑似号码', 0.88
    if len(set(n)) <= 2 and len(n) <= 6:
        return '无意义灌水', '低信息密度', 0.76
    return '待人工', '需人工复核', 0.5

def run_cleaning():
    rows = []
    raw_lines = [x for x in st.session_state.input_text.splitlines() if x.strip()]
    for i, line in enumerate(raw_lines, 1):
        lab, why, score = classify(line)
        rows.append({
            '序号': i,
            '原始评论': line,
            '分类': lab,
            '建议操作': '保留' if lab == '优质保留' else '隐藏',
            '理由': why,
            '置信度': round(score, 2),
            '人工审核': '待人工审核' if lab == '待人工' else '无需人工',
            '用户ID': f'U{(i % 6) + 1}',
            '批次时间': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
        })
    st.session_state.cleaned_df = pd.DataFrame(rows)
    st.session_state.review_items = st.session_state.cleaned_df.loc[
        st.session_state.cleaned_df['人工审核'] == '待人工审核',
        ['序号', '原始评论']
    ].to_dict('records') if not st.session_state.cleaned_df.empty else []
    st.session_state.clean_run_id += 1
    st.session_state.review_status = {}
    st.session_state.review_decisions = {}

def current_df():
    return st.session_state.cleaned_df.copy() if not st.session_state.cleaned_df.empty else pd.DataFrame()

def save_batch(df):
    snap = {
        '批次': st.session_state.clean_run_id,
        'summary': {
            '总评论': len(df),
            '保留': int((df['建议操作'] == '保留').sum()) if '建议操作' in df else 0,
            '隐藏': int((df['建议操作'] == '隐藏').sum()) if '建议操作' in df else 0,
            '待人工': int((df['人工审核'] == '待人工审核').sum()) if '人工审核' in df else 0,
            '已审核': int((df['人工审核'] == '已审核').sum()) if '人工审核' in df else 0
        },
        'data': df.fillna('').to_dict('records')
    }
    st.session_state.saved_batches = [b for b in st.session_state.saved_batches if b['批次'] != snap['批次']] + [snap]

def delete_batch(bid):
    st.session_state.saved_batches = [b for b in st.session_state.saved_batches if b['批次'] != bid]
    st.session_state.delete_target_batch = None
    st.session_state.delete_confirm_checked = False
    st.rerun()

def score(df):
    if df.empty:
        return 0, '暂无数据'
    n = len(df)
    s = float((df['分类'] == '广告引流').sum()) / n if '分类' in df else 0
    g = float((df['分类'] == '杠精/负能量').sum()) / n if '分类' in df else 0
    r = float((df['人工审核'] == '待人工审核').sum()) / n if '人工审核' in df else 0
    val = max(0, 100 - int((s * 45 + g * 35 + r * 20) * 100))
    return val, '健康' if val >= 80 else '轻度波动' if val >= 60 else '需要治理'

def trend_df():
    rows = []
    for b in st.session_state.saved_batches:
        sc, _ = score(pd.DataFrame(b['data']))
        s = b['summary']
        rows.append({'批次': b['批次'], '总评论': s['总评论'], '保留': s['保留'], '隐藏': s['隐藏'], '待人工': s['待人工'], '健康度': sc})
    return pd.DataFrame(rows)

def clusters(df):
    m = defaultdict(list)
    for _, r in df.iterrows():
        k = re.sub(r'[!?！？。.,，]+', '标点', re.sub(r'\d+', '0', norm(r.get('原始评论', ''))))[:12]
        m[k].append(r.get('原始评论', ''))
    return sorted(m.items(), key=lambda x: len(x[1]), reverse=True)

def profile(df):
    if df.empty:
        return pd.DataFrame()
    g = df.groupby('用户ID').agg(
        评论数=('原始评论', 'count'),
        广告=('分类', lambda s: int((s == '广告引流').sum())),
        负能量=('分类', lambda s: int((s == '杠精/负能量').sum())),
        待审=('人工审核', lambda s: int((s == '待人工审核').sum())),
        保留=('建议操作', lambda s: int((s == '保留').sum()))
    ).reset_index()
    g['风险分'] = (g['广告'] * 3 + g['负能量'] * 2 + g['待审']) / g['评论数'].clip(lower=1)
    g['类型'] = g['风险分'].apply(lambda x: '高风险' if x >= 1 else '中风险' if x >= 0.5 else '低风险')
    return g.sort_values(['风险分', '评论数'], ascending=[False, False])

def keyword_suggest(df):
    rt, stt, nt = [], [], []
    for _, r in df.iterrows():
        ts = toks(r.get('原始评论', ''))
        if r.get('建议操作') == '保留':
            rt += ts
        if r.get('分类') == '广告引流':
            stt += ts
        if r.get('分类') == '杠精/负能量':
            nt += ts
    def top(arr):
        return Counter([x for x in arr if len(x) > 1 and x not in st.session_state.whitelist and x not in st.session_state.spam_list and x not in st.session_state.neg_list]).most_common(8)
    return top(rt), top(stt), top(nt)

def weekly(df):
    if df.empty:
        return pd.DataFrame()
    return pd.DataFrame([{
        '周报主题': '闲语清屏治理周报',
        '总评论': len(df),
        '保留': int((df['建议操作'] == '保留').sum()) if '建议操作' in df else 0,
        '隐藏': int((df['建议操作'] == '隐藏').sum()) if '建议操作' in df else 0,
        '待人工': int((df['人工审核'] == '待人工审核').sum()) if '人工审核' in df else 0,
        '广告引流': int((df['分类'] == '广告引流').sum()) if '分类' in df else 0,
        '负能量': int((df['分类'] == '杠精/负能量').sum()) if '分类' in df else 0,
        '无意义灌水': int((df['分类'] == '无意义灌水').sum()) if '分类' in df else 0
    }])

def alert(df):
    if df.empty:
        return pd.DataFrame()
    sc, stt = score(df)
    msgs = []
    if sc <= st.session_state.alert_threshold:
        msgs.append(f'健康度低于阈值 {st.session_state.alert_threshold}')
    if int((df['分类'] == '广告引流').sum()) >= max(3, len(df) // 4):
        msgs.append('广告评论偏多')
    if int((df['分类'] == '杠精/负能量').sum()) >= max(3, len(df) // 5):
        msgs.append('负能量评论偏多')
    if int((df['人工审核'] == '待人工审核').sum()) > len(df) * 0.4:
        msgs.append('待人工比例偏高')
    return pd.DataFrame([{
        '批次': st.session_state.clean_run_id,
        '健康度': sc,
        '状态': stt,
        '告警': '；'.join(msgs) if msgs else '暂无异常'
    }])

st.sidebar.title('菜单')
for x in ['首页', '关键词筛选', '人工审核', '最终结果', '清理记录', '智能洞察', '周报中心', '自动告警']:
    st.sidebar.button(x, key=f'nav_{x}', use_container_width=True, on_click=page, args=(x,))

st.title('闲语清屏')
st.caption('精简版：保留核心功能，去掉冗余结构')

st.sidebar.divider()
st.sidebar.subheader('关键词')
white_text = st.sidebar.text_input('白名单', value=','.join(st.session_state.whitelist), key='white_text')
spam_text = st.sidebar.text_input('广告词', value=','.join(st.session_state.spam_list), key='spam_text')
neg_text = st.sidebar.text_input('负能量词', value=','.join(st.session_state.neg_list), key='neg_text')
st.session_state.min_keep_len = st.sidebar.slider('最短字数', 2, 20, st.session_state.min_keep_len, key='min_keep')
st.session_state.alert_threshold = st.sidebar.slider('告警阈值', 0, 100, st.session_state.alert_threshold, key='alert_th')
st.session_state.whitelist = [x.strip() for x in white_text.split(',') if x.strip()]
st.session_state.spam_list = [x.strip() for x in spam_text.split(',') if x.strip()]
st.session_state.neg_list = [x.strip() for x in neg_text.split(',') if x.strip()]
st.session_state.input_text = st.text_area('输入评论，每行一条', '\n'.join(sample_comments), height=220)

if st.session_state.page == '首页':
    a, b, c, d = st.columns(4)
    a.metric('类型', '4+1')
    b.metric('关键词组', f'{len(st.session_state.whitelist)} / {len(st.session_state.spam_list)} / {len(st.session_state.neg_list)}')
    c.metric('最短字数', st.session_state.min_keep_len)
    d.metric('告警阈值', st.session_state.alert_threshold)
    st.markdown('### 这是一个更短、更干净的版本')
    st.write('保留了筛选、人工审核、结果、记录、洞察、周报、告警等核心页面。')
    st.write('建议先在“关键词筛选”页运行清理。')

elif st.session_state.page == '关键词筛选':
    st.header('关键词筛选')
    c1, c2, c3 = st.columns(3)
    c1.write(st.session_state.whitelist)
    c2.write(st.session_state.spam_list)
    c3.write(st.session_state.neg_list)
    if st.button('开始清理', type='primary'):
        run_cleaning()
        st.session_state.page = '最终结果'
        st.rerun()

elif st.session_state.page == '人工审核':
    st.header('人工审核')
    if st.session_state.review_items:
        for item in st.session_state.review_items:
            seq, txt = item['序号'], item['原始评论']
            dkey, rkey, skey = f'd{seq}', f'r{seq}', f's{seq}'
            with st.expander(f'评论 {seq} · {txt[:30]}'):
                if dkey not in st.session_state:
                    st.session_state[dkey] = '保留'
                if rkey not in st.session_state:
                    st.session_state[rkey] = '内容有价值'
                dec = st.radio('处理结果', ['保留', '隐藏'], key=dkey)
                rea = st.selectbox('理由', ['内容有价值', '重复/灌水', '与主题无关', '广告/引流', '情绪攻击', '其他'], key=rkey)
                kw = st.text_input('手动关键词', value='', key=f'k{seq}')
                if st.button('加入白名单', key=f'w{seq}'):
                    st.session_state.whitelist = list(dict.fromkeys(st.session_state.whitelist + [x.strip() for x in kw.split(',') if x.strip()]))
                if st.button('加入广告词', key=f'a{seq}'):
                    st.session_state.spam_list = list(dict.fromkeys(st.session_state.spam_list + [x.strip() for x in kw.split(',') if x.strip()]))
                if st.button('加入负能量词', key=f'n{seq}'):
                    st.session_state.neg_list = list(dict.fromkeys(st.session_state.neg_list + [x.strip() for x in kw.split(',') if x.strip()]))
                if st.button('提交审核结果', key=skey):
                    if not st.session_state.cleaned_df.empty:
                        m = st.session_state.cleaned_df['序号'] == seq
                        st.session_state.cleaned_df.loc[m, ['人工审核结果', '人工审核理由', '人工审核', '建议操作']] = [dec, rea, '已审核', dec]
                    st.success(f'已提交：{dec} · {rea}')
    else:
        st.info('当前没有待人工审核的评论。')

elif st.session_state.page == '最终结果':
    st.header('最终结果')
    df = current_df()
    if df.empty:
        st.info('还没有清理结果。')
    else:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric('总评论', len(df))
        c2.metric('保留', int((df['建议操作'] == '保留').sum()))
        c3.metric('隐藏', int((df['建议操作'] == '隐藏').sum()))
        c4.metric('待人工', int((df['人工审核'] == '待人工审核').sum()))
        c5.metric('已审核', int((df['人工审核'] == '已审核').sum()))
        if st.checkbox('确认保存到清理记录'):
            save_batch(df)
            st.success('已保存。')
        show_cols = [x for x in ['序号', '原始评论', '用户ID', '批次时间', '分类', '建议操作', '理由', '置信度', '人工审核', '人工审核结果', '人工审核理由'] if x in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
        st.download_button('下载结果 CSV', df[show_cols].to_csv(index=False).encode('utf-8-sig'), 'cleaned_comments.csv', 'text/csv')

elif st.session_state.page == '清理记录':
    st.header('清理记录')
    if not st.session_state.saved_batches:
        st.info('当前还没有保存的清理记录。')
    else:
        labels = [f"第 {b['批次']} 批 · 保留 {b['summary']['保留']} · 隐藏 {b['summary']['隐藏']}" for b in st.session_state.saved_batches]
        sel = st.selectbox('记录列表', labels)
        batch = st.session_state.saved_batches[labels.index(sel)]
        s = batch['summary']
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric('总评论', s['总评论'])
        c2.metric('保留', s['保留'])
        c3.metric('隐藏', s['隐藏'])
        c4.metric('待人工', s['待人工'])
        c5.metric('已审核', s['已审核'])
        if st.button('删除此批次', key=f"del_{batch['批次']}"):
            st.session_state.delete_target_batch = batch['批次']
        if st.session_state.delete_target_batch == batch['批次']:
            st.warning(f"确认删除第 {batch['批次']} 批吗？")
            st.session_state.delete_confirm_checked = st.checkbox(f'我确认要删除第 {batch["批次"]} 批', value=st.session_state.delete_confirm_checked, key=f'ck_{batch["批次"]}')
            if st.button('确认删除', key=f'cd_{batch["批次"]}'):
                if st.session_state.delete_confirm_checked:
                    delete_batch(batch['批次'])
                else:
                    st.error('请先勾选确认框。')
        with st.expander(f"展开查看第 {batch['批次']} 批最终结果"):
            view_df = pd.DataFrame(batch['data'])
            show_cols = [x for x in ['序号', '原始评论', '用户ID', '批次时间', '分类', '建议操作', '理由', '置信度', '人工审核', '人工审核结果', '人工审核理由'] if x in view_df.columns]
            st.dataframe(view_df[show_cols], use_container_width=True, hide_index=True)
            st.download_button(f"下载第 {batch['批次']} 批 CSV", view_df[show_cols].to_csv(index=False).encode('utf-8-sig'), f"batch_{batch['批次']}.csv", 'text/csv')

elif st.session_state.page == '智能洞察':
    st.header('智能洞察')
    df = current_df()
    if df.empty:
        st.info('先去“关键词筛选”页跑一批评论。')
    else:
        sc, note = score(df)
        a, b, c, d = st.columns(4)
        a.metric('批次健康度', f'{sc}/100')
        b.metric('治理状态', note)
        c.metric('评论总数', len(df))
        d.metric('已保存批次', len(st.session_state.saved_batches))
        tdf = trend_df()
        if not tdf.empty:
            st.markdown('### 批次趋势')
            st.line_chart(tdf.set_index('批次')[['健康度', '总评论', '保留', '隐藏', '待人工']])
            st.dataframe(tdf, use_container_width=True, hide_index=True)
        st.markdown('### 分类分布')
        st.bar_chart(df.groupby('分类').size())
        st.markdown('### 关键词热度')
        cnt = Counter()
        for t in df['原始评论'].astype(str):
            for w in toks(t):
                if len(w) > 1 and w not in st.session_state.whitelist and w not in st.session_state.spam_list and w not in st.session_state.neg_list:
                    cnt[w] += 1
        hot = pd.Series(dict(cnt.most_common(12)))
        if not hot.empty:
            st.bar_chart(hot)
        rt, at, nt = keyword_suggest(df)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write('**保留候选**')
            [st.write(f'- {w} × {n}') for w, n in rt]
        with c2:
            st.write('**广告候选**')
            [st.write(f'- {w} × {n}') for w, n in at]
        with c3:
            st.write('**负能量候选**')
            [st.write(f'- {w} × {n}') for w, n in nt]
        st.markdown('### 重复评论聚类')
        for i, (k, items) in enumerate(clusters(df)[:8], 1):
            with st.expander(f'聚类 {i} · {len(items)} 条 · {k}'):
                for x in items[:10]:
                    st.write(f'- {x}')
        st.markdown('### 用户画像')
        pf = profile(df)
        if not pf.empty:
            st.dataframe(pf, use_container_width=True, hide_index=True)
            st.scatter_chart(pf.set_index('用户ID')[['评论数', '风险分']])
        st.markdown('### 治理报告')
        rep = {
            '总评论': len(df),
            '保留': int((df['建议操作'] == '保留').sum()) if '建议操作' in df else 0,
            '隐藏': int((df['建议操作'] == '隐藏').sum()) if '建议操作' in df else 0,
            '待人工': int((df['人工审核'] == '待人工审核').sum()) if '人工审核' in df else 0,
            '广告引流': int((df['分类'] == '广告引流').sum()) if '分类' in df else 0,
            '负能量': int((df['分类'] == '杠精/负能量').sum()) if '分类' in df else 0,
            '无意义灌水': int((df['分类'] == '无意义灌水').sum()) if '分类' in df else 0
        }
        st.json(rep)
        st.download_button('下载治理报告 CSV', pd.DataFrame([rep]).to_csv(index=False).encode('utf-8-sig'), 'governance_report.csv', 'text/csv')

elif st.session_state.page == '周报中心':
    st.header('周报中心')
    df = current_df()
    if df.empty:
        st.info('先去“关键词筛选”页跑一批评论。')
    else:
        wb = weekly(df)
        st.dataframe(wb, use_container_width=True, hide_index=True)
        st.download_button('下载周报 CSV', wb.to_csv(index=False).encode('utf-8-sig'), 'weekly_report.csv', 'text/csv')
        st.write('本周系统自动完成评论分类、人工复核、风险用户识别、批次趋势跟踪和治理报告汇总。')

else:
    st.header('自动告警')
    df = current_df()
    if df.empty:
        st.info('先去“关键词筛选”页跑一批评论。')
    else:
        ar = alert(df)
        st.dataframe(ar, use_container_width=True, hide_index=True)
        st.download_button('下载告警 CSV', ar.to_csv(index=False).encode('utf-8-sig'), 'alert_report.csv', 'text/csv')
        st.write('当健康度低于阈值，或广告/负能量/待审比例过高时，会自动触发告警。')
