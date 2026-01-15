import pandas as pd
import streamlit as st
import re
from collections import Counter
from textblob import TextBlob
import nltk
from nltk.tokenize import sent_tokenize
import plotly.express as px  # 用于画NSS图表

# 自动处理分句器所需的数据包
def load_nltk_resources():
    resources = ['punkt', 'punkt_tab'] # 兼容新旧版本的资源包
    for res in resources:
        try:
            nltk.data.find(f'tokenizers/{res}')
        except LookupError:
            nltk.download(res)

load_nltk_resources()

# 设置页面宽度和标题
st.set_page_config(page_title="酒精笔卖点渗透看板", layout="wide")

@st.cache_data
def calculate_nss_logic(df, mapping, sentiment_lib):
    all_sentences = []
    for review in df['Review Content'].fillna("").astype(str):
        all_sentences.extend(sent_tokenize(review.lower()))

    # 定义常见的否定词
    negations = {'not', 'no', 'never', 'bad', "don't", "doesn't", "isn't", "aren't"}

    patterns = {cat: re.compile(r'(' + '|'.join([re.escape(k) for k in keywords]) + r')')
                for cat, keywords in mapping.items()}

    processed_lib = {}
    for cat in mapping.keys():
        # ... (保留你原来的 Set 化逻辑) ...
        # 确保 lib_data 能够正确处理中文键名
        target_key = cat
        while isinstance(sentiment_lib.get(target_key), str):
            target_key = sentiment_lib[target_key]
        lib_data = sentiment_lib.get(target_key, {"正面": [], "负面": []})
        processed_lib[cat] = {"pos": set(lib_data["正面"]), "neg": set(lib_data["负面"])}

    results = []
    for category, pattern in patterns.items():
        pos_count, neg_count, total_hit = 0, 0, 0
        lib = processed_lib[category]

        for sentence in all_sentences:
            if pattern.search(sentence):
                total_hit += 1
                score = 0
                
                # 1. 检查是否存在否定含义 (简单前缀法)
                words = set(sentence.split())
                has_negation = not words.isdisjoint(negations)

                # 2. 匹配负面词库 (提高负面优先级)
                if any(n in sentence for n in lib["neg"]):
                    score = -1
                # 3. 匹配正面词库
                elif any(p in sentence for p in lib["pos"]):
                    # 如果有否定词，正面词变负面（如 not great）
                    score = -1 if has_negation else 1
                
                # 4. 恢复 TextBlob 兜底 (可选)
                if score == 0:
                    pol = TextBlob(sentence).sentiment.polarity
                    if pol > 0.2: score = 1
                    elif pol < -0.1: score = -1 # 降低负面阈值，捕捉更多不满

                if score == 1: pos_count += 1
                elif score == -1: neg_count += 1

        if total_hit > 0:
            results.append({
                "维度": category,
                "提及句子数": total_hit,
                "正面次数": pos_count,
                "负面次数": neg_count,
                "NSS分数": round((pos_count - neg_count) / total_hit, 3)
            })
    return pd.DataFrame(results)
    
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

