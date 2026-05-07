import re
from collections import Counter, defaultdict
import streamlit as st
import pandas as pd

st.set_page_config(page_title='闲语清屏 Demo', page_icon='🧹', layout='wide')

for k, v in {
    'page': '首页',
    'review_items': [],
    'whitelist': ['感谢', '支持', '收藏', '学到了', '实用'],
    'spam_list': ['微信', '加我', '私信', '链接', '代理', '互关', '引流'],
    'neg_list': ['笑死', '垃圾', '滚', '废物', '骗', '水'],
    'pending_add_white': [],
    'pending_add_spam': [],
    'pending_add_neg': [],
    'cleaned_df': pd.DataFrame(),
    'review_decisions': {},
    'review_status': {},
    'min_keep_len': 5,
    'clean_run_id': 0,
    'saved_batches': [],
    'delete_target_batch': None,
    'delete_confirm_checked': False,
    'last_batch_snapshot': None,
    'alert_threshold': 65,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

sample_comments = [
    '太好了，学到了，感谢分享！', '加我微信 123456 领取免费资料', '内容不错，就是有点水', '哈哈哈',
    '这个方法太实用了，收藏了', '求互关，私信我', '你这也叫教程？笑死', '今天阳光很好',
    '链接在主页，低价代理', '作者讲得很清楚，支持', '哈哈哈哈哈哈哈', '同意', '1', '加群看主页', '这也太离谱了吧',
    '真的很实用，感谢', '看不懂', '私信我领资料', '垃圾内容', '顶顶顶', '哈哈', '主页有福利'
]

def set_page(name):
    st.session_state.page = name

st.sidebar.title('菜单')
for label in ['首页', '关键词筛选', '人工审核', '最终结果', '清理记录', '智能洞察', '周报中心', '自动告警']:
    st.sidebar.button(label, key=f'nav_{label}', use_container_width=True, on_click=set_page, args=(label,))

st.title('闲语清屏')
st.caption('评论清理 + 智能洞察 + 周报 + 自动告警 Demo')

st.sidebar.divider()
st.sidebar.subheader('关键词筛选列表')
white_text = st.sidebar.text_input('白名单关键词（逗号分隔）', value=','.join(st.session_state.whitelist), key='white_input')
spam_text = st.sidebar.text_input('广告关键词（逗号分隔）', value=','.join(st.session_state.spam_list), key='spam_input')
neg_text = st.sidebar.text_input('负能量关键词（逗号分隔）', value=','.join(st.session_state.neg_list), key='neg_input')
st.session_state.min_keep_len = st.sidebar.slider('保留评论最短字数', 2, 20, st.session_state.min_keep_len, key='keep_len_slider')
st.session_state.alert_threshold = st.sidebar.slider('自动告警阈值', 0, 100, st.session_state.alert_threshold, key='alert_threshold_slider')

white = [x.strip() for x in white_text.split(',') if x.strip()]
spam = [x.strip() for x in spam_text.split(',') if x.strip()]
neg = [x.strip() for x in neg_text.split(',') if x.strip()]
text_input = st.text_area('输入评论，支持每行一条', '\n'.join(sample_comments), height=230)

def normalize(text):
    return re.sub(r'\s+', '', str(text).strip())

def tokenize(text):
    text = normalize(text)
    parts = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}|\d+|[!?！？。.,，]+', text)
    return parts if parts else [text]

def classify(comment: str):
    t = str(comment).strip()
    nt = normalize(t)
    if not t:
        return '空白', '空行', 0.0
    if any(k in t for k in white):
        return '优质保留', '命中白名单', 0.95
    if any(k in t for k in spam):
        return '广告引流', '命中广告词', 0.9
    if any(k in t for k in neg):
        return '杠精/负能量', '命中负面词', 0.86
    if len(nt) < st.session_state.min_keep_len:
        return '无意义灌水', '过短', 0.8
    if re.fullmatch(r'[哈嘿哦啊嗯嘛~!！?.。，,。]+', t):
        return '无意义灌水', '纯情绪/口水', 0.82
    if re.search(r'\d{5,}', t):
        return '广告引流', '疑似号码', 0.88
    if len(set(nt)) <= 2 and len(nt) <= 6:
        return '无意义灌水', '低信息密度', 0.76
    return '待人工', '需人工复核', 0.5

