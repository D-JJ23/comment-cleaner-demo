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
st.sidebar.button('关键词筛选', use_container_width=True, on_click=set_page, args=('关键词筛选',))
st.sidebar.button('人工审核', use_container_width=True, on_click=set_page, args=('人工审核',))
st.sidebar.button('最终结果', use_container_width=True, on_click=set_page, args=('最终结果',))

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

if st.button('一键清理', type='primary'):
    rows = []
    for i, line in enumerate([x for x in text_input.splitlines() if x.strip()], start=1):
        label, reason = classify(line)
        action = '保留' if label == '优质保留' else '隐藏'
        review_flag = '待人工审核' if label == '待人工' else '无需人工'
        rows.append({
            '序号': i,
            '评论': line,
            '分类': label,
            '建议操作': action,
            '理由': reason,
            '人工审核': review_flag
        })

    if rows:
        df = pd.DataFrame(rows)
        st.session_state.cleaned_df = df
        st.session_state.review_items = df[df['人工审核'] == '待人工审核'][['序号', '评论']].to_dict('records')

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
    st.info('在这里修改左侧关键词后，点击菜单切换或“一键清理”即可生效。')
    if st.button('一键清理', type='primary'):
        st.session_state.page = '最终结果'
        st.rerun()

elif st.session_state.page == '人工审核':
    st.header('人工审核')
    if st.session_state.review_items:
        for idx, item in enumerate(st.session_state.review_items):
            with st.expander(f"评论 {item['序号']} · {item['评论'][:30]}"):
                c1, c2 = st.columns([1, 1])
                chosen = c1.radio('处理结果', ['保留', '隐藏'], key=f'action_{item["序号"]}_{idx}')
                reason = c2.selectbox('理由', ['内容有价值', '重复/灌水', '与主题无关', '广告/引流', '情绪攻击', '其他'], key=f'reason_{item["序号"]}_{idx}')
                manual_kw = st.text_input('手动提取关键词（逗号分隔）', value='', key=f'kw_{item["序号"]}_{idx}')
                b1, b2, b3 = st.columns(3)
                if b1.button('加入白名单', key=f'white_{item["序号"]}_{idx}'):
                    st.session_state.pending_add_white.extend([x.strip() for x in manual_kw.split(',') if x.strip()])
                    st.success('已加入待更新白名单')
                if b2.button('加入广告词', key=f'spam_{item["序号"]}_{idx}'):
                    st.session_state.pending_add_spam.extend([x.strip() for x in manual_kw.split(',') if x.strip()])
                    st.success('已加入待更新广告词')
                if b3.button('加入负能量词', key=f'neg_{item["序号"]}_{idx}'):
                    st.session_state.pending_add_neg.extend([x.strip() for x in manual_kw.split(',') if x.strip()])
                    st.success('已加入待更新负能量词')
                if st.button('提交审核结果', key=f'submit_{item["序号"]}_{idx}'):
                    st.success(f'已提交：{chosen} · {reason}')

        if st.button('更新关键词'):
            st.session_state.whitelist = list(dict.fromkeys(st.session_state.whitelist + st.session_state.pending_add_white))
            st.session_state.spam_list = list(dict.fromkeys(st.session_state.spam_list + st.session_state.pending_add_spam))
            st.session_state.neg_list = list(dict.fromkeys(st.session_state.neg_list + st.session_state.pending_add_neg))
            st.session_state.pending_add_white = []
            st.session_state.pending_add_spam = []
            st.session_state.pending_add_neg = []
            st.session_state.page = '关键词筛选'
            st.rerun()
    else:
        st.info('当前没有待人工审核的评论。先到“关键词筛选”页点击“一键清理”。')

else:
    st.header('最终结果')
    if not st.session_state.cleaned_df.empty:
        df = st.session_state.cleaned_df.copy()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('总评论', len(df))
        c2.metric('保留', int((df['建议操作'] == '保留').sum()))
        c3.metric('隐藏', int((df['建议操作'] == '隐藏').sum()))
        c4.metric('待人工', int((df['人工审核'] == '待人工审核').sum()))
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button('下载结果 CSV', df.to_csv(index=False).encode('utf-8-sig'), 'cleaned_comments.csv', 'text/csv')
    else:
        st.info('还没有清理结果，先去“关键词筛选”页点击“一键清理”。')
