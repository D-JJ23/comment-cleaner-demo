import re
import streamlit as st
import pandas as pd

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
if 'clean_records' not in st.session_state:
    st.session_state.clean_records = []
if 'confirm_save' not in st.session_state:
    st.session_state.confirm_save = False

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
    '作者讲得很清楚，支持'
]

def set_page(name):
    st.session_state.page = name

st.sidebar.title('菜单')
st.sidebar.button('首页', key='nav_home', use_container_width=True, on_click=set_page, args=('首页',))
st.sidebar.button('关键词筛选', key='nav_keywords', use_container_width=True, on_click=set_page, args=('关键词筛选',))
st.sidebar.button('人工审核', key='nav_review', use_container_width=True, on_click=set_page, args=('人工审核',))
st.sidebar.button('最终结果', key='nav_result', use_container_width=True, on_click=set_page, args=('最终结果',))
st.sidebar.button('清理记录', key='nav_records', use_container_width=True, on_click=set_page, args=('清理记录',))

st.title('闲语清屏')
st.caption('社交社区无关评论一键清理 Demo')

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

text_input = st.text_area('输入评论，支持每行一条', '\n'.join(sample_comments), height=220)

def classify(comment: str):
    t = comment.strip()
    if not t:
        return '空白', '空行'
    if any(k in t for k in white):
        return '优质保留', '命中白名单'
    if any(k in t for k in spam):
        return '广告引流', '命中广告词'
    if any(k in t for k in neg):
        return '杠精/负能量', '命中负面词'
    if len(re.sub(r'\s+', '', t)) < st.session_state.min_keep_len:
        return '无意义灌水', '过短'
    if re.fullmatch(r'[哈嘿哦啊嗯嘛~!！?.。，,。]+', t):
        return '无意义灌水', '纯情绪/口水'
    if re.search(r'\d{5,}', t):
        return '广告引流', '疑似号码'
    return '待人工', '需人工复核'

def make_display_row(comment: str, label: str):
    if label == '优质保留':
        return f"{comment} → **{comment}**"
    return f"{comment} → ~~{comment}~~"

def run_cleaning():
    rows = []
    records = []
    for i, line in enumerate([x for x in text_input.splitlines() if x.strip()], start=1):
        label, reason = classify(line)
        action = '保留' if label == '优质保留' else '隐藏'
        review_flag = '待人工审核' if label == '待人工' else '无需人工'
        display_text = make_display_row(line, label)
        row = {
            '序号': i,
            '原始评论': line,
            '显示记录': display_text,
            '分类': label,
            '建议操作': action,
            '理由': reason,
            '人工审核': review_flag
        }
        rows.append(row)
        records.append({
            '序号': i,
            '原始评论': line,
            '显示记录': display_text,
            '分类': label,
            '建议操作': action,
            '理由': reason,
            '人工审核': review_flag
        })
    st.session_state.cleaned_df = pd.DataFrame(rows)
    st.session_state.clean_records = records
    if not st.session_state.cleaned_df.empty:
        st.session_state.review_items = st.session_state.cleaned_df[st.session_state.cleaned_df['人工审核'] == '待人工审核'][['序号', '原始评论']].to_dict('records')
    else:
        st.session_state.review_items = []
    st.session_state.clean_run_id += 1
    st.session_state.review_status = {}
    st.session_state.review_decisions = {}
    st.session_state.pending_add_white = []
    st.session_state.pending_add_spam = []
    st.session_state.pending_add_neg = []
    st.session_state.confirm_save = False

def current_final_df():
    if st.session_state.cleaned_df.empty:
        return pd.DataFrame()
    df = st.session_state.cleaned_df.copy()
    if st.session_state.review_decisions:
        for seq, info in st.session_state.review_decisions.items():
            mask = df['序号'] == seq
            if mask.any():
                df.loc[mask, '人工审核结果'] = info['action']
                df.loc[mask, '人工审核理由'] = info['reason']
                df.loc[mask, '人工审核'] = '已审核'
                if info['action'] == '保留':
                    df.loc[mask, '建议操作'] = '保留'
                elif info['action'] == '隐藏':
                    df.loc[mask, '建议操作'] = '隐藏'
                original = df.loc[mask, '原始评论'].iloc[0]
                df.loc[mask, '显示记录'] = f"{original} → {'**' + original + '**' if info['action'] == '保留' else '~~' + original + '~~'}"
    return df

