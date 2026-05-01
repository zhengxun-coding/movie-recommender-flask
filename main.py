#!/usr/bin/env python3
"""Movie Recommender 命令行工具

用法:
    python3 main.py init                # 从 TMDB API 初始化数据库
    python3 main.py sample            # 使用内置示例数据初始化
    python3 main.py posters           # 下载电影海报
    python3 main.py add-user <name>   # 添加用户
    python3 main.py rate <user> <movie_id> <rating>  # 给电影评分
    python3 main.py recommend <user>   # 获取推荐
    python3 main.py charts <user>      # 生成图表
"""

import argparse
import sys
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from movie_recommender.database import Database
from movie_recommender import fetcher
from movie_recommender import visualization
from movie_recommender.recommender import ContentBasedRecommender, CollaborativeFilteringRecommender
from config import TMDB_BEARER_TOKEN, SAMPLE_MOVIE_COUNT, SAMPLE_USERS


def cmd_init():
    """从 TMDB API 获取电影数据初始化数据库（增量：已有的不重复，没有的补上）。"""
    if not TMDB_BEARER_TOKEN:
        print("错误: 请先配置 TMDB_BEARER_TOKEN 环境变量")
        print("提示: 如果想使用示例数据，请运行: make sample")
        return

    print("正在初始化数据库...")
    db = Database()

    existing_ids = {m.movie_id for m in db.get_all_movies()}
    print(f"数据库中已有 {len(existing_ids)} 部电影")

    print(f"正在从 TMDB API 获取电影数据（Token: {TMDB_BEARER_TOKEN[:8]}...）...")
    movies = fetcher.fetch_all_movies(TMDB_BEARER_TOKEN, count=SAMPLE_MOVIE_COUNT)

    movies_to_add = [m for m in movies if m.movie_id not in existing_ids]
    if movies_to_add:
        print(f"正在导入 {len(movies_to_add)} 部新电影...")
        db.insert_movies(movies_to_add)
        print("电影数据导入完成。")
    else:
        print("所有电影已在数据库中，跳过导入。")

    users = db.get_all_users()
    if not users:
        print("创建示例用户和评分...")
        for name, ratings in SAMPLE_USERS:
            user_id = db.create_user(name)
            print(f"  创建用户: {name} (ID: {user_id})")
            for movie_id, rating in ratings:
                if db.movie_exists(movie_id):
                    db.add_or_update_rating(user_id, movie_id, rating)
        print("示例数据和评分创建完成。")
    else:
        print(f"已有 {len(users)} 个用户，跳过创建示例用户。")

    print("正在生成可视化图表...")
    Path("static/images").mkdir(parents=True, exist_ok=True)
    visualization.plot_rating_distribution(db)
    visualization.plot_genre_preference(db)
    print("初始化完成！")


def cmd_sample():
    """使用内置示例数据初始化数据库（增量：已有的不重复，没有的补上）。"""
    print("正在使用内置示例数据初始化数据库...")
    db = Database()

    existing_ids = {m.movie_id for m in db.get_all_movies()}
    movies_to_add = []
    for m in fetcher.load_sample_movies():
        if m.movie_id not in existing_ids:
            movies_to_add.append(m)

    if movies_to_add:
        print(f"正在导入 {len(movies_to_add)} 部新电影...")
        db.insert_movies(movies_to_add)
        print("电影数据导入完成。")
    else:
        print("数据库中已有示例电影，跳过导入。")

    users = db.get_all_users()
    if not users:
        print("创建示例用户和评分...")
        for name, ratings in SAMPLE_USERS:
            user_id = db.create_user(name)
            print(f"  创建用户: {name} (ID: {user_id})")
            for movie_id, rating in ratings:
                if db.movie_exists(movie_id):
                    db.add_or_update_rating(user_id, movie_id, rating)
        print("示例数据和评分创建完成。")
    else:
        print(f"已有 {len(users)} 个用户，跳过创建示例用户。")

    print("正在生成可视化图表...")
    Path("static/images").mkdir(parents=True, exist_ok=True)
    visualization.plot_rating_distribution(db)
    visualization.plot_genre_preference(db)
    print("初始化完成！")


