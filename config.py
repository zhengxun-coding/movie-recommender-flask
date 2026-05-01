import os

TMDB_BEARER_TOKEN = os.environ.get("TMDB_BEARER_TOKEN", "")
SAMPLE_MOVIE_COUNT = 250

SAMPLE_USERS = [
    ("Alice", [(550988, 5), (155, 4), (27205, 5), (240, 4), (129, 4)]),
    ("Bob",   [(238, 5), (680, 4), (155, 5), (122, 4), (157336, 4)]),
    ("Cindy", [(129, 5), (372058, 5), (324857, 4), (496243, 4), (603, 4)]),
]
