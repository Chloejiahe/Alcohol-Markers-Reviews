import pandas as pd
import streamlit as st
import re
from collections import Counter

# 设置页面宽度和标题
st.set_page_config(page_title="酒精笔卖点渗透看板", layout="wide")

# --- 0. 配置词库 ---
EXTENDED_MAPPING = {
    "alcohol": ["alcohol", "permanent", "ink"],
    "markers": ["markers", "marker", "pens", "pen"],
    "colors": ["colors", "color", "shades", "pigments"],
    "coloring": ["coloring", "color in", "fill in"],
    "art": ["art", "artist", "artwork"],
    "dual": ["dual", "double", "two sided", "both ends"],
    "tip": ["tip", "tips", "nib", "point"],
    "drawing": ["drawing", "draw", "strokes"],
    "set": ["set", "kit", "pack", "bundle"],
    "marker": ["marker", "pen"],
    "kids": ["kids", "children", "child", "son", "daughter"],
    "adult": ["adult", "adults", "grown up"],
    "sketching": ["sketching", "sketch", "doodle"],
    "illustration": ["illustration", "illustrations", "illustrate"],
    "adults": ["adults", "adult", "grown ups", "coloring"],
    "chisel": ["chisel", "broad", "wide", "wedge"],
    "sketch": ["sketch", "sketching", "sketches", "doodle"],
    "artist": ["artist", "artists", "professional"],
    "fine": ["fine", "point", "small", "thin", "detail"],
    "case": ["case", "bag", "organizer", "holder", "carrying"],
    "permanent": ["permanent", "alcohol", "waterproof"],
    "brush": ["brush", "flexible", "soft", "foam"],
    "tips": ["tips", "tip", "nib", "nibs"],
    "painting": ["painting", "paint", "color"],
    "perfect": ["perfect", "great", "excellent", "ideal"],
    "pens": ["pens", "pen", "markers", "marker"],
    "double": ["double", "dual", "two ends", "both sides"],
    "refillable": ["refillable", "refills", "refill", "ink bottle"],
    "artists": ["artists", "artist", "pro", "professional"],
    "tipped": ["tipped", "tip", "ends"],
    "supplies": ["supplies", "stationary", "tools", "kit"],
    "ohuhu": ["ohuhu", "honolulu", "oahu","brand"],
    "book": ["book", "books", "coloring book", "pages"],
    "color": ["color", "colors", "shades", "palette"],
    "blender": ["blender", "blending", "mix"],
    "books": ["books", "book", "coloring books"],
    "card": ["card", "cards", "cardstock", "postcards"],
    "making": ["making", "craft", "create", "diy"],
    "students": ["students", "student", "school", "class"],
    "gift": ["gift", "gifts", "present", "birthday"],
    "ink": ["ink", "fluid", "juicy", "dry"],
    "pen": ["pen", "pens", "marker", "markers"],
    "100": ["100", "count", "variety", "huge set", "large pack", "plenty", "lots of"],
    "plus": ["plus", "extra", "bonus", "additional"],
    "certificated": ["certificated", "safe", "non-toxic", "certification", "sds", "conform"],
    "caliart": ["caliart","brand"],
    "colorless": ["colorless", "blender", "0", "clear"],
    "shuttle": ["shuttle", "shuttle art","brand"],
    "gifts": ["gifts", "gift", "present", "birthday", "christmas"],
    "white": ["white", "highlight", "blender", "light"],
    "120": ["120", "count", "huge", "variety", "selection"],
    "honolulu": ["honolulu", "ohuhu","brand"],
    "colored": ["colored", "color", "colors", "pigment"],
    "pastel": ["pastel", "pale", "light colors", "soft"],
    "black": ["black", "dark", "outline", "liner"],
    "holders": ["holders", "case", "stand", "tray", "base"],
    "262": ["262", "massive", "every color", "giant", "complete"],
    "blending": ["blending", "blend", "mix", "gradient", "seamless"],
    "carrying": ["carrying", "case", "bag", "portable", "travel"],
    "tone": ["tone", "tones", "skin", "shades"],
    "kit": ["kit", "set", "pack", "supplies", "bundle"],
    "illustrations": ["illustrations", "illustration"],
    "girls": ["girls", "girl", "daughter", "granddaughter", "niece"],
    "boys": ["boys", "boy", "son", "grandson", "nephew"],
    "portrait": ["portrait", "faces", "skin", "flesh", "people"],
    "sfaih": ["sfaih","brand"],
    "skin": ["skin", "flesh", "portrait", "tones", "nude"],
    "broad": ["broad", "chisel", "wide", "thick"],
    "professional": ["professional", "pro", "quality", "artist grade"],
    "school": ["school", "class", "project", "student"],
    "base": ["base", "alcohol based"],
    "anime": ["anime", "manga", "comic", "characters"],
    "blendable": ["blendable", "blending", "mix", "seamless"],
    "168": ["168", "count", "set", "massive"],
    "wellokb": ["wellokb","brand"],
    "oahu": ["oahu", "ohuhu","brand"],
    "taotree": ["taotree","brand"],
    "soucolor": ["soucolor","brand"],
    "animation": ["animation", "anime", "cartoon", "characters"],
    "penholder": ["penholder", "base", "stand", "organizer", "tray"],
    "anymark": ["anymark", "brand"],
    "copic": ["copic","brand"],
    "cute": ["cute", "adorable", "kawaii", "lovely", "pretty"],
    "121": ["121", "massive", "every color", "giant", "count", "set"],
    "teen": ["teen", "teens", "teenager", "youth"],
    "aesthetic": ["aesthetic", "beautiful", "vibrant", "pretty"],
    "creators": ["creators", "creator", "artists"],
    "barrel": ["barrel", "handle", "hold", "grip", "shape"],
    "bonus": ["bonus", "extra", "free", "additional", "gift"],
    "series": ["series", "collection", "set"],
    "highlighters": ["highlighters", "highlighting", "neon", "bright"],
    "teens": ["teens", "teenager", "youth", "12-17"],
    "decorations": ["decorations", "decor", "craft", "diy"],
    "memoffice": ["memoffice", "brand"],
    "stuffers": ["stuffers", "fillers", "gift", "stocking"],
    "underlining": ["underlining", "underline", "highlight", "note taking"],
    "halloween": ["halloween", "spooky", "fall", "orange", "black"],
    "highlighters": ["highlighters", "highlighting", "neon", "marker"],
    "highlighter": ["highlighter", "highlighting", "neon", "marker"],
    "bianyo": ["bianyo"],
    "cozy": ["cozy", "comfortable", "warm", "homey"],
}

