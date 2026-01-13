import pandas as pd
import streamlit as st
import re
from collections import Counter

# 设置页面宽度和标题
st.set_page_config(page_title="酒精笔卖点渗透看板", layout="wide")

# --- 1. 极其基础的分词函数 ---
def get_title_keywords(title):
    # \b\w{3,}\b 匹配长度大于等于3的单词或数字（保留120, 72等规格）
    words = re.findall(r'\b\w{3,}\b', str(title).lower())
    
    # 仅保留最基础的语法虚词
    stop_words = {'and', 'the', 'with', 'for', 'based', 'from', 'this', 'that', 'these', 'those'}
    
    # 标题内部去重：一个 ASIN 标题里出现多次同样的词只记一次
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

    # --- A. 标题端统计 (按 ASIN 去重) ---
    # 每个 ASIN 仅取其第一行 Title 进行词频分析
    asin_level_df = df.groupby('ASIN')['Title'].first().reset_index()
    asin_level_df['kw_list'] = asin_level_df['Title'].apply(get_title_keywords)
    
    all_title_words = []
    for ks in asin_level_df['kw_list']:
        all_title_words.extend(ks)
    
    kw_counts = Counter(all_title_words)
    # 取标题中出现频率最高的前 100 个关键词
    top_kws = [item[0] for item in kw_counts.most_common(100)]

    # --- B. 评论端统计 (按 评论行数 统计) ---
# --- 核心分析循环修改 ---
    analysis_data = []
    for kw, synonyms in EXTENDED_MAPPING.items():
        # 1. 找到标题里包含该核心词的 ASIN 列表
        pattern_title = fr'\b{re.escape(kw)}\b'
        relevant_asins = asin_level_df[asin_level_df['Title'].str.contains(pattern_title, na=False)]['ASIN'].tolist()
        
        title_mentions = len(relevant_asins) # 标题渗透数
        title_penetration = (title_mentions / total_asins) * 100
        
        # 2. 仅针对这些 ASIN 的评论进行分析
        if title_mentions > 0:
            relevant_reviews_df = df[df['ASIN'].isin(relevant_asins)]
            specific_total_reviews = len(relevant_reviews_df) # 该卖点关联的总评论分母
            
            # 匹配延伸词库（语义丛）
            pattern_review = r'\b(' + '|'.join([re.escape(w) for w in synonyms]) + r')\b'
            review_mentions = relevant_reviews_df['Review Content'].str.contains(pattern_review, na=False).sum()
            
            # 关键修改：除以该卖点关联的评论总数
            review_echo_rate = (review_mentions / specific_total_reviews) * 100
        else:
            review_mentions = 0
            review_echo_rate = 0
            specific_total_reviews = 0

        analysis_data.append({
            "关键词": kw,
            "标题提及ASIN数": title_mentions,
            "标题渗透率 (%)": round(title_penetration, 2),
            "关联评论总数": specific_total_reviews, # 新增辅助列，方便排查
            "语义命中次数": review_mentions,
            "评论回声率 (%)": round(review_echo_rate, 2),
            "心智转化比": round(review_echo_rate / (title_penetration if title_penetration > 0 else 1), 2)
        })

    result_df = pd.DataFrame(analysis_data)
    # 计算转化效率：回声率 / 渗透率
    result_df['心智转化比'] = (result_df['评论回声率 (%)'] / result_df['标题渗透率 (%)']).round(2)
    
    return result_df, total_asins, total_reviews

# --- 3. Streamlit 展示层 ---
st.title("🎯 卖点回声分析看板")
st.markdown("""
通过对比 **商家宣传（标题）** 与 **用户复述（评论）**，识别真实的市场心智。
- **标题渗透率**: 市场上有多少比例的 ASIN 在卖这个点。
- **评论回声率**: 有多少比例的用户评论在反馈这个点。
""")

uploaded_file = st.file_uploader("上传您的数据文件 (Excel 或 CSV)", type=['csv', 'xlsx'])

if uploaded_file:
    # 根据后缀读取数据
    if uploaded_file.name.endswith('.csv'):
        df_input = pd.read_csv(uploaded_file)
    else:
        df_input = pd.read_excel(uploaded_file)
    
    # 执行分析
    res_df, total_a, total_r = analyze_market_echo(df_input)
    
    if not res_df.empty:
        # 指标总览卡片
        m1, m2 = st.columns(2)
        m1.metric("分析 ASIN 总数", total_a)
        m2.metric("分析评论总条数", total_r)

        st.divider()

        # 数据表格展示
        st.subheader("📊 关键词卖点转化清单")
        
        # 默认按评论回声率排序
        res_df = res_df.sort_values("评论回声率 (%)", ascending=False)
        
        # 应用背景渐变色，增强可读性
        styled_df = res_df.style.background_gradient(
            subset=['标题渗透率 (%)', '评论回声率 (%)', '心智转化比'], 
            cmap='GnBu'
        )
        
        st.dataframe(styled_df, use_container_width=True)
        
        st.info("""
        **指标解释：**
        1. **标题渗透率 (%)**: 酒精笔市场中，有多少卖家在标题里使用了这个词。
        2. **评论回声率 (%)**: 买了酒精笔的用户，有多少人在评论里提到了这个词。
        3. **心智转化比**: 评论回声率 ÷ 标题渗透率。数值越高，代表这个词对用户的心智触达越强。
        """)
else:
    st.warning("👈 请先上传数据文件进行分析。")
