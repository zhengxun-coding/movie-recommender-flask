from typing import Optional
import re


def clean_title(title: str) -> str:
    """清洗电影标题，去掉多余空格和特殊符号。"""
    title = title.strip()
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'[\"\'\/\\]', '', title)
    return title


def extract_year(date_text: str) -> Optional[int]:
    """从上映日期字符串中提取年份。"""
    if not date_text:
        return None
    match = re.search(r'(19|20)\d{2}', date_text)
    if match:
        return int(match.group())
    return None


def clean_overview(text: str) -> str:
    """清洗电影简介，去除 HTML 标签、多余换行、连续空格。"""
    if not text:
        return ""
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def parse_genres(genre_text: str) -> list[str]:
    """将类型字符串（如 'Action,Adventure,Sci-Fi' 或 '动作/科幻'）转为列表。"""
    if not genre_text:
        return []
    genres = re.split(r'[,/\\]+', genre_text)
    return [g.strip() for g in genres if g.strip()]