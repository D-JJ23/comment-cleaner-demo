import re
import streamlit as st
import pandas as pd

st.set_page_config(page_title='闲语清屏 Demo', page_icon='🧹', layout='wide')

if 'page' not in st.session_state:
    st.session_state.page = '关键词筛选'
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
st.sidebar.button('关键词筛选', key='nav_keywords', use_container_width=True, on_click=set_page, args=('关键词筛选',))
st.sidebar.button('人工审核', key='nav_review', use_container_width=True, on_click=set_page, args=('人工审核',))
st.sidebar.button('最终结果', key='nav_result', use_container_width=True, on_click=set_page, args=('最终结果',))

st.title('闲语清屏')
st.caption('社交社区无关评论一键清理 Demo')
st.write('这是一款轻量评论清理 Demo，可识别无意义灌水、无关闲聊、广告引流、负能量杠精评论，并支持白名单保留优质评论。')

st.sidebar.divider()
st.sidebar.subheader('关键词筛选列表')
white_text = st.sidebar.text_input('白名单关键词（逗号分隔）', value=','.join(st.session_state.whitelist), key='white_input')
spam_text = st.sidebar.text_input('广告关键词（逗号分隔）', value=','.join(st.session_state.spam_list), key='spam_input')
neg_text = st.sidebar.text_input('负能量关键词（逗号分隔）', value=','.join(st.session_state.neg_list), key='neg_input')

white = [x.strip() for x in white_text.split(',') if x.strip()]
spam = [x.strip() for x in spam_text.split(',') if x.strip()]
neg = [x.strip() for x in neg_text.split(',') if x.strip()]

st.sidebar.caption(f'白名单：{len(white)} 条 · 广告词：{len(spam)} 条 · 负能量词：{len(neg)} 条')

text_input = st.text_area('输入评论，支持每行一条', '\n'.join(sample_comments), height=220)
min_len = 5

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
    if len(re.sub(r'\s+', '', t)) < min_len:
        return '无意义灌水', '过短'
    if re.fullmatch(r'[哈嘿哦啊嗯嘛~!！?.。，,。]+', t):
        return '无意义灌水', '纯情绪/口水'
    if re.search(r'\d{5,}', t):
        return '广告引流', '疑似号码'
    return '待人工', '需人工复核'

def run_cleaning():
    rows = []
    for i, line in enumerate([x for x in text_input.splitlines() if x.strip()], start=1):
        label, reason = classify(line)
        action = '保留' if label == '优质保留' else '隐藏'
        review_flag = '待人工审核' if label == '待人工' else '无需人工'
        rows.append({'序号': i, '评论': line, '分类': label, '建议操作': action, '理由': reason, '人工审核': review_flag})
    st.session_state.cleaned_df = pd.DataFrame(rows)
    if not st.session_state.cleaned_df.empty:
        st.session_state.review_items = st.session_state.cleaned_df[st.session_state.cleaned_df['人工审核'] == '待人工审核'][['序号', '评论']].to_dict('records')
    else:
        st.session_state.review_items = []

if st.session_state.page == '关键词筛选':
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
    st.info('在这里修改左侧关键词后，点击“开始清理”即可进入清理并生效。')
    if st.button('开始清理', key='clean_keywords', type='primary'):
        run_cleaning()
        st.session_state.page = '最终结果'
        st.rerun()

elif st.session_state.page == '人工审核':
    st.header('人工审核')
    if st.session_state.review_items:
        for idx, item in enumerate(st.session_state.review_items):
            seq = item['序号']
            with st.expander(f"评论 {seq} · {item['评论'][:30]}"):
                c1, c2 = st.columns([1, 1])
                decision_key = f'decision_{seq}'
                reason_key = f'review_reason_{seq}'
                if decision_key not in st.session_state:
                    st.session_state[decision_key] = '保留'
                if reason_key not in st.session_state:
                    st.session_state[reason_key] = '内容有价值'
                chosen = c1.radio('处理结果', ['保留', '隐藏'], key=decision_key)
                reason = c2.selectbox('理由', ['内容有价值', '重复/灌水', '与主题无关', '广告/引流', '情绪攻击', '其他'], key=reason_key)
                manual_kw = st.text_input('手动提取关键词（逗号分隔）', value='', key=f'kw_{seq}')
                b1, b2, b3 = st.columns(3)
                if b1.button('加入白名单', key=f'white_{seq}'):
                    st.session_state.pending_add_white.extend([x.strip() for x in manual_kw.split(',') if x.strip()])
                    st.session_state.review_status[seq] = f'已加入白名单候选：{manual_kw}'
                if b2.button('加入广告词', key=f'spam_{seq}'):
                    st.session_state.pending_add_spam.extend([x.strip() for x in manual_kw.split(',') if x.strip()])
                    st.session_state.review_status[seq] = f'已加入广告词候选：{manual_kw}'
                if b3.button('加入负能量词', key=f'neg_{seq}'):
                    st.session_state.pending_add_neg.extend([x.strip() for x in manual_kw.split(',') if x.strip()])
                    st.session_state.review_status[seq] = f'已加入负能量词候选：{manual_kw}'
                if st.button('提交审核结果', key=f'submit_{seq}'):
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

else:
    st.header('最终结果')
    if not st.session_state.cleaned_df.empty:
        df = st.session_state.cleaned_df.copy()
        if st.session_state.review_decisions:
            for seq, info in st.session_state.review_decisions.items():
                mask = df['序号'] == seq
                if mask.any():
                    df.loc[mask, '人工审核结果'] = info['action']
                    df.loc[mask, '人工审核理由'] = info['reason']
                    if in
