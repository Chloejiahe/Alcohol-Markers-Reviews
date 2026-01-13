import pandas as pd
import streamlit as st
import plotly.express as px
import re
from collections import Counter

# 设置页面宽度和标题
st.set_page_config(page_title="酒精笔卖点渗透看板", layout="wide")

# --- 1. 极其基础的分词函数 ---
def get_title_keywords(title):
    # \b\w{3,}\b 表示匹配长度大于等于3的单词或数字
    words = re.findall(r'\b\w{3,}\b', str(title).lower())
    
    # 仅保留最基础的语法虚词，不干预业务词汇
    stop_words = {'and', 'the', 'with', 'for', 'based', 'from', 'this', 'that', 'these', 'those'}
    
    # 标题内部去重：一个标题里出现两次同样的词，对该 ASIN 只记一次
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

    # --- A. 标题统计 (ASIN去重) ---
    # 每个 ASIN 只取第一条标题记录，防止评论行数干扰标题词频
    asin_level_df = df.groupby('ASIN')['Title'].first().reset_index()
    asin_level_df['kw_list'] = asin_level_df['Title'].apply(get_title_keywords)
    
    all_title_words = []
    for ks in asin_level_df['kw_list']:
        all_title_words.extend(ks)
    
    kw_counts = Counter(all_title_words)
    # 取标题中出现频率最高的前 50 个关键词
    top_kws = [item[0] for item in kw_counts.most_common(50)]

    # --- B. 评论统计 (按行计数) ---
    analysis_data = []
    for kw in top_kws:
        # 标题端指标
        title_mentions = kw_counts[kw]
        title_penetration = (title_mentions / total_asins) * 100
        
        # 评论端指标 (精确全词匹配)
        pattern = fr'\b{kw}\b'
        review_mentions = df['Review Content'].str.contains(pattern, case=False, na=False).sum()
        review_echo_rate = (review_mentions / total_reviews) * 100
        
        analysis_data.append({
            "关键词": kw,
            "标题提及次数 (ASIN数)": title_mentions,
            "标题渗透率 (%)": round(title_penetration, 2),
            "评论提及次数 (行数)": review_mentions,
            "评论回声率 (%)": round(review_echo_rate, 2)
        })

    result_df = pd.DataFrame(analysis_data)
    # 计算转化效率：回声率 / 渗透率
    result_df['心智转化比'] = (result_df['评论回声率 (%)'] / result_df['标题渗透率 (%)']).round(2)
    
    return result_df, total_asins, total_reviews

# --- 3. Streamlit 展示层 ---
st.title("🎯 卖点回声分析看板")
st.markdown("""
该工具分析**商家宣传词（标题）**与**用户复述词（评论）**的重合度：
* **标题渗透率**: 该卖点在多少比例的商品标题中出现了。
* **评论回声率**: 该卖点在多少比例的用户评论中被提到了。
""")

# 文件上传
uploaded_file = st.file_uploader("上传酒精笔数据 (CSV 或 Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    # 读取数据
    if uploaded_file.name.endswith('.csv'):
        df_input = pd.read_csv(uploaded_file)
    else:
        df_input = pd.read_excel(uploaded_file)
    
    # 执行分析
    res_df, total_a, total_r = analyze_market_echo(df_input)
    
    if not res_df.empty:
        # 数据卡片展示统计基数
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("分析 ASIN 总数", total_a)
        col_m2.metric("分析评论总条数", total_r)

        st.divider()

        # 数据表格展示
        st.subheader("📊 关键词指标明细")
        # 默认按评论回声率排序
        res_df = res_df.sort_values("评论回声率 (%)", ascending=False)
        st.dataframe(
            res_df.style.background_gradient(subset=['评论回声率 (%)', '标题渗透率 (%)'], cmap='Blues'),
            use_container_width=True
        )

        # 可视化图表
        st.subheader("💡 市场渗透 vs 用户感知 象限图")
        fig = px.scatter(
            res_df, 
            x="标题渗透率 (%)", 
            y="评论回声率 (%)",
            size="标题提及次数 (ASIN数)",
            color="心智转化比",
            text="关键词",
            hover_name="关键词",
            labels={"心智转化比": "转化效率 (回声/渗透)"},
            title="横轴: 市场宣传强度 | 纵轴: 用户反馈强度",
            height=600
        )
        fig.update_traces(textposition='top center')
        # 添加 1:1 参考对角线
        max_val = max(res_df["标题渗透率 (%)"].max(), res_df["评论回声率 (%)"].max())
        fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, 
                      line=dict(color="Gray", dash="dash"))
        
        st.plotly_chart(fig, use_container_width=True)

        st.info("**象限解读：**\n\n1. **左上角 (高回声/低渗透)**：黑马需求！商家提得少，用户却很在意，应加强宣传。\n2. **右下角 (低回声/高渗透)**：无效堆砌。商家写得多，用户不买账，建议优化标题。")
else:
    st.warning("👈 请先在侧边栏或上方上传数据文件。")
