import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

plt.rcParams['font.sans-serif'] = [
    'AR PL UMing CN', 'Droid Sans Fallback', 'WenQuanYi Micro Hei',
    'SimHei', 'Microsoft YaHei', 'DejaVu Sans'
]
plt.rcParams['axes.unicode_minus'] = False


def plot_rating_distribution(db, output_path: str = None) -> None:
    """生成用户评分分布图。"""
    if output_path is None:
        output_path = "static/images/rating_distribution.png"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    ratings = db.get_all_ratings()
    if not ratings:
        _generate_empty_chart("暂无评分数据", output_path)
        return

    rating_values = [r['rating'] for r in ratings]
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.hist(rating_values, bins=5, range=(1, 5), edgecolor='black', alpha=0.7, color='#667eea')
    ax.set_title('用户评分分布', fontsize=20, pad=15)
    ax.set_xlabel('评分', fontsize=16)
    ax.set_ylabel('数量', fontsize=16)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.tick_params(axis='both', labelsize=14)
    ax.grid(axis='y', alpha=0.75, linestyle='--')
    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches='tight')
    plt.close(fig)


def plot_genre_preference(db, output_path: str = None) -> None:
    """生成电影类型分布图。"""
    if output_path is None:
        output_path = "static/images/genre_preference.png"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    movies = db.get_all_movies()
    if not movies:
        _generate_empty_chart("暂无电影数据", output_path)
        return

    genre_counts = {}
    for movie in movies:
        for genre in movie.genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1

    if not genre_counts:
        _generate_empty_chart("暂无类型数据", output_path)
        return

    sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
    genres = [g[0] for g in sorted_genres[:12]]
    counts = [g[1] for g in sorted_genres[:12]]

    fig, ax = plt.subplots(figsize=(14, 7))
    bars = ax.bar(genres, counts, alpha=0.7, color='#764ba2')
    ax.set_title('电影类型分布', fontsize=20, pad=15)
    ax.set_xlabel('类型', fontsize=16)
    ax.set_ylabel('数量', fontsize=16)
    ax.tick_params(axis='x', labelsize=13, rotation=45)
    ax.tick_params(axis='y', labelsize=13)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.3,
                f'{int(bar.get_height())}', ha='center', va='bottom', fontsize=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches='tight')
    plt.close(fig)


def _generate_empty_chart(message: str, output_path: str) -> None:
    """生成空图表提示。"""
    fig = plt.figure(figsize=(10, 5))
    plt.text(0.5, 0.5, message, ha='center', va='center', fontsize=18)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close(fig)