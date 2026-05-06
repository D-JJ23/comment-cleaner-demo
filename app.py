import re
import streamlit as st
import pandas as pd

st.set_page_config(page_title='闲语清屏 Demo', page_icon='🧹', layout='wide')

st.title('闲语清屏')
st.caption('社交社区无关评论一键清理 Demo')
st.write('这是一款轻量评论清理 Demo，可识别无意义灌水、无关闲聊、广告引流、负能量杠精评论，并支持白名单保留优质评论。')

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

if 'review_items' not in st.session_state:
    st.session_state.review_items = []
if 'note' not in st.session_state:
    st.session_state.note = ''

st.sidebar.header('规则设置')
min_len = st.sidebar.slider('最短有效字数', 2, 20, 5)
keep_white = st.sidebar.text_input('白名单关键词（逗号分隔）', '感谢,支持,收藏,学到了,实用')
spam_kw = st.sidebar.text_input('广告关键词（逗号分隔）', '微信,加我,私信,链接,代理,互关,引流')
neg_kw = st.sidebar.text_input('负能量关键词（逗号分隔）', '笑死,垃圾,滚,废物,骗,水')
extract_len = st.sidebar.slider('自动截取字数', 4, 20, 8)
auto_kw = st.sidebar.checkbox('自动提取三类关键词', value=True)

text_input = st.text_area('输入评论，支持每行一条', '\n'.join(sample_comments), height=220)

white = [x.strip() for x in keep_white.split(',') if x.strip()]
spam = [x.strip() for x in spam_kw.split(',') if x.strip()]
neg = [x.strip() for x in neg_kw.split(',') if x.strip()]

def classify(comment: str):
    t = comment.strip()
    if not t:
        return '空白', 'gray', '空行'
    if any(k in t for k in white):
        return '优质保留', 'green', '命中白名单'
    if any(k in t for k in spam):
        return '广告引流', 'red', '命中广告词'
    if any(k in t for k in neg):
        return '杠精/负能量', 'orange', '命中负面词'
    if len(re.sub(r'\s+', '', t)) < min_len:
        return '无意义灌水', 'gray', '过短'
    if re.fullmatch(r'[哈嘿哦啊嗯嘛~!！?.。，,。]+', t):
        return '无意义灌水', 'gray', '纯情绪/口水'
    if re.search(r'\d{5,}', t):
        return '广告引流', 'red', '疑似号码'
    return '待人工', 'blue', '需人工复核'

def extract_keywords(text: str, n: int):
    t = re.sub(r'\s+', '', text)
    if not t:
        return []
    chunks = []
    if len(t) <= n:
        chunks.append(t)
    else:
        for i in range(0, len(t), n):
            chunk = t[i:i+n]
            if chunk:
                chunks.append(chunk)
    return chunks[:3]

if st.button('一键清理', type='primary'):
    rows = []
    for i, line in enumerate([x for x in text_input.splitlines() if x.strip()], start=1):
        label, color, reason = classify(line)
        action = '保留' if label == '优质保留' else '隐藏'
        review_flag = '待人工审核' if label == '待人工' else '无需人工'
        kw = extract_keywords(line, extract_len) if auto_kw else []
        rows.append({
            '序号': i,
            '评论': line,
            '分类': label,
            '建议操作': action,
            '理由': reason,
            '人工审核': review_flag,
            '提取关键词1': kw[0] if len(kw) > 0 else '',
            '提取关键词2': kw[1] if len(kw) > 1 else '',
            '提取关键词3': kw[2] if len(kw) > 2 else ''
        })

    if rows:
        df = pd.DataFrame(rows)
        st.session_state.review_items = df[df['人工审核'] == '待人工审核'].to_dict('records')

        c1, c2, c3, c4 = st.columns(4)
        c1.metric('总评论', len(df))
        c2.metric('保留', int((df['建议操作'] == '保留').sum()))
        c3.metric('隐藏', int((df['建议操作'] == '隐藏').sum()))
        c4.metric('待人工', int((df['人工审核'] == '待人工审核').sum()))

        st.subheader('清理结果')
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            '下载结果 CSV',
            df.to_csv(index=False).encode('utf-8-sig'),
            'cleaned_comments.csv',
            'text/csv'
        )
    else:
        st.warning('没有可处理的评论。')
else:
    st.info('点击「一键清理」开始演示。')

st.divider()
st.subheader('人工审核区域')
st.write('这里仅展示“待人工审核”的评论，并支持保留/隐藏、理由和可选关键词提取。')

review_source = st.session_state.review_items
if review_source:
    for idx, item in enumerate(review_source):
        with st.expander(f"评论 {item['序号']} · {item['评论'][:30]}"):
            c1, c2 = st.columns([1, 1])
            chosen = c1.radio(
                '处理结果',
                ['保留', '隐藏'],
                key=f"review_action_{item['序号']}_{idx}"
            )
            reason = c2.selectbox(
                '理由',
                ['内容有价值', '重复/灌水', '与主题无关', '广告/引流', '情绪攻击', '其他'],
                key=f"review_reason_{item['序号']}_{idx}"
            )
            extra = st.text_input(
                '补充说明',
                value=item.get('评论', '')[:extract_len] if auto_kw else '',
                key=f"review_extra_{item['序号']}_{idx}"
            )
            if st.button('提交审核结果', key=f"submit_{item['序号']}_{idx}"):
                st.success(f"已提交：{chosen} · {reason} · {extra}")
else:
    st.info('当前没有待人工审核的评论。先点击上方“一键清理”生成结果。')
