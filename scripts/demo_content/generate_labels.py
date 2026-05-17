#!/usr/bin/env python3
"""Generate semantic label mappings from topic cluster analysis.

Produces:
  - topic_labels.json: topic_id → {display_name, category}
  - query_labels.json: query_key → display label
  - templates.py: per-category Chinese content templates

Category assignment is manual but reproducible from cluster data.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# Manual category assignment per cluster rank.
# Cluster 1 is the mega-cluster (267 topics) → split into sub-categories by index range.
CLUSTER_CATEGORIES: dict[int, str] = {
    1:  "General",
    2:  "Technology",
    3:  "Education",
    4:  "Finance",
    5:  "Health",
    6:  "Food",
    7:  "Gaming",
    8:  "Entertainment",
    9:  "Sports",
    10: "Travel",
    11: "Music",
    12: "Career",
    13: "Automotive",
    14: "Tech Gadgets",
    15: "Fashion",
    16: "Pets",
    17: "Home",
    18: "Anime",
    19: "History",
    20: "Psychology",
    21: "Law",
    22: "Design",
}

# Sub-categories for cluster 1 mega-topics (split by index ranges)
MEGA_SUB_CATEGORIES = [
    ("Food", 0, 30),
    ("Technology", 30, 60),
    ("Education", 60, 85),
    ("Finance", 85, 110),
    ("Health", 110, 135),
    ("Gaming", 135, 155),
    ("Entertainment", 155, 175),
    ("Sports", 175, 195),
    ("Travel", 195, 215),
    ("Career", 215, 235),
    ("Music", 235, 250),
    ("Tech Gadgets", 250, 267),
]

# Topic display names per category — each category has a list of plausible names
CATEGORY_TOPIC_NAMES: dict[str, list[str]] = {
    "Food": ["Hot Pot", "BBQ", "Sushi", "Ramen", "Pizza", "Tacos", "Dim Sum", "Burgers",
             "Pho", "Curry", "Steak", "Pasta", "Tapas", "Sashimi", "Biryani", "Pad Thai",
             "Croissant", "Burrito", "Paella", "Falafel", "Kimchi", "Gyoza", "Poke", "Hummus",
             "Samosa", "Banh Mi", "Ceviche", "Tom Yum", "Ramen", "Dumplings"],
    "Technology": ["AI", "Machine Learning", "Deep Learning", "Autonomous Driving", "5G",
             "Chips", "Cloud Computing", "Big Data", "Blockchain", "IoT", "Quantum Computing",
             "AR/VR", "Robotics", "Drones", "SpaceX", "OpenAI", "GPT", "Neural Networks",
             "NLP", "Computer Vision", "Speech Recognition", "Recommendation Systems", "Edge Computing",
             "DevOps", "Cybersecurity"],
    "Education": ["Graduate Exams", "College Admissions", "Study Abroad", "English Learning",
             "Mathematics", "Physics", "Programming", "MBA", "PhD", "GRE", "TOEFL", "IELTS",
             "SAT", "University Rankings", "Online Learning", "Coursera", "Thesis Writing",
             "Research", "Lab Work", "Exchange Programs", "Scholarships", "Internships",
             "Career Fairs", "Bootcamps", "Self-Study"],
    "Finance": ["Stocks", "Funds", "S&P 500", "Nasdaq", "Bitcoin", "Ethereum", "Housing Market",
             "Mortgages", "Personal Finance", "Insurance", "Taxes", "Inflation", "Startups",
             "Venture Capital", "IPO", "Earnings Reports", "Value Investing", "Index Funds",
             "Crypto Trading", "Quantitative Trading"],
    "Health": ["Fitness", "Weight Loss", "Yoga", "Running", "Swimming", "Cycling", "Hiking",
             "Marathon", "CrossFit", "Meditation", "Mental Health", "Sleep", "Nutrition",
             "Supplements", "Vaccines", "Health Checkups", "Physical Therapy", "Wellness"],
    "Gaming": ["League of Legends", "Genshin Impact", "Elden Ring", "Zelda", "Final Fantasy",
             "CS:GO", "DOTA 2", "Minecraft", "Fortnite", "Baldur's Gate 3", "Starfield",
             "Monster Hunter", "Switch", "PS5", "Steam", "Indie Games", "Esports",
             "Retro Gaming", "VR Gaming", "RPGs"],
    "Entertainment": ["Movie Recs", "TV Shows", "Netflix", "K-Drama", "Anime", "Reality TV",
             "Documentaries", "Nolan", "Marvel", "DC", "Sci-Fi", "Thriller", "Comedy",
             "Horror", "Oscars", "Cannes", "IMDB Top", "YouTube", "Streaming", "Vlogs"],
    "Sports": ["NBA", "Football", "World Cup", "Premier League", "La Liga", "Champions League",
             "Tennis", "F1", "Olympics", "Skateboarding", "Skiing", "Surfing", "Climbing",
             "Boxing", "UFC", "Badminton", "Table Tennis"],
    "Travel": ["Japan", "Thailand", "Europe Trip", "USA Road Trip", "New Zealand", "Iceland",
             "Maldives", "Road Trip", "Backpacking", "Camping", "Hotels", "Airbnb",
             "Visa Tips", "Travel Guides", "Budget Travel", "Family Travel", "Honeymoon",
             "Northern Lights", "Solo Travel"],
    "Career": ["Interviews", "Resume Tips", "FAANG", "Job Hopping", "Salary Negotiation",
             "Remote Work", "Freelancing", "Side Hustle", "Communication", "Management",
             "Leadership", "OKRs", "KPIs", "Promotion", "Career Change", "Networking",
             "Startup Culture", "Work-Life Balance"],
    "Music": ["Taylor Swift", "Kendrick Lamar", "BTS", "BLACKPINK", "Classical", "Jazz",
             "Rock", "Hip Hop", "EDM", "Folk", "K-Pop", "Piano", "Guitar", "Festivals",
             "Live Shows", "Vinyl", "Spotify", "Playlists"],
    "Automotive": ["Tesla", "BYD", "NIO", "EVs", "Autonomous Driving", "Model 3",
             "SUV", "Sports Cars", "Car Mods", "Fuel Economy", "Maintenance", "Used Cars",
             "Car Reviews", "F1", "WRC"],
    "Tech Gadgets": ["iPhone", "Samsung", "MacBook", "iPad", "AirPods", "Camera",
             "Lenses", "Drones", "Headphones", "Smartwatch", "Monitor", "Mechanical Keyboard",
             "NAS", "Smart Home", "HomeKit", "Android"],
    "Fashion": ["Streetwear", "Makeup", "Skincare", "Fragrance", "Lipstick", "Serum",
             "Sunscreen", "Face Mask", "Sneakers", "Luxury", "Minimalist", "Vintage",
             "Japanese Style", "Korean Style", "Color Theory"],
    "Pets": ["Cats", "Dogs", "British Shorthair", "Ragdoll Cat", "Golden Retriever",
             "Corgi", "Hamsters", "Rabbits", "Parrots", "Aquarium", "Pet Food",
             "Flea Treatment", "Neutering", "Adoption", "Dog Walking", "Vet"],
    "Home": ["Interior Design", "Scandinavian Style", "Japanese Style", "Minimalism",
             "Organization", "Furniture", "IKEA", "Smart Home", "Lighting Design",
             "Decor", "Decluttering", "Rental Makeover", "Balcony Garden", "Kitchen",
             "Bathroom", "Plants", "Rugs", "Curtains"],
    "Anime": ["Attack on Titan", "Demon Slayer", "Jujutsu Kaisen", "One Piece", "Naruto",
             "Spy x Family", "EVA", "Fullmetal Alchemist", "Death Note", "Fate",
             "Makoto Shinkai", "Studio Ghibli", "Cosplay", "Manga", "Comiket"],
    "History": ["Ancient History", "Modern History", "WWII", "Cold War", "Roman Empire",
             "Ming Dynasty", "Tang Dynasty", "Silk Road", "Archaeology", "Museums"],
    "Psychology": ["MBTI", "Attachment Styles", "Anxiety", "Depression", "Therapy",
             "CBT", "Family of Origin", "Relationships", "Social Anxiety", "Mindfulness",
             "Self-Growth", "Communication Skills", "NLP"],
    "Law": ["Labor Law", "Contract Law", "Family Law", "Intellectual Property", "Corporate Law",
             "Arbitration", "Litigation", "Bar Exam", "Compliance", "Privacy", "GDPR"],
    "Design": ["UI Design", "UX", "Graphic Design", "Illustration", "Figma", "Photoshop",
             "Sketch", "Typography", "Color Theory", "Layout", "Branding", "Logo Design",
             "Posters", "Industrial Design", "Architecture"],
    "General": ["Trending", "Opinion", "Discussion", "Tips & Tricks", "Review",
             "Comparison", "Tutorial", "Explainer", "Myth Busting", "Q&A"],
}


def load_cluster_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def generate_topic_labels(clusters: list[dict]) -> dict[int, dict]:
    labels: dict[int, dict] = {}
    seed = 42  # deterministic "randomness"

    for cluster in clusters:
        rank = cluster["cluster_rank"]
        topic_ids = cluster["topic_ids"]

        if rank == 1:
            # Mega cluster: assign sub-categories by index range, cycling through shuffled names
            for sub_cat, start, end in MEGA_SUB_CATEGORIES:
                names = list(CATEGORY_TOPIC_NAMES[sub_cat])
                rng = random.Random(seed + start)
                rng.shuffle(names)
                sub_topics = topic_ids[start:end]
                for i, topic_id in enumerate(sub_topics):
                    labels[int(topic_id)] = {
                        "display_name": names[i % len(names)],
                        "category": sub_cat,
                    }
        else:
            category = CLUSTER_CATEGORIES.get(rank, "General")
            names = CATEGORY_TOPIC_NAMES.get(category, CATEGORY_TOPIC_NAMES["General"])
            rng = random.Random(seed + rank * 1000)
            rng.shuffle(names)
            for i, topic_id in enumerate(topic_ids):
                labels[int(topic_id)] = {
                    "display_name": names[i % len(names)],
                    "category": category,
                }

    # De-duplicate display_names within same category — use natural chinese suffixes
    _DEDUP_SUFFIXES = ["", " Advanced", " Pro", " Guide", " Deep Dive", " Basics", " Tips", " Trends"]
    seen: dict[tuple, list[int]] = {}
    for tid, info in labels.items():
        key = (info["category"], info["display_name"])
        seen.setdefault(key, []).append(tid)

    for (cat, name), tids in seen.items():
        if len(tids) <= 1:
            continue
        for i, tid in enumerate(tids):
            if i > 0 and i < len(_DEDUP_SUFFIXES):
                labels[tid]["display_name"] = f"{name}{_DEDUP_SUFFIXES[i]}"
            elif i > 0:
                labels[tid]["display_name"] = f"{name} (pt.{i})"

    return labels


def generate_query_labels(demo_personas_path: Path) -> dict[str, str]:
    """Generate Chinese labels for persona query_keys."""
    personas = json.loads(demo_personas_path.read_text(encoding="utf-8"))
    query_labels: dict[str, str] = {}

    # Chinese query templates mapped to persona categories
    query_templates = {
        "Food": ["hot pot recommendation", "best ramen near me", "sushi guide", "BBQ spots",
                 "pizza reviews", "tacos tuesday", "best brunch"],
        "Technology": ["AI trends 2026", "machine learning tutorial", "best LLM models",
                 "cloud migration tips", "cybersecurity news", "GPT alternatives"],
        "Education": ["grad school advice", "study abroad tips", "learn programming",
                 "MBA worth it", "PhD application guide", "GRE study plan"],
        "Gaming": ["best RPGs", "Steam sale picks", "PS5 games", "indie game gems",
                 "Elden Ring tips"],
        "Entertainment": ["must watch movies", "Netflix hidden gems", "best anime 2026",
                 "documentary picks", "what to watch"],
        "General": ["trending now", "recommended for you", "popular today", "top picks"],
    }

    # Assign query labels based on persona's cluster categories
    for persona in personas:
        # Use top topic to determine category
        top_topic = persona["top_topics"][0]["topic_id"]
        # Load the topic labels we just generated
        topic_labels = load_generated_labels()
        category = topic_labels.get(top_topic, {}).get("category", "General")
        templates = query_templates.get(category, query_templates["General"])

        # Read the actual query_keys from the persona profile seed
        profile_path = demo_personas_path.parent / "demo_persona_profile_seeds.json"
        profiles = json.loads(profile_path.read_text(encoding="utf-8"))
        for profile in profiles:
            if profile["user_id"] == persona["user_id"]:
                for i, q in enumerate(profile.get("recent_queries", [])):
                    key = q["query_key"]
                    if key not in query_labels:
                        query_labels[key] = templates[i % len(templates)]
                break

    return query_labels


def load_generated_labels() -> dict[int, dict]:
    """Load already-generated labels or return empty."""
    path = SCRIPT_DIR / "topic_labels.json"
    if path.exists():
        return {int(k): v for k, v in json.loads(path.read_text(encoding="utf-8")).items()}
    return {}


def write_templates_py() -> None:
    """Write templates.py with per-category Chinese content templates."""
    question_title_templates: dict[str, list[str]] = {
        "美食": [
            "关于{display_name}的讨论，大家怎么看？",
            "分享一家{topic_name}的好去处",
            "{topic_name}爱好者必看！这些经验很实用",
            "为什么越来越多人喜欢{topic_name}？",
            "{topic_name}的N种打开方式，你试过几种？",
        ],
        "科技": [
            "{topic_name}最新进展：一个深度分析",
            "浅谈{topic_name}的未来发展趋势",
            "{topic_name}在业界的应用与实践",
            "如何看待{topic_name}的突破性进展？",
            "关于{topic_name}，这些观点值得一读",
        ],
        "教育": [
            "{topic_name}经验分享，希望能帮到你",
            "关于{topic_name}的一些思考和建议",
            "{topic_name}方法论：从入门到精通",
            "谈谈{topic_name}对我的影响",
            "分享一些{topic_name}的实用资源",
        ],
        "财经": [
            "{topic_name}投资策略深度解析",
            "聊一聊{topic_name}的市场前景",
            "{topic_name}的底层逻辑是什么？",
            "关于{topic_name}的一点个人看法",
            "{topic_name}入门的几点建议",
        ],
        "游戏": [
            "{topic_name}深度测评与心得",
            "关于{topic_name}的一些攻略分享",
            "玩了{topic_name}之后的一些想法",
            "{topic_name}新手向指南",
            "为什么推荐你尝试{topic_name}？",
        ],
        "影视": [
            "推荐一部{topic_name}相关的作品",
            "谈谈{topic_name}中的精彩细节",
            "关于{topic_name}的一些个人感悟",
            "从{topic_name}看创作的魅力",
            "有没有类似{topic_name}的推荐？",
        ],
    }

    default_question_templates = [
        "关于{display_name}的热门讨论",
        "{display_name}相关分享与交流",
        "聊聊{display_name}那些事",
        "分享一些关于{display_name}的经验",
        "大家怎么看{display_name}这个话题？",
    ]

    answer_summary_templates: dict[str, list[str]] = {
        "美食": [
            "一家口碑不错的{topic_name}店铺，环境好味道正宗，值得一试。",
            "关于{topic_name}的详细体验分享，从菜品到服务都很到位。",
            "作为{topic_name}爱好者，推荐这几家性价比高的选择。",
            "周末打卡了这家{topic_name}，整体体验超出预期。",
            "分享一些{topic_name}的避坑经验，帮大家少走弯路。",
        ],
        "科技": [
            "关于{topic_name}的深度技术分析，适合有一定基础的同学阅读。",
            "{topic_name}领域的最新动态和发展方向解读。",
            "从实际案例出发，浅析{topic_name}的应用价值。",
            "一个详细的{topic_name}入门教程，内容通俗易懂。",
            "{topic_name}在产业界的落地实践与思考。",
        ],
        "教育": [
            "整理了一份{topic_name}的学习路径，希望对初学者有帮助。",
            "关于{topic_name}考试的一些备考心得和资料推荐。",
            "分享一下我在{topic_name}方面的经验和方法。",
            "推荐几个{topic_name}相关的优质资源和课程。",
            "谈谈{topic_name}对个人成长的帮助和启发。",
        ],
        "财经": [
            "关于{topic_name}的市场分析和投资逻辑分享。",
            "用数据说话，解读{topic_name}的长期价值。",
            "分享一下我对{topic_name}的几点判断和依据。",
            "整理了{topic_name}相关的关键指标和看点。",
            "从宏观角度分析{topic_name}的趋势与机会。",
        ],
    }

    default_summary_templates = [
        "关于{display_name}的一篇高质量回答，内容详实逻辑清晰。",
        "这个回答从多个角度分析了{display_name}，值得一读。",
        "一篇关于{display_name}的实用分享，内容经过整理和总结。",
        "来自社区的一篇关于{display_name}的精选回答。",
        "关于{display_name}的深度讨论，作者观点鲜明有理有据。",
    ]

    content = f'''"""Semantic content templates for demo world generation.

