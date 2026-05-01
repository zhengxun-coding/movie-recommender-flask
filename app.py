from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
import sys
import re
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from movie_recommender.database import Database
from movie_recommender.recommender import ContentBasedRecommender, CollaborativeFilteringRecommender
from movie_recommender import visualization
from config import TMDB_BEARER_TOKEN, SAMPLE_MOVIE_COUNT, SAMPLE_USERS
from movie_recommender import fetcher


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'movie-recommender-secret-key-change-me')
db = Database()


def _safe_filename(filename):
    """安全的文件名，防止路径遍历"""
    return re.sub(r'[^a-zA-Z0-9._-]', '', filename)


@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    user_name = None
    if user_id:
        users = db.get_all_users()
        for u in users:
            if u['user_id'] == user_id:
                user_name = u['name']
                break
    return dict(user_name=user_name)


@app.route('/')
def index():
    users = db.get_all_users()
    movies = db.get_all_movies()
    ratings = db.get_all_ratings()
    return render_template('index.html', users=users, movie_count=len(movies), rating_count=len(ratings))


@app.route('/movies')
def movies():
    all_movies = db.get_all_movies()
    years = sorted(set(m.release_year for m in all_movies if m.release_year), reverse=True)
    user_ratings = {r['movie_id']: r['rating'] for r in db.get_all_ratings() if r['user_id'] == session.get('user_id')}
    return render_template('movies.html', movies=all_movies, years=years, user_ratings=user_ratings)


@app.route('/login/<int:user_id>')
def login(user_id):
    users = db.get_all_users()
    if any(u['user_id'] == user_id for u in users):
        session['user_id'] = user_id
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))


@app.route('/recommend/<int:user_id>')
def recommend(user_id):
    users = db.get_all_users()
    user = next((u for u in users if u['user_id'] == user_id), None)
    if not user:
        return redirect(url_for('index'))

    session['user_id'] = user_id

    user_ratings = {r['movie_id']: r['rating'] for r in db.get_all_ratings() if r['user_id'] == user_id}

    content_rec = ContentBasedRecommender(db)
    cf_rec = CollaborativeFilteringRecommender(db)

    genre_recs = content_rec.recommend_by_genre_preference(user_id, top_n=5)
    cf_recs = cf_rec.recommend_by_collaborative_filtering(user_id, top_n=5)

    return render_template('recommend.html',
                           genre_recs=genre_recs,
                           cf_recs=cf_recs,
                           user_id=user_id,
                           user_name=user['name'],
                           user_ratings=user_ratings)


@app.route('/charts/<int:user_id>')
def charts(user_id):
    users = db.get_all_users()
    user = next((u for u in users if u['user_id'] == user_id), None)
    if not user:
        return redirect(url_for('index'))

    if session.get('user_id') != user_id:
        session['user_id'] = user_id

    # 只在图片不存在时生成，避免每次请求都重新生成
    rating_chart_path = Path("static/images/rating_distribution.png")
    genre_chart_path = Path("static/images/genre_preference.png")
    if not rating_chart_path.exists() or not genre_chart_path.exists():
        Path("static/images").mkdir(parents=True, exist_ok=True)
        visualization.plot_rating_distribution(db)
        visualization.plot_genre_preference(db)

    ratings = db.get_all_ratings()
    rating_counts = Counter(round(r['rating']) for r in ratings)
    rating_labels = ['1', '2', '3', '4', '5']
    rating_values = [rating_counts.get(i, 0) for i in range(1, 6)]

    movies = db.get_all_movies()
    genre_counts = Counter()
    for movie in movies:
        for genre in (movie.genres or []):
            genre_counts[genre] += 1
    genre_labels = list(genre_counts.keys())[:10]
    genre_values = [genre_counts[g] for g in genre_labels]

    return render_template('charts.html',
                           user_id=user_id,
                           user_name=user['name'],
                           rating_labels=rating_labels,
                           rating_values=rating_values,
                           genre_labels=genre_labels,
                           genre_values=genre_values)


@app.route('/init')
def init_route():
    """Initialize database and import movie data."""
    existing = db.get_all_movies()
    if not existing:
        if TMDB_BEARER_TOKEN:
            movies = fetcher.fetch_all_movies(TMDB_BEARER_TOKEN, SAMPLE_MOVIE_COUNT)
        else:
            movies = fetcher.load_sample_movies()
        db.insert_movies(movies)

    users = db.get_all_users()
    if not users:
        for name, ratings in SAMPLE_USERS:
            user_id = db.create_user(name)
            for movie_id, rating in ratings:
                if db.movie_exists(movie_id):
                    db.add_or_update_rating(user_id, movie_id, rating)

    return redirect(url_for('index'))


@app.route('/user/add', methods=['POST'])
def add_user():
    name = request.form.get('name', '').strip()
    if not name:
        return redirect(url_for('index'))
    try:
        db.create_user(name)
    except Exception as e:
        print(f"创建用户失败: {e}")
    return redirect(url_for('index'))


@app.route('/api/rate', methods=['POST'])
def api_rate():
    """API endpoint for rating movies from the modal popup."""
    user_id = session.get('user_id')
    if not user_id:
        return {'error': '请先登录'}, 401

    movie_id = request.form.get('movie_id', type=int)
    rating = request.form.get('rating', type=float)

    if not movie_id or not rating:
        return {'error': '缺少参数'}, 400

    if not 1 <= rating <= 5:
        return {'error': '评分必须是1-5'}, 400

    try:
        db.add_or_update_rating(user_id, movie_id, rating)
        return {'success': True, 'rating': rating}
    except ValueError as e:
        return {'error': str(e)}, 400


@app.route('/posters/<filename>')
def serve_poster(filename):
    return send_from_directory(str(Path(__file__).parent / 'data' / 'posters'), _safe_filename(filename))


if __name__ == '__main__':
    app.run(debug=True)
