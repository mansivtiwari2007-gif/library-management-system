from flask import Flask, render_template, request, redirect, flash, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "library-app-secret"  # needed for flash messages


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
        password = request.form.get("password", "").strip()

        conn = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id, username FROM users WHERE username = %s AND password = %s",
                (username, password)
            )

            user = cursor.fetchone()

            if user:
                session["user_id"] = user[0]
                session["username"] = user[1]
                return redirect("/")

            return render_template(
                "login.html",
                error="Invalid username or password."
            )

        except Exception as err:
            print("Login error:", err)
            return render_template("login.html", error=str(err))

        finally:
            if conn is not None:
                conn.close()

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.before_request
def require_login():
    if request.endpoint in ["login", "static"]:
        return

    if "user_id" not in session:
        return redirect("/login")
def get_books():
    books = []
    error = None
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, author, category, available_copies FROM books")
        books = cursor.fetchall()
    except Exception as err:
        error = str(err)
        print("Database error:", error)
    finally:
        if conn is not None:
            conn.close()
    return books, error


@app.route("/")
def home():
    books, error = get_books()
    return render_template("index.html", books=books, error=error)


@app.route("/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "").strip()
        error = None

        try:
            available_copies = int(request.form.get("available_copies", 1) or 1)
        except ValueError:
            available_copies = 1

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO books (title, author, category, available_copies) VALUES (%s, %s, %s, %s)",
                (title, author, category, available_copies)
            )
            conn.commit()
            flash("Book added successfully!")
            return redirect("/")
        except Exception as err:
            print("Add book error:", err)
            error = str(err)
        finally:
            if conn is not None:
                conn.close()
        return render_template("add_book.html", error=error)
    return render_template("add_book.html")


@app.route("/delete/<int:book_id>")
def delete_book(book_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM books WHERE id = %s", (book_id,))
        conn.commit()
        flash("Book deleted successfully!")
    except Exception as err:
        print("Delete book error:", err)
    finally:
        if conn is not None:
            conn.close()
    return redirect("/")


@app.route("/edit/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    conn = None
    error = None
    book = None

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        category = request.form.get("category", "").strip()

        try:
            available_copies = int(request.form.get("available_copies", 1) or 1)
        except ValueError:
            available_copies = 1

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE books SET title = %s, author = %s, category = %s, available_copies = %s WHERE id = %s",
                (title, author, category, available_copies, book_id)
            )
            conn.commit()
            flash("Book updated successfully!")
            return redirect("/")
        except Exception as err:
            print("Edit book update error:", err)
            error = str(err)
        finally:
            if conn is not None:
                conn.close()

        return render_template("edit_book.html", book=book, error=error)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title, author, category, available_copies FROM books WHERE id = %s",
            (book_id,)
        )
        book = cursor.fetchone()
        if book is None:
            return redirect("/")
    except Exception as err:
        print("Edit book fetch error:", err)
        error = str(err)
    finally:
        if conn is not None:
            conn.close()

    if error:
        books, _ = get_books()
        return render_template("index.html", books=books, error=error)

    return render_template("edit_book.html", book=book)


def get_members():
    members = []
    error = None
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, phone, membership_date FROM members")
        members = cursor.fetchall()
    except Exception as err:
        error = str(err)
        print("Members database error:", error)
    finally:
        if conn is not None:
            conn.close()
    return members, error


@app.route("/members")
def members_page():
    members, error = get_members()
    return render_template("member.html", members=members, error=error)


@app.route('/members/add', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        membership_date = request.form.get("membership_date", "").strip()

        if not name or not email or not phone or not membership_date:
            return render_template("add_member.html", error="All fields are required.")

        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO members (name, email, phone, membership_date) VALUES (%s, %s, %s, %s)",
                (name, email, phone, membership_date)
            )
            conn.commit()
            flash("Member added successfully!")
            return redirect("/members")
        except Exception as err:
            print("Add member error:", err)
            return render_template("add_member.html", error=str(err))
        finally:
            if conn is not None:
                conn.close()

    return render_template("add_member.html")
