import re
import streamlit as st
import pandas as pd
from collections import Counter, defaultdict

st.set_page_config(page_title='闲语清屏 Demo', page_icon='🧹', layout='wide')

if 'page' not in st.session_state:
    st.session_state.page = '首页'
if 'review_items' not in st.session_state:
    st.session_state.review_items = []
if 'whitelist' not in st.session_state:
    st.session_state.whitelist = ['感谢', '支持', '收藏', '学到了', '实用']
if 'spam_list' not in st.session_state:
    st.session_state.spam_list = ['微信', '加我', '私信', '链接', '代理', '互关', '引流']
if 'neg_list' not in st.session_state:
    st.session_state.neg_list = ['笑死', '垃圾', '滚', '废物', '骗', '水']
if 'pending_add_white' not in st.session_state:
    st.session_state.pending_add_white = []
if 'pending_add_spam' not in st.session_state:
    st.session_state.pending_add_spam = []
if 'pending_add_neg' not in st.session_state:
    st.session_state.pending_add_neg = []
if 'cleaned_df' not in st.session_state:
    st.session_state.cleaned_df = pd.DataFrame()
if 'review_decisions' not in st.session_state:
    st.session_state.review_decisions = {}
if 'review_status' not in st.session_state:
    st.session_state.review_status = {}
if 'min_keep_len' not in st.session_state:
    st.session_state.min_keep_len = 5
if 'clean_run_id' not in st.session_state:
    st.session_state.clean_run_id = 0
if 'saved_batches' not in st.session_state:
    st.session_state.saved_batches = []
if 'delete_target_batch' not in st.session_state:
    st.session_state.delete_target_batch = None
if 'delete_confirm_checked' not in st.session_state:
    st.session_state.delete_confirm_checked = False
if 'last_batch_snapshot' not in st.session_state:
    st.session_state.last_batch_snapshot = None

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
    '这也太离谱了吧'
]

def set_page(name):
    st.session_state.page = name

st.sidebar.title('菜单')
st.sidebar.button('首页', key='nav_home', use_container_width=True, on_click=set_page, args=('首页',))
st.sidebar.button('关键词筛选', key='nav_keywords', use_container_width=True, on_click=set_page, args=('关键词筛选',))
st.sidebar.button('人工审核', key='nav_review', use_container_width=True, on_click=set_page, args=('人工审核',))
st.sidebar.button('最终结果', key='nav_result', use_container_width=True, on_click=set_page, args=('最终结果',))
st.sidebar.button('清理记录', key='nav_records', use_container_width=True, on_click=set_page, args=('清理记录',))
st.sidebar.button('智能洞察', key='nav_insight', use_container_width=True, on_click=set_page, args=('智能洞察',))

st.title('闲语清屏')
st.caption('评论清理 + 智能洞察 Demo')

st.sidebar.divider()
st.sidebar.subheader('关键词筛选列表')
white_text = st.sidebar.text_input('白名单关键词（逗号分隔）', value=','.join(st.session_state.whitelist), key='white_input')
spam_text = st.sidebar.text_input('广告关键词（逗号分隔）', value=','.join(st.session_state.spam_list), key='spam_input')
neg_text = st.sidebar.text_input('负能量关键词（逗号分隔）', value=','.join(st.session_state.neg_list), key='neg_input')
keep_len = st.sidebar.slider('保留评论最短字数', 2, 20, st.session_state.min_keep_len, key='keep_len_slider')
st.session_state.min_keep_len = keep_len

white = [x.strip() for x in white_text.split(',') if x.strip()]
spam = [x.strip() for x in spam_text.split(',') if x.strip()]
neg = [x.strip() for x in neg_text.split(',') if x.strip()]

text_input = st.text_area('输入评论，支持每行一条', '\n'.join(sample_comments), height=230)

def normalize(text):
    return re.sub(r'\s+', '', text.strip())

def tokenize(text):
    text = normalize(text)
    parts = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}|\d+|[!?！？。.,，]+', text)
    return parts if parts else [text]

def classify(comment: str):
    t = comment.strip()
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

def extract_signals(comment: str):
    return tokenize(comment)

