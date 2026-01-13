import pandas as pd
import streamlit as st
import plotly.express as px
import re
from collections import Counter

# --- 1. 简单的分词函数 ---
def get_title_keywords(title):
    # 只保留字母，转小写
    words = re.findall(r'\b[a-zA-Z]{3,}\b', str(title).lower())
    # 增加了一些常见的行业虚词，让结果更精准
    stop_words = {
        'and', 'the', 'with', 'for', 'set', 'markers', 'alcohol', 'art', 
        'color', 'colors', 'drawing', 'sketch', 'illustration', 'artist'
    }
    return [w for w in words if w not in stop_words]

# --- 2. 核心分析任务 ---
def analyze_exact_match(df):
    # 检查必要的列是否存在
    if 'Title' not in df.columns or 'Review Content' not in df.columns:
        st.error("上传的文件必须包含 'Title' 和 'Review Content' 两列！")
        return pd.DataFrame()

    # 提取标题高频词
    all_title_words = []
    # 临时处理缺失值，避免 apply 报错
    df['Title'] = df['Title'].fillna('')
    df['Review Content'] = df['Review Content'].fillna('')
    
    df['title_keywords'] = df['Title'].apply(get_title_keywords)
    for ks in df['title_keywords']:
        all_title_words.extend(ks)
    
    # 统计标题中最常见的关键词 top 20
    top_kws = [item[0] for item in Counter(all_title_words).most_common(20)]
    
    match_results = []
    for kw in top_kws:
        # A. 找到标题包含该词的行
        mask_title = df['Title'].str.contains(kw, case=False, na=False)
        subset = df[mask_title].copy()
        
        if not subset.empty:
            # B. 检查评论中是否包含原词 (\b 是单词边界)
            pattern = fr'\b{kw}\b'
            subset['is_matched'] = subset['Review Content'].str.contains(pattern, case=False, na=False)
            
            # 计算提及率
            match_rate = subset['is_matched'].mean() * 100
            
            match_results.append({
                "标题关键词": kw,
                "标题出现频率": len(subset),
                "评论原词提及率(%)": round(match_rate, 2)
            })
            
    return pd.DataFrame(match_results).sort_values("评论原词提及率(%)", ascending=False)

# --- 3. Streamlit 展示层 ---
st.set_page_config(page_title="标题-评论原词重合度分析", layout="wide")

st.title("🔍 标题-评论原词重合度挖掘")
st.markdown("""
通过对比 **标题中的卖点词** 是否在 **用户评论** 中原样出现，来验证营销关键词的“回声”强度。
""")

# --- 文件上传组件 ---
uploaded_file = st.file_uploader("请上传您的数据文件", type=['csv', 'xlsx'])

if uploaded_file is not None:
    # 根据文件扩展名读取数据
    try:
        if uploaded_file.name.endswith('.csv'):
            df_full = pd.read_csv(uploaded_file)
        else:
            df_full = pd.read_excel(uploaded_file)
        
        st.success(f"成功加载文件：{uploaded_file.name}，共 {len(df_full)} 行数据。")
        
        # 执行分析
        with st.spinner('正在分析中...'):
            exact_match_df = analyze_exact_match(df_full)

        if not exact_match_df.empty:
            # 布局：左边表格，右边图表
            col1, col2 = st.columns([1, 1.5])
            
            with col1:
                st.subheader("高频卖点‘回声’排名")
                st.dataframe(exact_match_df, use_container_width=True)
            
            with col2:
                st.subheader("卖点心智转化分布")
                fig = px.bar(
                    exact_match_df, 
                    x="评论原词提及率(%)", 
                    y="标题关键词",
                    orientation='h', # 改为横向方便阅读长单词
                    text="评论原词提及率(%)", 
                    color="评论原词提及率(%)",
                    color_continuous_scale='Blues',
                    labels={'评论原词提及率(%)': '心智转化率 (%)'}
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                
    except Exception as e:
        st.error(f"读取文件时出错: {e}")
else:
    st.info("💡 请在上方上传 CSV 或 Excel 文件开始分析。")