def run_cleaning():
    rows = []
    raw_lines = [x for x in text_input.splitlines() if x.strip()]
    for i, line in enumerate(raw_lines, 1):
        label, reason, score = classify(line)
        rows.append({
            '序号': i,
            '原始评论': line,
            '分类': label,
            '建议操作': '保留' if label == '优质保留' else '隐藏',
            '理由': reason,
            '置信度': round(score, 2),
            '人工审核': '待人工审核' if label == '待人工' else '无需人工',
            '用户ID': f'U{(i % 6) + 1}',
            '批次时间': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')
        })
    st.session_state.cleaned_df = pd.DataFrame(rows)
    st.session_state.review_items = st.session_state.cleaned_df.loc[
        st.session_state.cleaned_df['人工审核'] == '待人工审核', ['序号', '原始评论']
    ].fillna('').to_dict('records')
    st.session_state.clean_run_id += 1
    st.session_state.review_status = {}
    st.session_state.review_decisions = {}
    st.session_state.pending_add_white = []
    st.session_state.pending_add_spam = []
    st.session_state.pending_add_neg = []
    st.session_state.delete_target_batch = None
    st.session_state.delete_confirm_checked = False
    st.session_state.last_batch_snapshot = None

def apply_review(seq, action, reason):
    df = st.session_state.cleaned_df
    if df.empty:
        return
    m = df['序号'] == seq
    if m.any():
        df.loc[m, ['人工审核结果', '人工审核理由', '人工审核', '建议操作']] = [action, reason, '已审核', action]
        st.session_state.review_decisions[seq] = {'action': action, 'reason': reason}

def current_final_df():
    return st.session_state.cleaned_df.copy() if not st.session_state.cleaned_df.empty else pd.DataFrame()

def summarize_batch(df):
    return {
        '总评论': len(df),
        '保留': int((df['建议操作'] == '保留').sum()) if '建议操作' in df else 0,
        '隐藏': int((df['建议操作'] == '隐藏').sum()) if '建议操作' in df else 0,
        '待人工': int((df['人工审核'] == '待人工审核').sum()) if '人工审核' in df else 0,
        '已审核': int((df['人工审核'] == '已审核').sum()) if '人工审核' in df else 0,
    }

def save_current_batch(df):
    snap = {
        '批次': st.session_state.clean_run_id,
        'summary': summarize_batch(df),
        'data': df.fillna('').to_dict('records')
    }
    st.session_state.saved_batches = sorted(
        [b for b in st.session_state.saved_batches if b['批次'] != snap['批次']] + [snap],
        key=lambda x: x['批次']
    )
    st.session_state.last_batch_snapshot = snap

def delete_batch(batch_id):
    st.session_state.saved_batches = [b for b in st.session_state.saved_batches if b['批次'] != batch_id]
    st.session_state.delete_target_batch = None
    st.session_state.delete_confirm_checked = False
    st.rerun()

def build_keyword_suggestions(df, topn=8):
    retain_tokens, spam_tokens, neg_tokens = [], [], []
    for _, row in df.iterrows():
        toks = tokenize(str(row.get('原始评论', '')))
        if row.get('建议操作') == '保留':
            retain_tokens.extend(toks)
        if row.get('分类') == '广告引流':
            spam_tokens.extend(toks)
        if row.get('分类') == '杠精/负能量':
            neg_tokens.extend(toks)
    def top(tokens):
        return Counter([t for t in tokens if len(t) > 1 and t not in white and t not in spam and t not in neg]).most_common(topn)
    return top(retain_tokens), top(spam_tokens), top(neg_tokens)

