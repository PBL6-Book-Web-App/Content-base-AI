from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_cors import CORS, cross_origin
import os

database_url = os.environ.get("DATABASE_URL")

app = Flask(__name__)
# Apply Flask CORS
CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

# Thông tin kết nối đến cơ sở dữ liệu
DB_HOST = os.environ.get("DB_HOST", "default_host")
DB_PORT = int(os.environ.get("DB_PORT", 5432))
DB_USER = os.environ.get("DB_USER", "default_user")
DB_PASS = os.environ.get("DB_PASS", "default_password")
DB_NAME = os.environ.get("DB_NAME", "default_database")


# Hàm kết nối đến cơ sở dữ liệu và thực hiện truy vấn
def query_db(query, params=None):
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


# Giả sử hàm này sử dụng mô hình AI của bạn để tìm ra 10 sách liên quan từ một ID sách
def get_recommended_book_ids(book_id):
    # Đây chỉ là ví dụ, bạn cần thay thế bằng mã xử lý AI thực sự của mình
    # Ở đây, tôi sẽ trả về 10 ID sách giả định
    return [
        "247293",
        "249178",
        "249166",
        "0812568710",
        "1570714347",
        "0385483872",
        "0590433369",
        "0307001164",
        "263694",
        "0809288346",
    ]


# API để trả về danh sách sách dựa trên danh sách id
@app.route("/content-based-recommend/<int:book_id>", methods=["GET"])
@cross_origin(origin="*")  # Fix to current web domain
def get_books(book_id):
    if not book_id:
        return jsonify({"error": "No book ID provided"}), 400

    recommend_books = get_recommended_book_ids(book_id)

    # Truy vấn thông tin sách và tác giả từ cơ sở dữ liệu
    books_query = """
        SELECT
            b.id,
            b.title,
            b.book_cover AS "bookCover",
            b.language,
            b.image_url AS "imageUrl",
            b.release_date AS "releaseDate",
            b.price,
            b.average_rating AS "averageRating",
            b.source_id,
            json_agg(
                json_build_object(
                    'author', json_build_object(
                        'id', a.id,
                        'name', a.name,
                        'avatar', a.avatar
                    )
                )
            ) AS authors
        FROM book b
        LEFT JOIN author_to_book atb ON b.id = atb.book_id
        LEFT JOIN author a ON atb.author_id = a.id
        WHERE b.id = ANY(%s)
        GROUP BY b.id
    """
    books = query_db(books_query, (recommend_books,))

    # Truy vấn thông tin nguồn từ cơ sở dữ liệu
    source_ids = [book["source_id"] for book in books]
    sources_query = """
        SELECT id, name
        FROM source
        WHERE id = ANY(%s)
    """
    sources = {
        source["id"]: source for source in query_db(sources_query, (source_ids,))
    }

    # Truy vấn thông tin tương tác từ cơ sở dữ liệu
    interactions_query = """
        SELECT
            i.book_id,
            json_agg(
                json_build_object(
                    'user_id', i.user_id,
                    'type', i.type,
                    'value', i.value
                )
            ) AS interactions
        FROM interaction i
        WHERE i.book_id = ANY(%s)
        GROUP BY i.book_id
    """
    interactions = {
        interaction["book_id"]: interaction["interactions"]
        for interaction in query_db(interactions_query, (recommend_books,))
    }

    # Kết hợp thông tin nguồn và interactions vào dữ liệu sách
    for book in books:
        book["source"] = sources.get(
            book["source_id"], {"id": book["source_id"], "name": "Unknown"}
        )
        book["interactions"] = interactions.get(book["id"], [])

    return jsonify({"data": books})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
