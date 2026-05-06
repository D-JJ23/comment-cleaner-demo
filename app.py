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
if 'white_text' not in st.session_state:
    st.session_state.white_text = ','.join(st.session_state.whitelist)
if 'spam_text' not in st.session_state:
    st.session_state.spam_text = ','.join(st.session_state.spam_list)
if 'neg_text' not in st.session_state:
    st.session_state.neg_text = ','.join(st.session_state.neg_list)

st.sidebar.header('规则设置')
min_len = st.sidebar.slider('最短有效字数', 2, 20, 5)
text_input = st.text_area('输入评论，支持每行一条', '
'.join(sample_comments), height=220)

st.sidebar.subheader('关键词筛选列表')
st.session_state.white_text = st.sidebar.text_input('白名单关键词（逗号分隔）', value=st.session_state.white_text, key='white_input')
st.session_state.spam_text = st.sidebar.text_input('广告关键词（逗号分隔）', value=st.session_state.spam_text, key='spam_input')
st.session_state.neg_text = st.sidebar.text_input('负能量关键词（逗号分隔）', value=st.session_state.neg_text, key='neg_input')