def build_cluster_report(df):
    groups = defaultdict(list)
    for _, row in df.iterrows():
        txt = normalize(row.get('原始评论', ''))
        key = re.sub(r'\d+', '0', txt)
        key = re.sub(r'[哈嘿哦啊嗯嘛]{2,}', '情绪重复', key)
        key = re.sub(r'[!?！？。.,，]+', '标点', key)
        groups[key[:12]].append(row.get('原始评论', ''))
    return sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)

def batch_health_score(df):
    if df.empty:
        return 0, '暂无数据'
    total = len(df)
    spam_rate = float((df['分类'] == '广告引流').sum()) / total if '分类' in df else 0
    neg_rate = float((df['分类'] == '杠精/负能量').sum()) / total if '分类' in df else 0
    review_rate = float((df['人工审核'] == '待人工审核').sum()) / total if '人工审核' in df else 0
    clean = max(0, 100 - int((spam_rate * 45 + neg_rate * 35 + review_rate * 20) * 100))
    return clean, '健康' if clean >= 80 else '轻度波动' if clean >= 60 else '需要治理'

def trend_by_batch():
    if not st.session_state.saved_batches:
        return pd.DataFrame()
    rows = []
    for b in st.session_state.saved_batches:
        s = b['summary']
        score, _ = batch_health_score(pd.DataFrame(b['data']))
        rows.append({'批次': b['批次'], '总评论': s['总评论'], '保留': s['保留'], '隐藏': s['隐藏'], '待人工': s['待人工'], '健康度': score})
    return pd.DataFrame(rows)

def infer_profiles(df):
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

def weekly_report(df):
    if df.empty:
        return pd.DataFrame()
    report = {
        '周报主题': '闲语清屏治理周报',
        '总评论': len(df),
        '保留': int((df['建议操作'] == '保留').sum()),
        '隐藏': int((df['建议操作'] == '隐藏').sum()),
        '待人工': int((df['人工审核'] == '待人工审核').sum()),
        '广告引流': int((df['分类'] == '广告引流').sum()),
        '负能量': int((df['分类'] == '杠精/负能量').sum()),
        '无意义灌水': int((df['分类'] == '无意义灌水').sum()),
    }
    return pd.DataFrame([report])

