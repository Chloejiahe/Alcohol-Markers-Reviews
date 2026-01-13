import pandas as pd
import streamlit as st
import plotly.express as px
import re
from collections import Counter

# --- 1. 简单的分词函数（排除数字和虚词） ---
def get_title_keywords(title):
    # 只保留字母，转小写
    words = re.findall(r'\b[a-zA-Z]{3,}\b', str(title).lower())
    # 排除常见的停用词
    stop_words = {'and', 'the', 'with', 'for', 'set', 'markers', 'alcohol', 'art', 'color', 'colors'}
    return [w for w in words if w not in stop_words]

# --- 2. 核心分析任务 ---
def analyze_exact_match(df):
    # 提取所有标题中出现的高频词
    all_title_words = []
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
            # B. 检查这些行的评论是否也包含这个词
            # 使用 \b 确保是精确单词匹配，而不是包含关系
            pattern = fr'\b{kw}\b'
            subset['is_matched'] = subset['Review Content'].str.contains(pattern, case=False, na=False)
            
            match_rate = subset['is_mentioned'].mean() * 100
            
            match_results.append({
                "标题关键词": kw,
                "标题出现次数": len(subset),
                "评论原词提及率(%)": round(match_rate, 2)
            })
            
    return pd.DataFrame(match_results).sort_values("评论原词提及率(%)", ascending=False)

# --- 3. Streamlit 展示 ---
st.title("🔍 标题-评论原词重合度挖掘")
st.info("不使用主观词库，直接对比标题中的词是否被用户在评论中原样复述。")

exact_match_df = analyze_exact_match(df_full)

st.subheader("高频标题词在评论中的‘回声’排名")
st.write("提及率越高，说明该词是用户最敏感、最认同的核心卖点。")
st.dataframe(exact_match_df)

# 可视化
fig = px.bar(exact_match_df, x="标题关键词", y="评论原词提及率(%)", 
             text="评论原词提及率(%)", color="评论原词提及率(%)",
             color_continuous_scale='Viridis')
st.plotly_chart(fig)