if st.session_state.page == '首页':
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('可识别类型', '4+1')
    c2.metric('关键词组', f"{len(white)} / {len(spam)} / {len(neg)}")
    c3.metric('最短字数', st.session_state.min_keep_len)
    c4.metric('当前批次', st.session_state.clean_run_id)
    left, right = st.columns([1.15, 0.85], gap='large')
    with left:
        st.markdown('### 让评论清理先有个“门面”')
        st.write('这是一款轻量评论清理 Demo，适合演示社交社区里常见的无意义灌水、无关闲聊、广告引流、负能量对喷与人工复核流程。')
        st.write('你可以先把它当作一个首页：看清能力、看清规则、看清流程，再切换到左侧功能页完成真正的筛选、审核与输出。')
        col_a, col_b = st.columns(2)
        with col_a:
            st.success('支持左侧关键词动态维护')
            st.info('支持最短字数阈值调节')
        with col_b:
            st.success('支持人工审核结果回写')
            st.info('支持清理记录存档')
    with right:
        st.markdown('### 功能概览')
        st.write('• 关键词筛选：维护白名单、广告词、负能量词。')
        st.write('• 人工审核：逐条处理待审评论，并把结果写回。')
        st.write('• 最终结果：确认保存为清理记录。')
        st.markdown('### 演示样例')
        for s in sample_comments[:5]:
            st.code(s, language='text')
    st.divider()
    c5, c6, c7 = st.columns(3)
    c5.metric('首页状态', '已启用')
    c6.metric('示例评论', len(sample_comments))
    c7.metric('页面入口', '左侧菜单')

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
    st.info('这里可以调节“保留评论最短字数”，修改左侧关键词后点击“开始清理”即可进入初筛。')
    if st.button('开始清理', key=f'clean_keywords_{st.session_state.clean_run_id}', type='primary'):
        run_cleaning()
        st.session_state.page = '初筛结果'
        st.rerun()

elif st.session_state.page == '人工审核':
    st.header('人工审核')
    st.caption(f'当前清理批次：{st.session_state.clean_run_id}')
    if st.session_state.review_items:
        for item in st.session_state.review_items:
            seq = item['序号']
            decision_key = f'decision_{st.session_state.clean_run_id}_{seq}'
            reason_key = f'review_reason_{st.session_state.clean_run_id}_{seq}'
            kw_key = f'kw_{st.session_state.clean_run_id}_{seq}'
            submit_key = f'submit_{st.session_state.clean_run_id}_{seq}'
            white_key = f'white_{st.session_state.clean_run_id}_{seq}'
            spam_key = f'spam_{st.session_state.clean_run_id}_{seq}'
            neg_key = f'neg_{st.session_state.clean_run_id}_{seq}'
            with st.expander(f"评论 {seq} · {item['原始评论'][:30]}"):
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
                    st.session_state.review_decisions[seq] = {'action': chosen, 'reason': reason}
                    st.session_state.review_status[seq] = f'已提交：{chosen} · {reason}'
                status = st.session_state.review_status.get(seq, '')
                if status:
                    st.success(status)
                if seq in st.session_state.review_decisions:
                    d = st.session_state.review_decisions[seq]
                    st.info(f"当前记录：{d['action']} · {d['reason']}")
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
        st.info('当前没有待人工审核的评论。先到“关键词筛选”页点击“开始清理”。')

elif st.session_state.page == '初筛结果':
    st.header('初筛结果')
    df = st.session_state.cleaned_df.copy()
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('总评论', len(df))
        c2.metric('保留', int((df['建议操作'] == '保留').sum()))
        c3.metric('隐藏', int((df['建议操作'] == '隐藏').sum()))
        c4.metric('待人工', int((df['人工审核'] == '待人工审核').sum()))
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button('下载初筛结果 CSV', df.to_csv(index=False).encode('utf-8-sig'), 'screened_comments.csv', 'text/csv')
    else:
        st.info('还没有初筛结果。')

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
            st.session_state.clean_records = df[['原始评论', '显示记录', '分类', '建议操作', '理由']].to_dict('records')
            st.success('已保存到清理记录区块。')
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button('下载结果 CSV', df.to_csv(index=False).encode('utf-8-sig'), 'cleaned_comments.csv', 'text/csv')
    else:
        st.info('还没有清理结果，先去“关键词筛选”页点击“开始清理”。')

else:
    st.header('清理记录')
    if st.session_state.clean_records:
        st.write('以下为已保存的清理记录。格式：左侧原始文本 → 右侧处理结果。')
        for idx, rec in enumerate(st.session_state.clean_records):
            st.markdown(f"{idx+1}. {rec['原始评论']} → {rec['显示记录']}")
        options = [f"记录 {i+1}" for i in range(len(st.session_state.clean_records))]
        selected = st.selectbox('查看保存的记录列表', options)
        if selected:
            i = options.index(selected)
            rec = st.session_state.clean_records[i]
            st.code(f"{rec['原始评论']} → {rec['显示记录']}", language='text')
    else:
        st.info('当前还没有保存的清理记录。去“最终结果”页勾选确认保存。')