def alert_report(df):
    if df.empty:
        return pd.DataFrame()
    score, note = batch_health_score(df)
    flags = []
    if score <= st.session_state.alert_threshold:
        flags.append(f'健康度低于阈值 {st.session_state.alert_threshold}')
    if '分类' in df.columns and int((df['分类'] == '广告引流').sum()) >= max(3, len(df) // 4):
        flags.append('广告评论偏多')
    if '分类' in df.columns and int((df['分类'] == '杠精/负能量').sum()) >= max(3, len(df) // 5):
        flags.append('负能量评论偏多')
    if '人工审核' in df.columns and int((df['人工审核'] == '待人工审核').sum()) > len(df) * 0.4:
        flags.append('待人工比例偏高')
    if not flags:
        flags.append('暂无异常')
    return pd.DataFrame([{'批次': st.session_state.clean_run_id, '健康度': score, '状态': note, '告警': '；'.join(flags)}])

if st.session_state.page == '首页':
    a, b, c, d = st.columns(4)
    a.metric('可识别类型', '4+1')
    b.metric('关键词组', f'{len(white)} / {len(spam)} / {len(neg)}')
    c.metric('最短字数', st.session_state.min_keep_len)
    d.metric('告警阈值', st.session_state.alert_threshold)
    l, r = st.columns([1.15, 0.85], gap='large')
    with l:
        st.markdown('### 让评论清理更像治理系统')
        st.write('这个版本加入了按批次趋势图、自动告警、关键词热度、用户画像和周报中心。')
        st.write('它更像一个轻量治理后台，而不是单纯的筛选脚本。')
        st.info('建议先跑一批评论，再到智能洞察、周报中心和自动告警查看结果。')
    with r:
        st.markdown('### 新增能力')
        st.write('• 批次趋势折线图。')
        st.write('• 自动告警。')
        st.write('• 关键词热度图。')
        st.write('• 用户画像与周报。')
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric('示例评论', len(sample_comments))
    m2.metric('创新模块', '5 个')
    m3.metric('页面入口', '左侧菜单')

elif st.session_state.page == '关键词筛选':
    st.header('关键词筛选')
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric('白名单', len(white))
        st.write(white)
    with c2:
        st.metric('广告词', len(spam))
        st.write(spam)
    with c3:
        st.metric('负能量词', len(neg))
        st.write(neg)
    st.info('点击“开始清理”后，会同时生成初筛结果与后续智能洞察所需的数据。')
    if st.button('开始清理', key=f'clean_keywords_{st.session_state.clean_run_id}', type='primary'):
        run_cleaning()
        st.session_state.page = '最终结果'
        st.rerun()

elif st.session_state.page == '人工审核':
    st.header('人工审核')
    st.caption(f'当前清理批次：{st.session_state.clean_run_id}')
    if st.session_state.review_items:
        for item in st.session_state.review_items:
            seq = item.get('序号', '')
            comment_text = item.get('原始评论', '')
            decision_key = f'decision_{st.session_state.clean_run_id}_{seq}'
            reason_key = f'review_reason_{st.session_state.clean_run_id}_{seq}'
            kw_key = f'kw_{st.session_state.clean_run_id}_{seq}'
            submit_key = f'submit_{st.session_state.clean_run_id}_{seq}'
            white_key = f'white_{st.session_state.clean_run_id}_{seq}'
            spam_key = f'spam_{st.session_state.clean_run_id}_{seq}'
            neg_key = f'neg_{st.session_state.clean_run_id}_{seq}'
            with st.expander(f'评论 {seq} · {comment_text[:30]}'):
                c1, c2 = st.columns([1, 1])
                if decision_key not in st.session_state:
                    st.session_state[decision_key] = '保留'
                if reason_key not in st.session_state:
                    st.session_state[reason_key] = '内容有价值'
                chosen = c1.radio('处理结果', ['保留', '隐藏'], key=decision_key)
                reason = c2.selectbox('理由', ['内容有价值', '重复/灌水', '与主题无关', '广告/引流', '情绪攻击', '其他'], key=reason_key)
                manual_kw = st.text_input('手动提取关键词（逗号分隔）', value='', key=kw_key)
                b1, b2, b3 = st.columns(3)
                if b1.button('加入白名单', key=white_key):
                    st.session_state.pending_add_white.extend([x.strip() for x in manual_kw.split(',') if x.strip()])
                    st.session_state.review_status[seq] = f'已加入白名单候选：{manual_kw}'
                if b2.button('加入广告词', key=spam_key):
                    st.session_state.pending_add_spam.extend([x.strip() for x in manual_kw.split(',') if x.strip()])
                    st.session_state.review_status[seq] = f'已加入广告词候选：{manual_kw}'
                if b3.button('加入负能量词', key=neg_key):
                    st.session_state.pending_add_neg.extend([x.strip() for x in manual_kw.split(',') if x.strip()])
                    st.session_state.review_status[seq] = f'已加入负能量词候选：{manual_kw}'
                if st.button('提交审核结果', key=submit_key):
                    apply_review(seq, chosen, reason)
                    st.session_state.review_status[seq] = f'已提交：{chosen} · {reason}'
                if st.session_state.review_status.get(seq, ''):
                    st.success(st.session_state.review_status[seq])
        if st.button('更新关键词', key='update_keywords'):
            st.session_state.whitelist = list(dict.fromkeys(st.session_state.whitelist + st.session_state.pending_add_white))
            st.session_state.spam_list = list(dict.fromkeys(st.session_state.spam_list + st.session_state.pending_add_spam))
            st.session_state.neg_list = list(dict.fromkeys(st.session_state.neg_list + st.session_state.pending_add_neg))
            st.session_state.pending_add_white = []
            st.session_state.pending_add_spam = []
            st.session_state.pending_add_neg = []
            st.session_state.page = '关键词筛选'
            st.rerun()
    else:
        st.info('当前没有待人工审核的评论。')

elif st.session_state.page == '最终结果':
    st.header('最终结果')
    df = current_final_df()
    if not df.empty:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric('总评论', len(df))
        c2.metric('保留', int((df['建议操作'] == '保留').sum()))
        c3.metric('隐藏', int((df['建议操作'] == '隐藏').sum()))
        c4.metric('待人工', int((df['人工审核'] == '待人工审核').sum()))
        c5.metric('已审核', int((df['人工审核'] == '已审核').sum()) if '人工审核' in df.columns else 0)
        st.checkbox('确认保存到清理记录', key='confirm_save')
        if st.session_state.confirm_save:
            save_current_batch(df)
            st.success('已保存到清理记录区块。')
        show_cols = [c for c in ['序号', '原始评论', '用户ID', '批次时间', '分类', '建议操作', '理由', '置信度', '人工审核', '人工审核结果', '人工审核理由'] if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
        st.download_button('下载结果 CSV', df[show_cols].to_csv(index=False).encode('utf-8-sig'), 'cleaned_comments.csv', 'text/csv')
    else:
        st.info('还没有清理结果。')

elif st.session_state.page == '清理记录':
    st.header('清理记录')
    if st.session_state.saved_batches:
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
        del_col, view_col = st.columns([1, 4])
        with del_col:
            if st.button('删除此批次', key=f"del_batch_{batch['批次']}", type='secondary'):
                st.session_state.delete_target_batch = batch['批次']
                st.session_state.delete_confirm_checked = False
            if st.session_state.delete_target_batch == batch['批次']:
                st.warning(f"确认删除第 {batch['批次']} 批吗？")
                st.session_state.delete_confirm_checked = st.checkbox(
                    f'我确认要删除第 {batch["批次"]} 批',
                    key=f'confirm_del_{batch["批次"]}',
                    value=st.session_state.delete_confirm_checked
                )
                cdel1, cdel2 = st.columns(2)
                with cdel1:
                    if st.button('确认删除', key=f'confirm_delete_{batch["批次"]}', type='primary'):
                        if st.session_state.delete_confirm_checked:
                            delete_batch(batch['批次'])
                        else:
                            st.error('请先勾选确认框。')
                with cdel2:
                    if st.button('取消', key=f'cancel_delete_{batch["批次"]}'):
                        st.session_state.delete_target_batch = None
                        st.session_state.delete_confirm_checked = False
                        st.rerun()
        with view_col:
            with st.expander(f"展开查看第 {batch['批次']} 批最终结果", expanded=False):
                view_df = pd.DataFrame(batch['data'])
                show_cols = [c for c in ['序号', '原始评论', '用户ID', '批次时间', '分类', '建议操作', '理由', '置信度', '人工审核', '人工审核结果', '人工审核理由'] if c in view_df.columns]
                st.dataframe(view_df[show_cols], use_container_width=True, hide_index=True)
                st.download_button(
                    f"下载第 {batch['批次']} 批 CSV",
                    view_df[show_cols].to_csv(index=False).encode('utf-8-sig'),
                    f"batch_{batch['批次']}.csv",
                    'text/csv'
                )
    else:
        st.info('当前还没有保存的清理记录。')

elif st.session_state.page == '智能洞察':
    st.header('智能洞察')
    df = current_final_df()
    if df.empty:
        st.info('先去“关键词筛选”页跑一批评论。')
    else:
        score, note = batch_health_score(df)
        a, b, c, d = st.columns(4)
        a.metric('批次健康度', f'{score}/100')
        b.metric('治理状态', note)
        c.metric('评论总数', len(df))
        d.metric('已保存批次', len(st.session_state.saved_batches))

        st.markdown('### 1. 批次趋势')
        trend_df = trend_by_batch()
        if not trend_df.empty:
            st.line_chart(trend_df.set_index('批次')[['健康度', '总评论', '保留', '隐藏', '待人工']])
            st.dataframe(trend_df, use_container_width=True, hide_index=True)

        st.markdown('### 2. 分类分布')
        class_dist = df.groupby('分类').size().reset_index(name='数量')
        st.bar_chart(class_dist.set_index('分类')['数量'])

        st.markdown('### 3. 关键词热度')
        counter = Counter()
        for txt in df['原始评论'].astype(str):
            for tok in tokenize(txt):
                if len(tok) > 1 and tok not in white and tok not in spam and tok not in neg:
                    counter[tok] += 1
        hot = pd.DataFrame(counter.most_common(12), columns=['关键词', '次数']) if counter else pd.DataFrame(columns=['关键词', '次数'])
        if not hot.empty:
            st.bar_chart(hot.set_index('关键词')['次数'])
            st.dataframe(hot, use_container_width=True, hide_index=True)

        st.markdown('### 4. 自动发现新词')
        retain_top, spam_top, neg_top = build_keyword_suggestions(df)
        k1, k2, k3 = st.columns(3)
        with k1:
            st.write('**保留候选**')
            for w, n in retain_top:
                st.write(f'- {w} × {n}')
        with k2:
            st.write('**广告候选**')
            for w, n in spam_top:
                st.write(f'- {w} × {n}')
        with k3:
            st.write('**负能量候选**')
            for w, n in neg_top:
                st.write(f'- {w} × {n}')

        st.markdown('### 5. 重复评论聚类')
        clusters = build_cluster_report(df)
        for idx, (key, items) in enumerate(clusters[:8], 1):
            with st.expander(f'聚类 {idx} · {len(items)} 条 · 核心片段：{key}'):
                for item in items[:10]:
                    st.write(f'- {item}')

        st.markdown('### 6. 用户画像')
        profiles = infer_profiles(df)
        if not profiles.empty:
            st.dataframe(profiles, use_container_width=True, hide_index=True)
            st.scatter_chart(profiles.set_index('用户ID')[['评论数', '风险分']])

        st.markdown('### 7. 治理报告')
        report = {
            '总评论': len(df),
            '保留': int((df['建议操作'] == '保留').sum()) if '建议操作' in df.columns else 0,
            '隐藏': int((df['建议操作'] == '隐藏').sum()) if '建议操作' in df.columns else 0,
            '待人工': int((df['人工审核'] == '待人工审核').sum()) if '人工审核' in df.columns else 0,
            '广告引流': int((df['分类'] == '广告引流').sum()) if '分类' in df.columns else 0,
            '负能量': int((df['分类'] == '杠精/负能量').sum()) if '分类' in df.columns else 0,
            '无意义灌水': int((df['分类'] == '无意义灌水').sum()) if '分类' in df.columns else 0,
        }
        st.json(report)
        st.download_button('下载治理报告 CSV', pd.DataFrame([report]).to_csv(index=False).encode('utf-8-sig'), 'governance_report.csv', 'text/csv')

elif st.session_state.page == '周报中心':
    st.header('周报中心')
    df = current_final_df()
    if df.empty:
        st.info('先去“关键词筛选”页跑一批评论。')
    else:
        wb = weekly_report(df)
        st.dataframe(wb, use_container_width=True, hide_index=True)
        st.download_button('下载周报 CSV', wb.to_csv(index=False).encode('utf-8-sig'), 'weekly_report.csv', 'text/csv')
        st.markdown('### 本周摘要')
        st.write('本周系统已经自动完成评论分类、人工复核、风险用户识别、批次趋势跟踪和治理报告汇总。')
        st.write('如果某类评论增长很快，说明关键词和规则需要继续调整。')

else:
    st.header('自动告警')
    df = current_final_df()
    if df.empty:
        st.info('先去“关键词筛选”页跑一批评论。')
    else:
        ar = alert_report(df)
        st.dataframe(ar, use_container_width=True, hide_index=True)
        st.download_button('下载告警 CSV', ar.to_csv(index=False).encode('utf-8-sig'), 'alert_report.csv', 'text/csv')
        st.markdown('### 告警说明')
        st.write('当健康度低于阈值，或广告/负能量/待审比例过高时，会自动触发告警。')
        st.write('你可以通过调整白名单、广告词、负能量词和最短字数来降低告警。')