@app.route('/members/delete/<int:member_id>')
def delete_member(member_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM members WHERE id = %s", (member_id,))
        conn.commit()
        flash("Member deleted successfully!")
    except Exception as err:
        print("Delete member error:", err)
        flash("Unable to delete member.")
    finally:
        if conn is not None:
            conn.close()
    return redirect("/members")


@app.route("/members/edit/<int:member_id>", methods=["GET", "POST"])
def edit_member(member_id):
    conn = None
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        membership_date = request.form.get("membership_date", "").strip()

        if not name or not email or not phone or not membership_date:
            return render_template("edit_member.html", member_id=member_id, error="All fields are required.")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE members SET name = %s, email = %s, phone = %s, membership_date = %s WHERE id = %s",
                (name, email, phone, membership_date, member_id)
            )
            conn.commit()
            flash("Member updated successfully!")
            return redirect("/members")
        except Exception as err:
            print("Edit member update error:", err)
            error = str(err)
        finally:
            if conn is not None:
                conn.close()

        return render_template("edit_member.html", member_id=member_id, error=error)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, phone, membership_date FROM members WHERE id = %s", (member_id,))
        member = cursor.fetchone()
        if member is None:
            return redirect("/members")
    except Exception as err:
        print("Edit member fetch error:", err)
        error = str(err)
    finally:
        if conn is not None:
            conn.close()

    if error:
        members, _ = get_members()
        return render_template("member.html", members=members, error=error)

    return render_template("edit_member.html", member=member)
# ================= ISSUE / RETURN =================

@app.route("/issue", methods=["GET", "POST"])
def issue_book():
    conn = None
    error = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Books with available copies
        cursor.execute(
            "SELECT id, title, available_copies FROM books WHERE available_copies > 0"
        )
        books = cursor.fetchall()

        # All members
        cursor.execute(
            "SELECT id, name FROM members"
        )
        members = cursor.fetchall()

        if request.method == "POST":
            book_id = request.form.get("book_id")
            member_id = request.form.get("member_id")
            issue_date = request.form.get("issue_date")
            due_date = request.form.get("due_date")

            if not book_id or not member_id or not issue_date or not due_date:
                return render_template(
                    "issue_book.html",
                    books=books,
                    members=members,
                    error="All fields are required."
                )

            # Add issue record
            cursor.execute(
                """
                INSERT INTO issue_return
                (book_id, member_id, issue_date, due_date)
                VALUES (%s, %s, %s, %s)
                """,
                (book_id, member_id, issue_date, due_date)
            )

            # Decrease available copies
            cursor.execute(
                """
                UPDATE books
                SET available_copies = available_copies - 1
                WHERE id = %s AND available_copies > 0
                """,
                (book_id,)
            )

            conn.commit()

            flash("Book issued successfully!")
            return redirect("/issue-return")

    except Exception as err:
        print("Issue book error:", err)
        error = str(err)

    finally:
        if conn is not None:
            conn.close()

    return render_template(
        "issue_book.html",
        books=books,
        members=members,
        error=error
    )


@app.route("/return/<int:issue_id>")
def return_book(issue_id):
    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get book id of issued record
        cursor.execute(
            """
            SELECT book_id
            FROM issue_return
            WHERE id = %s AND return_date IS NULL
            """,
            (issue_id,)
        )

        record = cursor.fetchone()

        if record is None:
            flash("Book already returned or record not found.")
            return redirect("/issue-return")

        book_id = record[0]

        # Set return date
        cursor.execute(
            """
            UPDATE issue_return
            SET return_date = CURDATE()
            WHERE id = %s
            """,
            (issue_id,)
        )

        # Increase available copies
        cursor.execute(
            """
            UPDATE books
            SET available_copies = available_copies + 1
            WHERE id = %s
            """,
            (book_id,)
        )

        conn.commit()

        flash("Book returned successfully!")

    except Exception as err:
        print("Return book error:", err)
        flash("Unable to return book.")

    finally:
        if conn is not None:
            conn.close()

    return redirect("/issue-return")


@app.route("/issue-return")
def issue_return_page():
    records = []
    error = None
    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                issue_return.id,
                books.title,
                members.name,
                issue_return.issue_date,
                issue_return.due_date,
                issue_return.return_date
            FROM issue_return
            JOIN books ON issue_return.book_id = books.id
            JOIN members ON issue_return.member_id = members.id
            ORDER BY issue_return.id DESC
            """
        )

        records = cursor.fetchall()

    except Exception as err:
        print("Issue-return database error:", err)
        error = str(err)

    finally:
        if conn is not None:
            conn.close()

    return render_template(
        "issue_return.html",
        records=records,
        error=error
    )
@app.route("/dashboard")
def dashboard():
    conn = None
    stats = {
        "total_books": 0,
        "total_members": 0,
        "issued_books": 0,
        "returned_books": 0
    }
    error = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM books")
        stats["total_books"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM members")
        stats["total_members"] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM issue_return WHERE return_date IS NULL"
        )
        stats["issued_books"] = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM issue_return WHERE return_date IS NOT NULL"
        )
        stats["returned_books"] = cursor.fetchone()[0]

    except Exception as err:
        print("Dashboard error:", err)
        error = str(err)

    finally:
        if conn is not None:
            conn.close()

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
