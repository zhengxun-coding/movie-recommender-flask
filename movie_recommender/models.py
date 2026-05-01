from dataclasses import dataclass
from typing import Optional


@dataclass
class Movie:
    movie_id: int
    title: str
    overview: str
    release_year: Optional[int]
    genres: list[str]
    vote_average: float
    popularity: float
    poster_path: Optional[str] = None

    def genre_text(self) -> str:
        """将 genres 列表转为逗号拼接字符串。"""
        return ','.join(self.genres)


