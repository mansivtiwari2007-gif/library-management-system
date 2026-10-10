import os
from datetime import date
from functools import wraps

import psycopg
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash
)
from psycopg.rows import dict_row

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "library-project-secret-key")


# PostgreSQL connection on Render
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="library_db",
        use_pure=True  # required on Python 3.14: C extension segfaults during connect
    )
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, username, password FROM users "
                        "WHERE username = %s",
                        (username,)
                    )
                    user = cur.fetchone()

            if user and user["password"] == password:
                session["username"] = user["username"]
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))

            flash("Invalid username or password.")

        except Exception as e:
            app.logger.exception("Login database error")
            flash("Database connection error. Please check Render logs.")

    return render_template("login.html")


# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS total FROM books")
                total_books = cur.fetchone()["total"]

                cur.execute("SELECT COUNT(*) AS total FROM members")
                total_members = cur.fetchone()["total"]

                cur.execute("""
                    SELECT COUNT(*) AS total FROM issue_return
                    WHERE return_date IS NULL
                """)
                issued_books = cur.fetchone()["total"]

                cur.execute("""
                    SELECT COUNT(*) AS total FROM issue_return
                    WHERE return_date IS NOT NULL
                """)
                returned_books = cur.fetchone()["total"]

        return render_template(
            "dashboard.html",
            total_books=total_books,
            total_members=total_members,
            issued_books=issued_books,
            returned_books=returned_books,
            username=session["username"]
        )

    except Exception:
        app.logger.exception("Dashboard database error")
        return "Database error. Please check Render logs.", 500


# View books
@app.route("/books")
@login_required
def books():
    search = request.args.get("search", "").strip()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if search:
                cur.execute("""
                    SELECT * FROM books
                    WHERE title ILIKE %s OR author ILIKE %s
                    ORDER BY id DESC
                """, (f"%{search}%", f"%{search}%"))
            else:
                cur.execute("SELECT * FROM books ORDER BY id DESC")

            all_books = cur.fetchall()

    return render_template("books.html", books=all_books, search=search)


# Add book
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_book():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        quantity = request.form.get(
            "quantity", request.form.get("copies", "1")
        )

        try:
            quantity = int(quantity)
            if not title or not author or quantity < 0:
                flash("Please enter valid book details.")
            else:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO books (title, author, quantity)
                            VALUES (%s, %s, %s)
                        """, (title, author, quantity))

                flash("Book added successfully!")
                return redirect(url_for("books"))

        except ValueError:
            flash("Quantity must be a valid number.")
        except Exception:
            app.logger.exception("Add book error")
            flash("Could not add book. Please check the details.")

    return render_template("add_book.html")


# Delete book
@app.route("/delete_book/<int:book_id>", methods=["POST", "GET"])
@login_required
def delete_book(book_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) AS total FROM issue_return
                    WHERE book_id = %s AND return_date IS NULL
                """, (book_id,))
                active = cur.fetchone()["total"]

                if active:
                    flash("Return this book before deleting it.")
                else:
                    cur.execute("DELETE FROM books WHERE id = %s", (book_id,))
                    flash("Book deleted successfully.")

    except Exception:
        app.logger.exception("Delete book error")
        flash("Could not delete this book.")

    return redirect(url_for("books"))


# View members
@app.route("/members")
@login_required
def members():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM members ORDER BY id DESC")
            all_members = cur.fetchall()

    return render_template("members.html", members=all_members)


# Add member
@app.route("/add_member", methods=["GET", "POST"])
@login_required
def add_member():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name:
            flash("Member name is required.")
        else:
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO members (name, email, phone)
                            VALUES (%s, %s, %s)
                        """, (name, email, phone))

                flash("Member added successfully!")
                return redirect(url_for("members"))

            except Exception:
                app.logger.exception("Add member error")
                flash("Could not add member.")

    return render_template("add_member.html")


# Delete member
@app.route("/delete_member/<int:member_id>", methods=["POST", "GET"])
@login_required
def delete_member(member_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) AS total FROM issue_return
                    WHERE member_id = %s AND return_date IS NULL
                """, (member_id,))
                active = cur.fetchone()["total"]

                if active:
                    flash("This member has an unreturned book.")
                else:
                    cur.execute(
                        "DELETE FROM members WHERE id = %s",
                        (member_id,)
                    )
                    flash("Member deleted successfully.")

    except Exception:
        app.logger.exception("Delete member error")
        flash("Could not delete this member.")

    return redirect(url_for("members"))


