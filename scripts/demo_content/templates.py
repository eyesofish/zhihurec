"""Semantic content templates for demo world generation.

Provides template-based Chinese text generation for question titles,
answer summaries, and other display content. Templates are organized
by semantic category and designed to produce varied, realistic output.
"""

from __future__ import annotations

import random
from typing import Sequence

QUESTION_TITLE_TEMPLATES: dict[str, list[str]] = {
    "美食": [
        "关于{display_name}的讨论，大家怎么看？",
        "分享一家{topic_name}的好去处",
        "{topic_name}爱好者必看！这些经验很实用",
        "为什么越来越多人喜欢{topic_name}？",
        "{topic_name}的N种打开方式，你试过几种？"
    ],
    "科技": [
        "{topic_name}最新进展：一个深度分析",
        "浅谈{topic_name}的未来发展趋势",
        "{topic_name}在业界的应用与实践",
        "如何看待{topic_name}的突破性进展？",
        "关于{topic_name}，这些观点值得一读"
    ],
    "教育": [
        "{topic_name}经验分享，希望能帮到你",
        "关于{topic_name}的一些思考和建议",
        "{topic_name}方法论：从入门到精通",
        "谈谈{topic_name}对我的影响",
        "分享一些{topic_name}的实用资源"
    ],
    "财经": [
        "{topic_name}投资策略深度解析",
        "聊一聊{topic_name}的市场前景",
        "{topic_name}的底层逻辑是什么？",
        "关于{topic_name}的一点个人看法",
        "{topic_name}入门的几点建议"
    ],
    "游戏": [
        "{topic_name}深度测评与心得",
        "关于{topic_name}的一些攻略分享",
        "玩了{topic_name}之后的一些想法",
        "{topic_name}新手向指南",
        "为什么推荐你尝试{topic_name}？"
    ],
    "影视": [
        "推荐一部{topic_name}相关的作品",
        "谈谈{topic_name}中的精彩细节",
        "关于{topic_name}的一些个人感悟",
        "从{topic_name}看创作的魅力",
        "有没有类似{topic_name}的推荐？"
    ]
}

DEFAULT_QUESTION_TEMPLATES: list[str] = [
    "关于{display_name}的热门讨论",
    "{display_name}相关分享与交流",
    "聊聊{display_name}那些事",
    "分享一些关于{display_name}的经验",
    "大家怎么看{display_name}这个话题？"
]

ANSWER_SUMMARY_TEMPLATES: dict[str, list[str]] = {
    "美食": [
        "一家口碑不错的{topic_name}店铺，环境好味道正宗，值得一试。",
        "关于{topic_name}的详细体验分享，从菜品到服务都很到位。",
        "作为{topic_name}爱好者，推荐这几家性价比高的选择。",
        "周末打卡了这家{topic_name}，整体体验超出预期。",
        "分享一些{topic_name}的避坑经验，帮大家少走弯路。"
    ],
    "科技": [
        "关于{topic_name}的深度技术分析，适合有一定基础的同学阅读。",
        "{topic_name}领域的最新动态和发展方向解读。",
        "从实际案例出发，浅析{topic_name}的应用价值。",
        "一个详细的{topic_name}入门教程，内容通俗易懂。",
        "{topic_name}在产业界的落地实践与思考。"
    ],
    "教育": [
        "整理了一份{topic_name}的学习路径，希望对初学者有帮助。",
        "关于{topic_name}考试的一些备考心得和资料推荐。",
        "分享一下我在{topic_name}方面的经验和方法。",
        "推荐几个{topic_name}相关的优质资源和课程。",
        "谈谈{topic_name}对个人成长的帮助和启发。"
    ],
    "财经": [
        "关于{topic_name}的市场分析和投资逻辑分享。",
        "用数据说话，解读{topic_name}的长期价值。",
        "分享一下我对{topic_name}的几点判断和依据。",
        "整理了{topic_name}相关的关键指标和看点。",
        "从宏观角度分析{topic_name}的趋势与机会。"
    ]
}

DEFAULT_SUMMARY_TEMPLATES: list[str] = [
    "关于{display_name}的一篇高质量回答，内容详实逻辑清晰。",
    "这个回答从多个角度分析了{display_name}，值得一读。",
    "一篇关于{display_name}的实用分享，内容经过整理和总结。",
    "来自社区的一篇关于{display_name}的精选回答。",
    "关于{display_name}的深度讨论，作者观点鲜明有理有据。"
]


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
    return f"话题 {topic_id}"


def topic_category(topic_id: int, topic_labels: dict[int, dict]) -> str:
    """Look up category for a topic, with fallback."""
    info = topic_labels.get(topic_id)
    if info:
        return info["category"]
    return "General"
