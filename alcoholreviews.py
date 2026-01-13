import pandas as pd
import streamlit as st
import re
from collections import Counter

# 设置页面宽度和标题
st.set_page_config(page_title="酒精笔卖点渗透看板", layout="wide")

# --- 1. 极其基础的分词函数 ---
def get_title_keywords(title):
    # \b\w{3,}\b 匹配长度大于等于3的单词或数字
    words = re.findall(r'\b\w{3,}\b', str(title).lower())
    
    # 基础语法虚词
    stop_words = {'and', 'the', 'with', 'for', 'based', 'from', 'this', 'that', 'these', 'those'}
    
    # 标题内部去重
    return list(set([w for w in words if w not in stop_words]))

# --- 2. 核心分析逻辑 ---
def analyze_market_echo(df):
    # 基础列名校验
    required_cols = ['ASIN', 'Title', 'Review Content']
    if not all(col in df.columns for col in required_cols):
        st.error(f"数据缺失关键列，请确保文件包含: {required_cols}")
        return pd.DataFrame(), 0, 0

    # 预处理缺失值
    df['Title'] = df['Title'].fillna('')
    df['Review Content'] = df['Review Content'].fillna('')
    
    total_asins = df['ASIN'].nunique()
    total_reviews = len(df)

    # --- A. 标题端统计 (按 ASIN 提取关键词) ---
    asin_level_df = df.groupby('ASIN')['Title'].first().reset_index()
    asin_level_df['kw_list'] = asin_level_df['Title'].apply(get_title_keywords)
    
    all_title_words = []
    for ks in asin_level_df['kw_list']:
        all_title_words.extend(ks)
    
    kw_counts = Counter(all_title_words)
    # 取标题中出现频率最高的前 100 个关键词作为分析对象
    top_kws = [item[0] for item in kw_counts.most_common(100)]

    # --- B. 核心分析循环 (精确匹配分析) ---
    analysis_data = []
    
    for kw in top_kws:
        # 1. 找到标题里包含该关键词的 ASIN 列表
        # 使用 \b 确保精确匹配单词
        pattern = fr'\b{re.escape(kw)}\b'
        
        # 这里的 boolean mask 用于找出哪些 ASIN 的标题含此词
        has_kw_mask = asin_level_df['Title'].str.contains(pattern, case=False, na=False)
        relevant_asins = asin_level_df[has_kw_mask]['ASIN'].unique()
        
        title_mentions = len(relevant_asins) 
        title_penetration = (title_mentions / total_asins) * 100
        
        # 2. 针对这些 ASIN 的评论进行分析
        if title_mentions > 0:
            # 筛选出属于这些 ASIN 的所有评论行
            relevant_reviews_df = df[df['ASIN'].isin(relevant_asins)]
            specific_total_reviews = len(relevant_reviews_df) # 局部评论总数 (分母)
            
            # 在这些评论中，提到该关键词的次数 (分子)
            review_mentions = relevant_reviews_df['Review Content'].str.contains(pattern, case=False, na=False).sum()
            
            # 计算回声率：提到的评论数 / 该卖点关联的总评论数
            review_echo_rate = (review_mentions / specific_total_reviews) * 100
        else:
            review_mentions = 0
            review_echo_rate = 0
            specific_total_reviews = 0

        # 计算心智转化比 (分母保护)
        conversion_ratio = round(review_echo_rate / title_penetration, 2) if title_penetration > 0 else 0

        analysis_data.append({
            "关键词": kw,
            "标题提及ASIN数": title_mentions,
            "标题渗透率 (%)": round(title_penetration, 2),
            "关联评论总数 (分母)": specific_total_reviews,
            "评论提及次数 (分子)": review_mentions,
            "评论回声率 (%)": round(review_echo_rate, 2),
            "心智转化比": conversion_ratio
        })

    result_df = pd.DataFrame(analysis_data)
    return result_df, total_asins, total_reviews

# --- 3. Streamlit 展示层 ---
st.title("🎯 卖点回声分析看板 (精确匹配版)")
st.markdown("""
通过对比 **商家宣传（标题关键词）** 与 **用户复述（评论关键词）**，识别真实的卖点响应。
- **标题渗透率**: 市场上有多大比例的 ASIN 在标题里提到了这个词。
- **评论回声率**: 在**提到了该词的商品**中，有多大比例的评论也提到了这个词。
""")

uploaded_file = st.file_uploader("上传您的数据文件 (Excel 或 CSV)", type=['csv', 'xlsx'])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df_input = pd.read_csv(uploaded_file)
    else:
        df_input = pd.read_excel(uploaded_file)
    
    res_df, total_a, total_r = analyze_market_echo(df_input)
    
    if not res_df.empty:
        m1, m2 = st.columns(2)
        m1.metric("分析 ASIN 总数", total_a)
        m2.metric("分析评论总条数", total_r)

        st.divider()

        st.subheader("📊 关键词卖点转化清单")
        
        # 默认按评论回声率排序
        res_df = res_df.sort_values("评论回声率 (%)", ascending=False)
        
        # 背景渐变美化
        styled_df = res_df.style.background_gradient(
            subset=['标题渗透率 (%)', '评论回声率 (%)', '心智转化比'], 
            cmap='GnBu'
        )
        
        st.dataframe(styled_df, use_container_width=True)

else:
    st.warning("👈 请先上传数据文件进行分析。")