def cmd_download_posters():
    """下载电影海报。"""
    if not TMDB_BEARER_TOKEN:
        print("错误: TMDB_BEARER_TOKEN 未设置，无法下载海报")
        print("提示: 请先配置 TMDB_BEARER_TOKEN 环境变量")
        return

    db = Database()
    movies = db.get_all_movies()
    if not movies:
        print("数据库为空，请先运行: python3 main.py init")
        return

    POSTERS_DIR = Path(__file__).parent / "data" / "posters"
    POSTERS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"共 {len(movies)} 部电影，开始下载海报...")

    headers = {"Authorization": f"Bearer {TMDB_BEARER_TOKEN}"}
    TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
    success_count = 0
    skip_count = 0

    for movie in movies:
        local_path = POSTERS_DIR / f"{movie.movie_id}.jpg"
        if local_path.exists():
            skip_count += 1
            continue

        try:
            resp = requests.get(
                f"https://api.themoviedb.org/3/movie/{movie.movie_id}",
                headers=headers,
                timeout=15
            )
            resp.raise_for_status()
            details = resp.json()
            poster_path = details.get("poster_path")

            if poster_path:
                img_resp = requests.get(
                    f"{TMDB_IMAGE_BASE}{poster_path}",
                    timeout=30
                )
                img_resp.raise_for_status()
                with open(local_path, "wb") as f:
                    f.write(img_resp.content)
                print(f"  ✓ {details.get('title', movie.movie_id)}")
                success_count += 1
            else:
                print(f"  ✗ 无海报: {movie.movie_id}")

        except Exception as e:
            print(f"  ✗ 失败 ({movie.movie_id}): {e}")

    print(f"\n完成! 成功下载 {success_count} 张，跳过 {skip_count} 张已有海报")


def cmd_add_user(name: str):
    """添加新用户。"""
    db = Database()
    try:
        user_id = db.create_user(name)
        print(f"用户创建成功: {name} (ID: {user_id})")
    except Exception as e:
        print(f"创建用户失败: {e}")


def cmd_rate(user_name: str, movie_id: int, rating: float):
    """给电影评分。"""
    if not 1 <= rating <= 5:
        print(f"错误: 评分必须在 1-5 之间，当前值: {rating}")
        return
    db = Database()
    users = db.get_all_users()
    user = next((u for u in users if u['name'] == user_name), None)
    if not user:
        user_id = db.create_user(user_name)
        print(f"创建新用户: {user_name} (ID: {user_id})")
    else:
        user_id = user['user_id']
    try:
        db.add_or_update_rating(user_id, movie_id, rating)
        print(f"评分成功: {user_name} 对电影 {movie_id} 评 {rating} 分")
    except ValueError as e:
        print(f"评分失败 (数据错误): {e}")
    except Exception as e:
        print(f"评分失败 (系统错误): {type(e).__name__}: {e}")


def cmd_recommend(user_name: str):
    """获取推荐。"""
    db = Database()
    users = db.get_all_users()
    user = next((u for u in users if u['name'] == user_name), None)
    if not user:
        print(f"用户 {user_name} 不存在")
        return
    user_id = user['user_id']

    content_rec = ContentBasedRecommender(db)
    cf_rec = CollaborativeFilteringRecommender(db)

    print(f"\n=== 基于类型偏好的推荐 (用户: {user_name}) ===")
    genre_recs = content_rec.recommend_by_genre_preference(user_id, top_n=5)
    for r in genre_recs:
        print(f"  [{r['method']}] {r['movie'].title} (score: {r['score']})")

    print(f"\n=== 基于协同过滤的推荐 (用户: {user_name}) ===")
    cf_recs = cf_rec.recommend_by_collaborative_filtering(user_id, top_n=5)
    for r in cf_recs:
        print(f"  [{r['method']}] {r['movie'].title} (score: {r['score']})")


def cmd_charts(user_name: str):
    """生成可视化图表。"""
    db = Database()
    users = db.get_all_users()
    user = next((u for u in users if u['name'] == user_name), None)
    if not user:
        print(f"用户 {user_name} 不存在")
        return
    user_id = user['user_id']

    Path("static/images").mkdir(parents=True, exist_ok=True)
    visualization.plot_rating_distribution(db)
    visualization.plot_genre_preference(db)
    print(f"图表已生成到 static/images/ 目录")


def main():
    parser = argparse.ArgumentParser(description="Movie Recommender CLI")
    subparsers = parser.add_subparsers(dest='command')

    p_init = subparsers.add_parser('init', help='从 TMDB API 初始化数据库')
    p_sample = subparsers.add_parser('sample', help='使用内置示例数据初始化')
    p_posters = subparsers.add_parser('posters', help='下载电影海报')
    p_add = subparsers.add_parser('add-user', help='添加用户')
    p_add.add_argument('name', help='用户名')
    p_rate = subparsers.add_parser('rate', help='给电影评分')
    p_rate.add_argument('user')
    p_rate.add_argument('movie_id', type=int)
    p_rate.add_argument('rating', type=float)
    p_rec = subparsers.add_parser('recommend', help='获取推荐')
    p_rec.add_argument('user', help='用户名')
    p_charts = subparsers.add_parser('charts', help='生成图表')
    p_charts.add_argument('user', help='用户名')

    args = parser.parse_args()

    if args.command == 'init':
        cmd_init()
    elif args.command == 'sample':
        cmd_sample()
    elif args.command == 'posters':
        cmd_download_posters()
    elif args.command == 'add-user':
        cmd_add_user(args.name)
    elif args.command == 'rate':
        cmd_rate(args.user, args.movie_id, args.rating)
    elif args.command == 'recommend':
        cmd_recommend(args.user)
    elif args.command == 'charts':
        cmd_charts(args.user)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()