def run_cleaning():
    rows = []
    raw_lines = [x for x in text_input.splitlines() if x.strip()]
    for i, line in enumerate(raw_lines, start=1):
        label, reason, score = classify(line)
        action = '保留' if label == '优质保留' else '隐藏'
        review_flag = '待人工审核' if label == '待人工' else '无需人工'
        rows.append({
            '序号': i,
            '原始评论': line,
            '分类': label,
            '建议操作': action,
            '理由': reason,
            '置信度': round(score, 2),
            '人工审核': review_flag
        })
    df = pd.DataFrame(rows)
    st.session_state.cleaned_df = df
    st.session_state.review_items = df.loc[df['人工审核'] == '待人工审核', ['序号', '原始评论']].fillna('').to_dict('records') if not df.empty else []
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
    if st.session_state.cleaned_df.empty:
        return
    mask = st.session_state.cleaned_df['序号'] == seq
    if mask.any():
        st.session_state.cleaned_df.loc[mask, '人工审核结果'] = action
        st.session_state.cleaned_df.loc[mask, '人工审核理由'] = reason
        st.session_state.cleaned_df.loc[mask, '人工审核'] = '已审核'
        st.session_state.cleaned_df.loc[mask, '建议操作'] = action
        st.session_state.review_decisions[seq] = {'action': action, 'reason': reason}

def current_final_df():
    if st.session_state.cleaned_df.empty:
        return pd.DataFrame()
    return st.session_state.cleaned_df.copy()

def summarize_batch(df):
    total = len(df)
    keep = int((df['建议操作'] == '保留').sum()) if '建议操作' in df.columns else 0
    hide = int((df['建议操作'] == '隐藏').sum()) if '建议操作' in df.columns else 0
    review = int((df['人工审核'] == '待人工审核').sum()) if '人工审核' in df.columns else 0
    reviewed = int((df['人工审核'] == '已审核').sum()) if '人工审核' in df.columns else 0
    return {'总评论': total, '保留': keep, '隐藏': hide, '待人工': review, '已审核': reviewed}

def save_current_batch(df):
    summary = summarize_batch(df)
    snapshot = {
        '批次': st.session_state.clean_run_id,
        'summary': summary,
        'data': df.fillna('').to_dict('records')
    }
    existing = [b for b in st.session_state.saved_batches if b['批次'] != snapshot['批次']]
    existing.append(snapshot)
    st.session_state.saved_batches = sorted(existing, key=lambda x: x['批次'])
    st.session_state.last_batch_snapshot = snapshot

def delete_batch(batch_id):
    st.session_state.saved_batches = [b for b in st.session_state.saved_batches if b['批次'] != batch_id]
    if st.session_state.delete_target_batch == batch_id:
        st.session_state.delete_target_batch = None
        st.session_state.delete_confirm_checked = False
    st.rerun()

def build_keyword_suggestions(df, topn=8):
    retain_tokens = []
    spam_tokens = []
    neg_tokens = []
    for _, row in df.iterrows():
        toks = extract_signals(str(row.get('原始评论', '')))
        if row.get('建议操作', '') == '保留':
            retain_tokens.extend(toks)
        if row.get('分类', '') == '广告引流':
            spam_tokens.extend(toks)
        if row.get('分类', '') == '杠精/负能量':
            neg_tokens.extend(toks)
    def top(tokens):
        c = Counter([t for t in tokens if len(t) > 1 and t not in white and t not in spam and t not in neg])
        return c.most_common(topn)
    return top(retain_tokens), top(spam_tokens), top(neg_tokens)

def build_cluster_report(df):
    groups = defaultdict(list)
    for _, row in df.iterrows():
        txt = normalize(str(row.get('原始评论', '')))
        key = re.sub(r'\d+', '0', txt)
        key = re.sub(r'[哈嘿哦啊嗯嘛]{2,}', '情绪重复', key)
        key = re.sub(r'[!?！？。.,，]+', '标点', key)
        key = key[:12]
        groups[key].append(row.get('原始评论', ''))
    return sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)