CLEAN_MAPPING = {str(k).lower(): [str(i).lower() for i in v] for k, v in EXTENDED_MAPPING.items()}

# --- 1. 基础分词函数 ---
def get_title_keywords(title):
    words = re.findall(r'\b\w{3,}\b', str(title).lower())
    stop_words = {'and', 'the', 'with', 'for', 'based', 'from', 'this', 'that', 'these', 'those'}
    return list(set([w for w in words if w not in stop_words]))

# --- 2. 核心分析逻辑 ---

def perform_analysis(df, mode="exact"):
    """
    mode: "exact" 使用自动生成的 top_kws 进行词对词匹配
    mode: "fuzzy" 使用 EXTENDED_MAPPING 进行语义丛匹配
    """
    df['Title'] = df['Title'].fillna('').astype(str).str.lower()
    df['Review Content'] = df['Review Content'].fillna('').astype(str).str.lower()
    
    total_asins = df['ASIN'].nunique()
    asin_level_df = df.groupby('ASIN')['Title'].first().reset_index()
    asin_groups = {asin: group for asin, group in df.groupby('ASIN')}

    if mode == "exact":
        asin_level_df['kw_list'] = asin_level_df['Title'].apply(get_title_keywords)
        all_title_words = [w for ks in asin_level_df['kw_list'] for w in ks]
        target_list = [item[0] for item in Counter(all_title_words).most_common(100)]
    else:
        target_list = list(CLEAN_MAPPING.keys())

    analysis_data = []

    for key_word in target_list:
        # 1. 锁定标题包含该词的 ASIN
        title_pattern = fr'\b{re.escape(key_word)}\b'
        relevant_asins = asin_level_df[asin_level_df['Title'].str.contains(title_pattern, na=False)]['ASIN'].tolist()
        
        title_mentions = len(relevant_asins)
        if title_mentions == 0: continue
            
        title_penetration = (title_mentions / total_asins) * 100
        
        # 2. 锁定评论子集
        relevant_reviews_series = pd.concat([asin_groups[a]['Review Content'] for a in relevant_asins])
        specific_total_reviews = len(relevant_reviews_series)

        # 3. 确定匹配模式
        if mode == "exact":
            match_pattern = title_pattern
            display_name = key_word
            extra_info = "-"
        else:
            synonyms = CLEAN_MAPPING[key_word]
            match_pattern = r'\b(' + '|'.join([re.escape(s) for s in synonyms]) + r')\b'
            display_name = key_word
            extra_info = ", ".join(synonyms[:3]) + "..."

        # 4. 计算指标
        review_mentions = relevant_reviews_series.str.contains(match_pattern, na=False).sum()
        review_echo_rate = (review_mentions / specific_total_reviews * 100) if specific_total_reviews > 0 else 0
        conversion = review_echo_rate / title_penetration if title_penetration > 0 else 0

        analysis_data.append({
            "关键词/卖点": display_name,
            "语义涵盖范围": extra_info,
            "标题ASIN数": title_mentions,
            "标题渗透率 (%)": round(title_penetration, 2),
            "关联评论总数": specific_total_reviews,
            "评论提及次数": review_mentions,
            "评论回声率 (%)": round(review_echo_rate, 2),
            "心智转化比": round(conversion, 2)
        })

    return pd.DataFrame(analysis_data).sort_values("评论回声率 (%)", ascending=False)

# --- 3. 展示层 ---
st.title("🎯 酒精笔卖点渗透看板 (全效合一版)")

uploaded_file = st.file_uploader("上传数据文件 (Excel/CSV)", type=['csv', 'xlsx'])

if uploaded_file:
    df_input = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    total_a = df_input['ASIN'].nunique()
    total_r = len(df_input)

    st.sidebar.metric("分析 ASIN 总数", total_a)
    st.sidebar.metric("分析评论总条数", total_r)

    # 使用标签页区分两种模式
    tab1, tab2 = st.tabs(["🔍 词频精确匹配 (系统自动发现)", "🧬 语义模糊匹配 (基于自定义词库)"])

    with tab1:
        st.markdown("🔍 **逻辑：** 自动提取标题高频词，并在评论中寻找**一模一样**的单词。")
        res_exact = perform_analysis(df_input, mode="exact")
        st.dataframe(res_exact.style.background_gradient(subset=['评论回声率 (%)', '心智转化比'], cmap='YlGnBu'), use_container_width=True)

    with tab2:
        st.markdown("🧬 **逻辑：** 当标题出现核心词时，在评论中寻找其**所有同义词**（如：标题有dual，评论有double也算命中）。")
        res_fuzzy = perform_analysis(df_input, mode="fuzzy")
        st.dataframe(res_fuzzy.style.background_gradient(subset=['评论回声率 (%)', '心智转化比'], cmap='OrRd'), use_container_width=True)
else:
    st.info("请在上方上传文件以开始分析。")