# Issue a book
@app.route("/issue", methods=["GET", "POST"])
@login_required
def issue_book():
    if request.method == "POST":
        try:
            book_id = int(request.form.get("book_id", "0"))
            member_id = int(request.form.get("member_id", "0"))

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, quantity FROM books
                        WHERE id = %s FOR UPDATE
                    """, (book_id,))
                    book = cur.fetchone()

                    cur.execute(
                        "SELECT id FROM members WHERE id = %s",
                        (member_id,)
                    )
                    member = cur.fetchone()

                    if not book or not member:
                        flash("Please select a valid book and member.")
                    elif book["quantity"] < 1:
                        flash("This book is not available.")
                    else:
                        cur.execute("""
                            INSERT INTO issue_return
                                (book_id, member_id, issue_date)
                            VALUES (%s, %s, CURRENT_DATE)
                        """, (book_id, member_id))

                        cur.execute("""
                            UPDATE books SET quantity = quantity - 1
                            WHERE id = %s
                        """, (book_id,))

                        flash("Book issued successfully!")
                        return redirect(url_for("issued_books"))

        except (ValueError, TypeError):
            flash("Please select a valid book and member.")
        except Exception:
            app.logger.exception("Issue book error")
            flash("Could not issue book.")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM books ORDER BY title")
            all_books = cur.fetchall()

            cur.execute("SELECT * FROM members ORDER BY name")
            all_members = cur.fetchall()

    return render_template(
        "issue.html", books=all_books, members=all_members
    )


# View issued and returned books
@app.route("/issued")
@login_required
def issued_books():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ir.*, b.title AS book_title,
                       m.name AS member_name
                FROM issue_return ir
                LEFT JOIN books b ON b.id = ir.book_id
                LEFT JOIN members m ON m.id = ir.member_id
                ORDER BY ir.id DESC
            """)
            records = cur.fetchall()

    return render_template("issued.html", records=records, issues=records)


# Return a book
@app.route("/return/<int:issue_id>", methods=["POST", "GET"])
@login_required
def return_book(issue_id):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, book_id, issue_date, return_date
                    FROM issue_return
                    WHERE id = %s FOR UPDATE
                """, (issue_id,))
                record = cur.fetchone()

                if not record:
                    flash("Issue record not found.")
                elif record["return_date"] is not None:
                    flash("This book has already been returned.")
                else:
                    cur.execute("""
                        UPDATE issue_return
                        SET return_date = CURRENT_DATE
                        WHERE id = %s
                    """, (issue_id,))

                    cur.execute("""
                        UPDATE books SET quantity = quantity + 1
                        WHERE id = %s
                    """, (record["book_id"],))

                    flash("Book returned successfully!")

    except Exception:
        app.logger.exception("Return book error")
        flash("Could not return book.")

    return redirect(url_for("issued_books"))


# Fine calculator
@app.route("/fine", methods=["GET", "POST"])
@login_required
def fine_calculator():
    fine = None
    days_late = None

    if request.method == "POST":
        issue_date = request.form.get("issue_date", "")
        return_date = request.form.get("return_date", "")
        daily_fine = request.form.get("daily_fine", "5")

        try:
            start = date.fromisoformat(issue_date)
            end = date.fromisoformat(return_date)
            rate = float(daily_fine)

            if rate < 0 or end < start:
                raise ValueError

            days_late = max((end - start).days - 14, 0)
            fine = days_late * rate

        except (ValueError, TypeError):
            flash("Please enter valid dates and fine amount.")

    return render_template(
        "dashboard.html",
        stats=stats,
        error=error
    )
@app.route("/search")
def search_books():
    query = request.args.get("q", "").strip()
    books = []
    error = None
    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if query:
            cursor.execute(
                """
                SELECT id, title, author, category, available_copies
                FROM books
                WHERE title LIKE %s
                   OR author LIKE %s
                   OR category LIKE %s
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%")
            )
        else:
            cursor.execute(
                "SELECT id, title, author, category, available_copies FROM books"
            )

        books = cursor.fetchall()

    except Exception as err:
        print("Search error:", err)
        error = str(err)

    finally:
        if conn is not None:
            conn.close()

    return render_template(
        "search.html",
        books=books,
        query=query,
        error=error
    )
@app.route("/fine-calculator")
def fine_calculator():
    return render_template("fine_calculator.html")


if __name__ == "__main__":
    app.run(debug=True)