def batch_health_score(df):
    if df.empty:
        return 0, '暂无数据'
    total = len(df)
    spam_rate = float((df['分类'] == '广告引流').sum()) / total if '分类' in df.columns else 0
    neg_rate = float((df['分类'] == '杠精/负能量').sum()) / total if '分类' in df.columns else 0
    review_rate = float((df['人工审核'] == '待人工审核').sum()) / total if '人工审核' in df.columns else 0
    clean = max(0, 100 - int((spam_rate * 45 + neg_rate * 35 + review_rate * 20) * 100))
    note = '健康' if clean >= 80 else '轻度波动' if clean >= 60 else '需要治理'
    return clean, note

if st.session_state.page == '首页':
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('可识别类型', '4+1')
    c2.metric('关键词组', f"{len(white)} / {len(spam)} / {len(neg)}")
    c3.metric('最短字数', st.session_state.min_keep_len)
    c4.metric('当前批次', st.session_state.clean_run_id)
    left, right = st.columns([1.15, 0.85], gap='large')
    with left:
        st.markdown('### 让评论清理更像治理系统')
        st.write('这个版本加入了智能词建议、重复评论聚类、批次健康度与治理报告，目标是从“筛评论工具”升级成“评论治理分析台”。')
        st.write('核心思路不是单纯删，而是先识别模式、再聚合相似内容、最后形成可追踪的治理反馈。')
        st.info('建议先跑一批评论，再去“智能洞察”页查看自动分析结果。')
    with right:
        st.markdown('### 新增能力')
        st.write('• 自动发现新词。')
        st.write('• 相似评论聚类。')
        st.write('• 批次健康度评分。')
        st.write('• 治理报告输出。')
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric('示例评论', len(sample_comments))
    m2.metric('创新模块', '3 个')
    m3.metric('页面入口', '左侧菜单')

elif st.session_state.page == '关键词筛选':
    st.header('关键词筛选')
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric('白名单', len(white))
        st.write(white)
    with col2:
        st.metric('广告词', len(spam))
        st.write(spam)
    with col3:
        st.metric('负能量词', len(neg))
        st.write(neg)
    st.info('点击“开始清理”后，会同时生成初筛结果与后续智能洞察所需的分析数据。')
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
        show_cols = [c for c in ['序号', '原始评论', '分类', '建议操作', '理由', '置信度', '人工审核', '人工审核结果', '人工审核理由'] if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, hide_index=True)
        st.download_button('下载结果 CSV', df[show_cols].to_csv(index=False).encode('utf-8-sig'), 'cleaned_comments.csv', 'text/csv')
    else:
        st.info('还没有清理结果。')

elif st.session_state.page == '清理记录':
    st.header('清理记录')
    if st.session_state.saved_batches:
        batch_labels = [f"第 {b['批次']} 批 · 保留 {b['summary']['保留']} · 隐藏 {b['summary']['隐藏']}" for b in st.session_state.saved_batches]
        selected_label = st.selectbox('记录列表', batch_labels)
        idx = batch_labels.index(selected_label)
        batch = st.session_state.saved_batches[idx]
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
                show_cols = [c for c in ['序号', '原始评论', '分类', '建议操作', '理由', '置信度', '人工审核', '人工审核结果', '人工审核理由'] if c in view_df.columns]
                st.dataframe(view_df[show_cols], use_container_width=True, hide_index=True)
                st.download_button(
                    f"下载第 {batch['批次']} 批 CSV",
                    view_df[show_cols].to_csv(index=False).encode('utf-8-sig'),
                    f"batch_{batch['批次']}.csv",
                    'text/csv'
                )
    else:
        st.info('当前还没有保存的清理记录。')

else:
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

        st.markdown('### 1. 自动发现新词')
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

        st.markdown('### 2. 重复评论聚类')
        clusters = build_cluster_report(df)
        for idx, (key, items) in enumerate(clusters[:8], start=1):
            with st.expander(f'聚类 {idx} · {len(items)} 条 · 核心片段：{key}'):
                for item in items[:10]:
                    st.write(f'- {item}')

        st.markdown('### 3. 治理报告')
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