SENTIMENT_LIB = {
    # 1. 通用称呼类 (核心：markers)
    "markers": {
        "正面": ['multi-purpose', 'all-in-one', 'jack of all trades', 'works for everything','use it for everything', 'handles a variety of tasks', 'works on multiple surfaces',
                'use on different surfaces', 'good for many different projects', 'one set for all my needs','great for both drawing and writing', 'great markers', 'love these pens', 'best markers ever', 'excellent quality', 'highly recommend', 'perfect set', 'wonderful tools'],
        "负面": ['not versatile', 'lacks versatility', 'not multi-purpose', 'single-purpose', 'single use','one-trick pony', 'limited use', 'very limited in its use', 'limited application',  'only for paper', 'only works on paper', 'doesn\'t work on other surfaces',
                'only good for one thing', 'useless for anything else', 'very specific use', 'terrible markers', 'waste of money', 'disappointed', 'poor quality', 'returned them', 'not worth it', 'would not buy again']
    },
    "marker": "markers", "pens": "markers", "pen": "markers", "highlighters": "markers", "highlighter": "markers",

    # 2. 颜色种类类 (核心：colors)
    "colors": {
        "正面": ['great color selection', 'perfect pastel set', 'good range of skin tones', 'well-curated palette', 'love the color story', 'beautiful assortment of colors', 'has every color I need''good standard colors', 'love the basic set', 'has all the primary colors', 'classic colors', 'many colors', 'lot of colors', 'plenty of colors', 'good range', 'great variety', 'great selection', 'every color', 'so many options'],
        "负面": ['garish colors', 'colors are too loud', 'too neon', 'too bright', 'too fluorescent', 'overly bright', 'limited range', 'not enough colors', 'wish for more', 'missing colors', 'disappointed with selection', 'needs more colors','inconsistent', 'different shade', 'not the same', 'misleading cap', 'cap is wrong', 'color is off', 'darker than cap', 'lighter than cap', "doesn't match", 'wrong color']
    },
    "color": "colors", "colored": "colors",

   # 3. 数量完整性 (核心：100) -> 关注数字对应的实收情况
    "100": {
        "正面": ['all present', 'full count', 'none missing', 'no missing markers', 'all arrived juiced', 'every color included', 'all accounted for'],
        "负面": ['missing markers', 'arrived with dry ones', 'short a few', 'not the full count', 'some were empty', 'missing a few colors']
    },
    "120": "100", "121": "100", "168": "100", "262": "100",

    # 4. 套装与价值 (核心：set) -> 关注套装整体给人的感觉
    "set": {
        "正面": ['great set', 'perfect kit', 'excellent value', 'well worth the money', 
            'wonderful collection', 'love this assortment', 'plus version is worth it', 
            'good art supplies', 'highly recommended set', 'beautifully packaged',
            'great starter set', 'comprehensive kit', 'perfect gift set'],
        "负面": ['not worth the price', 'flimsy kit', 'disappointed in the set', 'bonus was useless', 
               'cheap supplies', 'disappointed in the set', 'flimsy kit','incomplete set']
    },
    "kit": "set", "plus": "set", "bonus": "set", "supplies": "set", "series": "set",
    
    # 5. 色彩特性类 (核心：blending)
    "blending": {
        "正面": ['easy to blend', 'blends well', 'blendable', 'effortless blending', 'seamless blend', 'smooth gradient', 'layers nicely', 'reactivates well', 'colorless blender works great', 'perfect for fixing mistakes', 
            'cleans up edges', 'adds great highlights', 'moist and useful', 'great for fading out'],
        "负面": ["doesn't blend", 'difficult to blend', 'hard to blend', 'impossible to blend', 'gets muddy', 'pills paper', 'lifts underlying ink', 'colorless pen is dry', 'blender is useless', 'leaves water marks', 
            'doesn’t move the color']
    },
    "blendable": "blending", "blender": "blending", "colorless": "blending",
    
    # 6. 特定色系类 (核心：skin)
    "skin": {
        "正面": ['skin tones', 'flesh tones', 'skin tone palette', 'portrait palette', 'range of skin tones',
                          'neutral palette', 'neutral colors', 'neutrals', 'set of neutrals', 'earth tones'],
        "负面": ['missing skin tones', 'too many similar colors', 'no true red', 'missing skin tones', 'needs more skin tones', 'too orange', 'unnatural flesh tones', 'ashy skin colors']
    },
    "tone": "skin", "portrait": "skin",

    # 7. 笔头表现类 (核心：brush)
    "brush": {
        "正面": ['love the brush tip', 'great brush nib', 'smooth application with the brush', 'brush tip is very responsive','flexible brush tip', 'soft brush tip allows for variation','happy with the brush','good line variation', 'can make thick and thin lines', 'great control over stroke width', 'responsive brush'],
        "负面": ['hard to get a thin line', 'only makes thick strokes', 'inconsistent line width', 'no line variation', 'brush tip frays', 'brush tip split', 'brush tip wore out', 'brush tip lost its point','inconsistent brush line','brush tip clogged', 'ink won\'t flow from the brush']
    },
    "chisel": {
        "正面": ['perfect width for highlighting', 'good broad edge', 'nice thick lines for headers', 'sharp chisel edge', 'maintains a sharp edge', 'makes clean broad strokes',  'perfect for block lettering', 'great for filling large areas',
                      'can create both thick and thin lines', 'consistent broad lines', 'even coverage with broad side'],
        "负面": ['too wide for my bible', 'too narrow for a highlighter', 'chisel tip is too broad', 'chisel tip is too thick', 'chisel tip is too narrow','chisel tip wore down', 'loses its edge quickly', 'edge became rounded',
                      'dull chisel tip', 'dull chisel edge', 'can\'t get a sharp line', 'no longer has a crisp edge','inconsistent broad line', 'chisel tip crumbled', 'chisel tip chipped']
    },     
    "fine": {
        "正面": ['perfect for details', 'love the fine tip', 'thin enough for writing', 'great for fine lines', 'super fine point','love the fine tip', 'precise fine liner', 'crisp fine lines', 'excellent for fine details', 'perfect for writing in small spaces', 'great for intricate work','happy with the bullet','happy with the fine',
                      'allows for detailed drawing', 'perfect for outlining', 'creates super thin lines'],
        "负面": ['too thick for a fine liner', 'not a true fine', 'wish it was thinner', 'still too broad for small spaces', 'fine tip is scratchy','fine tip dried out', 'bent the fine tip', 'fine tip broke', 'inconsistent fine line','fine nib wore down', 'tip lost its point', 'fine tip feels fragile']
    },  
    "broad": {
        "正面": ['great for filling large areas', 'even coverage with the broad side', 'perfect for backgrounds',
            'nice thick lines', 'consistent broad strokes', 'sharp edges for calligraphy', 
            'great broad tip', 'holds its shape well', 'makes bold lines'
        ],
        "负面": [
            'broad tip is too blunt', 'edge became rounded', 'loses its crispness', 
            'inconsistent flow on broad side', 'too wide for details', 
            'broad nib wore down quickly', 'feels scratchy when filling', 'dries out too fast'
        ]
    },      
    "tip": {
        "正面": [
            'sturdy tips', 'high quality nibs', 'durable tipped markers', 'well-made tips',
            'smooth tips', 'nice feel on paper', 'tips glide easily', 'precise tips',
            'tips hold their shape', 'not easily damaged', 'long-lasting tips',
            'consistent flow from both tips', 'perfectly tipped'
        ],
        "负面": [
            'frayed tips', 'split tips', 'tips are falling apart', 'mushy tips', 'tips wore down too fast',
            'tips arrived dried out', 'scratchy tips', 'no ink in the tips', 'tips are too dry',
            'broken tips', 'bent tips', 'tips are inconsistent', 'clogged tips',
            'rough tips', 'felt tips are too hard', 'tips feel cheap'
        ]
    },
    "tips": "tip", "tipped": "tip",
    
    "dual": {
        "正面": ['love the dual tip', 'love the two tips', 'love that it has two sides', 'love the dual nibs','great having two tips', 'useful dual tip', 'handy dual tip', 'convenient to have two tips','best of both worlds', 'love the brush and fine tip combo', 'perfect combination of tips','like having two pens in one', 'great for switching between broad and fine'
        ],
        "负面": ['useless dual tip', 'redundant dual tip', 'unnecessary dual tip', "don't need the dual tip", 'never use the other side', 'only use one side', 'the other end is useless',
                       'wish it was a single tip', 'wish they sold them separately', 'would rather have two separate pens','only bought it for the brush side', 'one of the tips is useless'
        ]
    },   
    "double": "dual",
    
    # 8. 墨水与流畅性 (核心：ink)
    "ink": {
        "正面": ['quick dry', 'dry so fast','fast dry','not smear','not bleed','no bleed', 'not smear or bleed','dries quickly', 'dries instantly', 'dries immediately', 'fast-drying ink','no smear', 'no smudge', 'zero smear', 'zero smudge', 'smear proof', 'smudge proof',
                        'smudge resistant', 'smear resistant', 'doesn\'t smear', 'doesn\'t smudge','good for lefties', 'perfect for left-handed', 'lefty friendly','can highlight over it', 'highlight without smearing'],
        "负面": ['smears easily', 'smudges easily', 'smears across the page', 'smudges when touched', 'takes forever to dry', 'long drying time', 'never fully dries', 'still wet after minutes', 'slow to dry',
                        'not for left-handed', 'not for lefties', 'smears for left-handers', 'gets ink on my hand','smears with highlighter', 'smudges when layering', 'ruined my work by smudging', 'bad smell', 'strong smell', 'chemical smell', 'toxic smell', 'horrible odor', 'awful scent','overpowering smell', 'overwhelming fumes', 'nauseating smell', 'smells terrible',
                     'stinks', 'reek', 'stench', 'acrid smell', 'plastic smell','gives me a headache', 'headache inducing', 'smell is too strong', 'lingering smell']
    },
    "alcohol": "ink", "base": "ink",
    
    # 9. 配件笔身类 (核心：case)
    "case": {
        "正面": [
            'sturdy carrying case', 'well organized', 'convenient bag', 
            'love the penholder', 'comfortable barrel', 'high quality case', 
            'great for travel', 'nice swatch card included', 'zipper works well',
            'easy to carry', 'keeps markers organized', 'beautiful packaging', 'nice packaging', 'lovely box', 'great presentation', 'well presented', 'elegant packaging', 'giftable', 'perfect for a gift', 'great gift box', 'nice enough to gift','well packaged', 'packaged securely', 'protective packaging', 'arrived safe', 'arrived in perfect condition', 'no damage during shipping', 'excellent packaging',
            'sturdy case', 'durable case', 'high-quality box', 'nice tin', 'reusable case', 'great storage tin', 'comes in a nice case'
        ],
        "负面": [
            'flimsy case', 'broken zipper', 'penholder is cheap', 'difficult to remove pens', 'pens are too tight in the slots',
            'barrel feels fragile', 'case doesn’t close', 'missing the swatch card', 'struggle to get them out',
            'case arrived damaged', 'hard to get markers out', 'handle broke','messy organization', 'poorly organized', 'pens fall out of place',
            'too bulky', 'markers fall out of the holders']
    },
    "carrying": "case", "holders": "case", "penholder": "case",

    # 10. 绘画场景类 (核心：art)
   "art": {
        "正面": [
            'perfect for art projects', 'great for illustrations', 'best for anime drawing', 
            'smooth for sketching', 'vibrant for painting', 'excellent for fine art', 
            'perfect for shading', 'great for mixed media'
        ],
        "负面": [
            'low quality for art', 'hard to control for details', 'streaky for painting', 
            'ruined my drawing', 'sketching feels scratchy', 'ink spreads too much for art',
            'not good for detailed illustrations'
        ]
    },
    "drawing": "art", "sketch": "art", "sketching": "art", "painting": "art", "illustration": "art", "illustrations": "art", "animation": "art", "anime": "art", "making": "art", "coloring": "art", 

    # 11. 品牌竞争 (核心：ohuhu)
    "ohuhu": {
        "正面": [
            'great ohuhu alternative', 'better than copic', 'comparable to copic', 
            'best markers for the price', 'half the price of copic', 'just as good as ohuhu',
            'love the honolulu series', 'oahu markers are great', 'impressed with this brand', 
            'high quality for a budget brand', 'superior to other brands', 'well known for quality',
            'perfect quality for the brand', 'best budget markers', 'great brand for beginners'
        ],
        "负面": [
            'not as good as ohuhu', 'cheap copic knockoff', 'not copic quality', 
            'disappointed compared to ohuhu', 'stick with copic instead',
            'cheap brand feel', 'low end markers', 'not professional grade', 
            'overpriced for this brand', 'brand is inconsistent', 'not as described by the brand'
        ]
    },
    "copic": "ohuhu", "caliart": "ohuhu", "soucolor": "ohuhu", 
    "taotree": "ohuhu", "bianyo": "ohuhu", "shuttle": "ohuhu", "sfaih": "ohuhu", 
    "wellokb": "ohuhu", "memoffice": "ohuhu", "anymark": "ohuhu", "honolulu": "ohuhu", "oahu": "ohuhu",
    
    # 12. 教育场景
    "kids": {
        "正面": [
            'perfect for school', 'great for students', 'ideal for school supplies', 
            'perfect for art class', 'best for school projects',
            'kids loved them', 'my daughter/son enjoys them', 'great for girls and boys', 
            'teen friendly', 'perfect for teens', 'happy students',
            'safe for children', 'easy for kids to use', 'non-toxic',
            'great gift for kids', 'perfect birthday present', 
            'excellent for beginners'
        ],
        "负面": [
            'too difficult for young kids', 'not for school use', 'messy for students',
            'strong chemical smell', 'not safe for children', 'too staining', 
            'caps are hard for kids to open',
            'disappointed kids', 'not what my teen wanted', 'too professional for a child'
        ]
    },
    "school": "kids", "students": "kids", "girls": "kids", "boys": "kids", "teens": "kids", "teen": "kids",
    
    # 13. 节日礼赠
    "gift": {
        "正面": [
            'perfect gift', 'highly recommend as a gift', 'great birthday present', 
            'nice enough to gift', 'giftable', 'well packaged for gifting',
            'perfect for halloween', 'great for decorations', 'ideal for holiday projects', 
            'used for halloween crafts', 'lovely decorations', 'festive colors',
            'was a huge hit', 'they loved the surprise', 'great value for a gift'
        ],
        "负面": [
            'not gift worthy', 'disappointed as a gift', 'box arrived damaged', 
            'cheap packaging', 'looks used', 'not suitable for gifting',
            'not good for decorations', 'colors didn’t work for halloween',
            'too messy for holiday crafts', 'arrived too late for the holiday'
        ]
    },
    "gifts": "gift","halloween": "gift","decorations": "gift",
    
    # 13. 专业背书与创作  
    "professional": {
        "正面": [
            'professional quality', 'artist grade', 'highly recommend for creators', 
            'perfect for serious artists', 'impressive for professionals',
            'safety certificated', 'meets professional standards', 'non-toxic and certified', 
            'high-end performance', 'professional feel',
            'excellent for professional work', 'reliable for creators', 'top tier quality'
        ],
        "负面": [
            'not for professional use', 'not artist grade', 'feels like a toy', 
            'too basic for serious artists', 'not for professional work',
            'lacks proper certification', 'disappointed as a professional', 
            'cheap for the price', 'not as described for creators'
        ]
    },
    "artist": "professional", "artists": "professional", "creators": "professional", "certificated": "professional",
    
    # 14. 成人
    "adults": {
        "正面": [
            'perfect for adult coloring books', 'great for stress relief', 
            'ideal for relaxing hobbies', 'wonderful for detailed coloring',
            'suitable for grown-ups', 'high quality for hobbyists', 
            'feels premium for the price', 'not a cheap kids toy',
            'gives a professional look to my hobby', 'very therapeutic to use',
            'great for intricate patterns', 'perfect for card making and journals',
            'excellent for adults', 'highly recommend for older users'
        ],
        "负面": [
            'too childish for adults', 'feels like a kids set', 
            'not enough color depth for adult art', 'lacks the sophistication I expected',
            'hard to use for complex adult coloring', 'too messy for detailed work',
            'quality is too basic for grown-up projects',
            'frustrating for hobbyists', 'disappointing for an adult user'
        ]
    },
    "adult": "adults",

    # 15. pastel
    "pastel": {
        "正面": [
            'beautiful pastel colors', 'lovely macaron tones', 'soft aesthetic shades', 'pretty pale colors', 'gorgeous light tones', 'subtle hues', 'creamy pastels',
            'smooth laydown', 'even coverage', 'not streaky at all', 'no brush marks', 
            'blends like a dream', 'perfect for skin tones', 'great for base layers',
            'true to cap color', 'exactly the soft shade I wanted', 'not too neon', 'perfectly muted'
        ],
        "负面": [
            'streaky application', 'patchy finish', 'too watery', 'ink is too sheer', 'shows every stroke', 'grainy texture', 'dried out quickly',
            'too light to see', 'looks washed out', 'not enough pigment', 'colors are too yellowish', 'dirty looking pastels', 'darker than the cap',
            'pastel colors smell stronger', 'leaks more than dark colors', 'stains the nib'
        ]
    },

    # 16. book
    "book": {
        "正面": [
            'perfect for coloring books', 'great for adult coloring books', 
            'works well on book paper', 'fun for activity books', 
            'made for coloring books', 'ideal for coloring pages',
            'does not bleed through pages', 'minimal ghosting on back', 
            'doesn\'t ruin the other side', 'stays within the lines',
            'ink dries fast on book paper', 'great for coloring books'
        ],
        "负面": [
            'bleeds through the paper', 'ruined my coloring book', 
            'soaked through the pages', 'damaged the next page', 
            'too much bleed through', 'cannot use on double-sided books',
            'ink spreads too much on book paper', 'tears the paper', 
            'scratches the book surface', 'smudges on glossy books',
            'too wet for standard coloring books'
        ]
    },
    "books": "book",
    
    # 17. black
    "black": {
        "正面": [
            'rich black ink', 'deep black', 'true black', 'very pigmented black', 
            'no grey tones', 'solid black coverage', 'jet black',
            'perfect for outlining', 'great for deep shadows', 'opaque black',
            'doesn\'t fade to grey', 'consistent flow',
            'opaque white', 'perfect white highlights', 'crisp white lines'
        ],
        "负面": [
            'looks more like dark grey', 'watery black', 'faded black', 
            'not dark enough', 'transparent black', 'greyish tint',
            'black marker was dried out', 'black ink leaks', 'smears when wet',
            'streaky coverage', 'stains through too much',
        ]
    },
    
    # 18. card
    "card": {
        "正面": ['comes with a swatch card', 'includes a swatch card', 'love the swatch card', 
               'helpful swatch card', 'great for swatching', 'easy to swatch', 'blank swatch card', 'pre-printed swatch card',
               'perfect for card making', 'great for DIY greeting cards', 'works well on heavy cardstock', 'ideal for handmade cards','ink looks vibrant on cards'
        ],
        "负面": ['no swatch card', "wish it had a swatch card", "doesn't come with a swatch card", 
               'had to make my own swatch card', 'bleeds through cardstock', 'ink feathers on cards', 
               'smudges on glossy card paper', 'not good for thick cards'
        ]
    },
    
    # 19. white
    "white": {
        "正面": [
            'great coverage over dark colors', 'opaque white ink', 'vibrant white highlights', 
            'thick white pigment', 'covers black perfectly', 'bold white lines',
            'flows smoothly', 'doesn\'t clog', 'consistent white ink', 
            'perfect for adding highlights', 'makes drawings pop',
            'works over alcohol markers', 'stands out on dark paper'
        ],
        "负面": [
            'translucent', 'too sheer', 'doesn\'t cover at all', 
            'very watery white', 'white ink is scratchy', 'dried out upon arrival',
            'clogged nib', 'ink skips', 'yellows over time', 
            'blends into the background', 'ruined my highlights'
        ]
    },
    
    # 20. refillable
    "refillable": {
        "正面": [
            'love that they are refillable', 'eco-friendly option', 'saves money in the long run', 
            'no need to buy a new set', 'sustainable markers',
            'easy to refill', 'mess-free refilling', 'ink bottles are great', 
            'nib is easy to remove for refill', 'refillable system works perfectly',
            'long-term investment', 'never run out of your favorite color'
        ],
        "负面": [
            'hard to refill', 'very messy to add ink', 'ink leaked everywhere during refill', 
            'damaged the nib while refilling', 'too difficult for beginners',
            'not actually refillable', 'cannot find refill ink anywhere', 
            'refill bottles are too expensive', 'proprietary refill system is annoying'
        ]
    },

    # 20. barrel
    "barrel": {
        "正面": [
            'durable body', 'sturdy', 'sturdy build', 
            'well-made', 'solid construction', 'solidly built','quality feel', 
            'feels premium', 'high quality materials', 'quality build', 'well put together',
            'feels substantial', 'built to last', 'high-grade plastic', 'metal construction', 'feels expensive','comfortable to hold', 'comfortable grip', 'ergonomic', 'ergonomic design', 'ergonomic shape', 'nice to hold', 'feels good in the hand', 'feels great in the hand', 'good grip', 'soft grip',
            'well-balanced', 'perfect weight', 'nice balance', 'fits my hand perfectly', 'contours to my hand', 'doesn\'t cause fatigue', 'no hand cramps', 'can write for hours', 'can draw for hours', 'reduces hand strain'
        ],
        "负面": [ 
            'uncomfortable to hold', 'uncomfortable grip', 'awkward to hold', 'awkward shape','causes hand fatigue', 'tires my hand quickly', 
            'gives me hand cramps', 'hand cramps up', 'hurts my hand', 'digs into my hand', 'sharp edges', 'too thick', 'too thin', 
            'too wide', 'too narrow', 'slippery grip', 'hard to get a good grip', 'poorly balanced', 'too heavy', 'too light', 'weird balance',
            'feels cheap', 'flimsy', 'cheap plastic', 'thin plastic', 'brittle plastic', 'feels plasticky', 'poorly made', 'poor construction', 
            'badly made', 'low quality build', 'fell apart','cracked easily', 'developed a crack','break', 'broke easily', 'broke when dropped', 
            'snapped in half', 'easy to break',
        ]
    },
    
    # 21. permanent
    "permanent": {
        "正面": [
            'truly permanent', 'permanent bond', 'archival quality', 'archival ink', 'museum quality','is waterproof', 'water resistant', 'doesn\'t run with water', 'survives spills', 'water-fast',
            'fade proof', 'fade resistant', 'lightfast', 'excellent lightfastness', 'uv resistant', 'doesn\'t fade over time'
        ],
        "负面": [ 
            'not permanent', 'isn\'t permanent', 'fades quickly', 'fades over time', 'colors have faded', 'not lightfast','not waterproof', 
            'isn\'t water resistant', 'washes away', 'runs with water', 'smears with water','ruined by a drop of water', 'ink bleeds when wet'
        ]
    },

    # 22. aesthetic
    "aesthetic": {
        "正面": [
            'pleasing aesthetic', 'beautiful design', 'minimalist design', 'sleek design', 'clean design', 
            'well-designed', 'thoughtful design', 'love the design', 'love the look of', 'looks elegant', 
            'high-end look', 'modern look', 'looks professional', 'beautiful packaging', 'nice packaging', 
            'lovely box', 'great presentation', 'well presented', 'elegant packaging', 'very photogenic', 'cozy vibes'
        ],
        "负面": [
            'looks cheap', 'feels cheap', 'cheaply made', 'cheap appearance', 'low-end look', 
            'plasticky feel', 'flimsy appearance', 'looks like a toy', 'toy-like', 'ugly design', 
            'unattractive design', 'clunky design', 'awkward look', 'poorly designed', 'gaudy colors', 
            'tacky design', 'looks dated', 'outdated design', 'flimsy packaging', 'cheap packaging'
        ]
    },

    # 23. underlining
    "underlining": {
        "正面": [
            'perfect for underlining', 'great for highlighting', 'smooth for taking notes', 
            'crisp lines for underlining', 'doesn\'t smudge my notes', 'precise for marking', 
            'ideal for study guides', 'works well on textbook paper', 'good for bullet journals'
        ],
        "负面": [
            'too thick for underlining', 'bleeds through the page', 'ruined my notes', 
            'too wet for marking', 'ink spreads too much', 'smears ink underneath', 
            'scratches thin paper', 'not good for textbooks', 'too bulky for small notes'
        ]
    },
    
    # 24. stuffers
    "stuffers": {
        "正面": [
            'perfect stocking stuffer', 'great small gift', 'kids loved this stuffer', 
            'fits perfectly in a stocking', 'excellent holiday stuffer', 'ideal stocking filler', 
            'cute little gift', 'was a big hit as a stuffer', 'nice surprise for kids'
        ],
        "负面": [
            'too big for a stuffer', 'poor quality for a gift', 'packaging too bulky', 
            'arrived too late for stocking', 'disappointing as a stuffer', 
            'box was crushed (not giftable)', 'not worth the price for a stuffer'
        ]
    },
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

# 整个脚本只保留一个 file_uploader
uploaded_file = st.file_uploader("上传数据文件 (Excel/CSV)", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        # 1. 数据读取逻辑
        if uploaded_file.name.endswith('.csv'):
            df_input = pd.read_csv(uploaded_file)
        else:
            df_input = pd.read_excel(uploaded_file)

        # 基础数据统计
        total_a = df_input['ASIN'].nunique()
        total_r = len(df_input)
        st.sidebar.metric("分析 ASIN 总数", total_a)
        st.sidebar.metric("分析评论总条数", total_r)

        # 2. 词频匹配板块 (Tab 模式)
        tab1, tab2 = st.tabs(["🔍 词频精确匹配", "🧬 语义模糊匹配"])

        with tab1:
            st.markdown("🔍 **逻辑：** 自动提取标题高频词，匹配评论原文。")
            res_exact = perform_analysis(df_input, mode="exact")
            st.dataframe(res_exact.style.background_gradient(subset=['评论回声率 (%)', '心智转化比'], cmap='YlGnBu'), use_container_width=True)

        with tab2:
            st.markdown("🧬 **逻辑：** 基于同义词词库进行模糊匹配渗透。")
            res_fuzzy = perform_analysis(df_input, mode="fuzzy")
            st.dataframe(res_fuzzy.style.background_gradient(subset=['评论回声率 (%)', '心智转化比'], cmap='OrRd'), use_container_width=True)

        # 3. 情感分析板块 (必须保持在这里，属于 if uploaded_file 内部)
        st.divider()
        st.header("🎭 卖点口碑深度分析 (NSS)")
        
        with st.spinner('正在计算句子级情感归因...'):
            # 调用你定义的函数
            nss_results = calculate_nss_logic(df_input, EXTENDED_MAPPING, SENTIMENT_LIB)
        
        if nss_results is not None and not nss_results.empty:
            nss_results = nss_results.sort_values("NSS分数", ascending=True)
            
            col_fig, col_table = st.columns([3, 2])
            
            with col_fig:
                # 选取代表性维度
                display_df = pd.concat([nss_results.head(10), nss_results.tail(10)]).drop_duplicates()
                fig = px.bar(
                    display_df, 
                    x="NSS分数", 
                    y="维度", 
                    orientation='h',
                    color="NSS分数",
                    color_continuous_scale='RdYlGn',
                    range_color=[-1, 1],
                    title="重点卖点口碑净值 (NSS)"
                )
                fig.add_vline(x=0, line_dash="dash", line_color="black")
                st.plotly_chart(fig, use_container_width=True)
                
            with col_table:
                st.subheader("明细数据")
                st.dataframe(
                    nss_results.style.background_gradient(subset=['NSS分数'], cmap='RdYlGn', vmin=-1, vmax=1),
                    height=400, use_container_width=True
                )

            # 负面预警
            critical_issues = nss_results[nss_results['NSS分数'] < 0]['维度'].tolist()
            if critical_issues:
                st.error(f"⚠️ **负面预警**：以下维度口碑为负，建议优先检查：{', '.join(critical_issues)}")
        else:
            st.warning("未能匹配到词库中的卖点，请扩充 EXTENDED_MAPPING 或检查评论列。")

    except Exception as e:
        st.error(f"处理文件时出错: {str(e)}")
        st.info("提示：请确保 CSV/Excel 包含 ASIN 和 review_body (评论内容) 列。")

else:
    # 没有任何文件上传时显示这个提示
    st.info("👋 请在上方上传数据文件以开始分析。")