Provides template-based Chinese text generation for question titles,
answer summaries, and other display content. Templates are organized
by semantic category and designed to produce varied, realistic output.
"""

from __future__ import annotations

import random
from typing import Sequence

QUESTION_TITLE_TEMPLATES: dict[str, list[str]] = {json.dumps(question_title_templates, ensure_ascii=False, indent=4)}

DEFAULT_QUESTION_TEMPLATES: list[str] = {json.dumps(default_question_templates, ensure_ascii=False, indent=4)}

ANSWER_SUMMARY_TEMPLATES: dict[str, list[str]] = {json.dumps(answer_summary_templates, ensure_ascii=False, indent=4)}

DEFAULT_SUMMARY_TEMPLATES: list[str] = {json.dumps(default_summary_templates, ensure_ascii=False, indent=4)}


def question_title(topic_display_name: str, category: str, question_id: int, *, seed: int = 0) -> str:
    """Generate a Chinese question title for a given topic and category."""
    templates = QUESTION_TITLE_TEMPLATES.get(category, DEFAULT_QUESTION_TEMPLATES)
    rng = random.Random(seed + question_id)
    template = rng.choice(templates)
    return template.format(display_name=topic_display_name, topic_name=topic_display_name)


def answer_summary(topic_display_names: Sequence[str], category: str, answer_id: int, *, seed: int = 0) -> str:
    """Generate a Chinese answer summary based on topic names and category."""
    templates = ANSWER_SUMMARY_TEMPLATES.get(category, DEFAULT_SUMMARY_TEMPLATES)
    rng = random.Random(seed + answer_id)
    template = rng.choice(templates)
    topic_name = topic_display_names[0] if topic_display_names else category
    return template.format(display_name=topic_name, topic_name=topic_name)


def topic_display_label(topic_id: int, topic_labels: dict[int, dict]) -> str:
    """Look up display name for a topic, with fallback."""
    info = topic_labels.get(topic_id)
    if info:
        return info["display_name"]
    return f"话题 {{topic_id}}"


def topic_category(topic_id: int, topic_labels: dict[int, dict]) -> str:
    """Look up category for a topic, with fallback."""
    info = topic_labels.get(topic_id)
    if info:
        return info["category"]
    return "General"
'''

    path = SCRIPT_DIR / "templates.py"
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    cluster_path = SCRIPT_DIR / "clusters" / "topic_clusters.json"
    clusters = load_cluster_json(cluster_path)
    print(f"Loaded {len(clusters)} clusters from {cluster_path}")

    # Generate topic_labels.json
    topic_labels = generate_topic_labels(clusters)
    output = {str(k): v for k, v in sorted(topic_labels.items())}
    topic_path = SCRIPT_DIR / "topic_labels.json"
    topic_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(output)} topic labels to {topic_path}")

    # Count per category
    from collections import Counter
    cat_counts = Counter(v["category"] for v in topic_labels.values())
    for cat, cnt in cat_counts.most_common():
        print(f"  {cat}: {cnt}")

    # Generate query_labels.json
    demo_personas_path = Path("build/demo_world/demo_personas.json")
    if demo_personas_path.exists():
        query_labels = generate_query_labels(demo_personas_path)
        query_path = SCRIPT_DIR / "query_labels.json"
        query_path.write_text(json.dumps(query_labels, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {len(query_labels)} query labels to {query_path}")
    else:
        print(f"Skipping query_labels: {demo_personas_path} not found")

    # Write templates.py
    write_templates_py()

    print("Done. Review the generated files before committing.")


if __name__ == "__main__":
    main()
