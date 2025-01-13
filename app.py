from flask import Flask, request,  jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user,UserMixin


app = Flask(__name__)
app.secret_key="something something"
app.config['SQLALCHEMY_DATABASE_URI']= 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
#git changes
db = SQLAlchemy(app)
loginManager = LoginManager()
loginManager.init_app(app)

class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    user_role = db.Column(db.String(10), nullable=False)

    @staticmethod
    def get_by_username(username):
        return Users.query.filter_by(username=username).first()

    @staticmethod   
    def get_by_id(user_id):
        return Users.query.get(user_id)

@loginManager.user_loader
def load_user(user_id):
    return Users.get_by_id(user_id)

@app.before_request
def set_default_content_type():
    if not request.content_type:
        request.environ['CONTENT_TYPE'] = 'application/json'

class Book(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    title = db.Column(db.String(50),nullable=False)
    author = db.Column(db.String(100))
    genre = db.Column(db.String(30))
    available = db.Column(db.Integer,default=0)

@app.route('/')
def index():
    return jsonify({"message":"Welcome to the Library Management System"})
    
@app.route('/authenticate',methods = ['POST'])
def authenticate():
    data = request.json
    if not data:
            return jsonify({"error":"No JSON Object Found"}), 401
    username = data.get('username')
    password = data.get('password')
    userRole = data.get('Role')
    if not username or not password or not userRole:
        return jsonify({"error": "Complete Data not Found"}), 401
    user = Users.get_by_username(username)
    print(user)
    if user and user.password == password and user.user_role == userRole:
        login_user(user)
        if user.user_role == 'Admin':
            return jsonify({"message": f"Welcome Admin {user.id}"}), 200
        elif user.user_role=="User":
            return jsonify({"message": f"Welcome User {user.id}"}), 200
        else:
            return jsonify({"message": f"Something Went Wrong"}), 401
    return jsonify({"message": f"Wrong Credentials"}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"message":"Logged Out Successfully"}), 200

def serialize_book(book):
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "genre": book.genre,
        "available": book.available,
    }

@app.route('/admin/books', methods = ['GET','POST'])
@login_required
def addBook():
    if(current_user.user_role!="Admin"):
        return jsonify({"message": "Unauthorized Access"}), 401
    if request.method== 'POST':
        data  = request.json
        if not data:
            return jsonify({"error":"No JSON Object Found"}), 401
        authot = ""
        genre = ""
        availability=0
        title=data.get('title')
        author = data.get('author')
        genre = data.get('genre')
        availability = data.get('available')
        if not title:
            return jsonify({"error":"Title Not Found"}), 401
        if not Book.query.filter_by(title = data.get('title')).first():
            book = Book(title=title, author=author,genre=genre,available=availability)
            db.session.add(book)
            db.session.commit()
            return jsonify({"message": "Book Added Successfully"}), 200
        else:
            return jsonify({"message":"Book Not added or may exist already"}), 401
    elif request.method =='GET':
        books = Book.query.all()
        serialized = [serialize_book(book) for book in books]
        return jsonify({"books": serialized})

@app.route('/admin/books/<int:book_id>', methods = ['PUT','DELETE'])
@login_required
def updateBook(book_id):
    if(current_user.user_role!="Admin"):
        return jsonify({"message": "Unauthorized Access"}), 401
    if request.method=='PUT':
        book = Book.query.get(book_id)
        if not book:
            return jsonify({"error": "Book not found"}), 404
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request, JSON body is required"}), 400
        book.title = data.get('title', book.title)
        book.author = data.get('author', book.author)
        book.genre = data.get('genre', book.genre)
        book.available = data.get('available', book.available)
        db.session.commit()
        return jsonify({"Message": f"Book {book.id} has been updated successfully"})
    elif request.method=='DELETE':
        book = Book.query.get(book_id)
        if not book:
            return jsonify({"error":"Book Not Found"}), 401
        db.session.delete(book)
        db.session.commit()
        return jsonify({"message":f"Book with id {book_id} deleted successsfully"})
    
@app.route('/books', methods=['GET'])
@login_required
def searchBooks():
    if(current_user.user_role!="User"):
        return jsonify({"message": "Unauthorized Access"}), 401
    query = request.args.get('query', '')
    if not query:
        books = Book.query.all()
    else:
        books = Book.query.filter(
            (Book.title.ilike(f"%{query}%")) |
            (Book.author.ilike(f"%{query}%")) |
            (Book.genre.ilike(f"%{query}%"))
        ).all()

    serialized = [serialize_book(book) for book in books] 
    return jsonify({"books": serialized})
        

        
@app.route('/borrow', methods=['POST'])
@login_required
def borrowBook():
    data = request.get_json()
    if not data:
            return jsonify({"error":"No JSON Object Found"}), 401
    book_id = data.get('book_id')
    book = Book.query.get(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404
    if not book.available:
        return jsonify({"error": "Book is not available"}), 400
    book.available = False
    db.session.commit()
    return jsonify({
        "message": f"Book '{book.title}' has been borrowed successfully ."
    }), 200

@app.route('/return', methods=['POST'])
@login_required
def returnBook():
    data = request.get_json()
    if not data:
            return jsonify({"error":"No JSON Object Found"}), 401
    book_id = data.get('book_id')
    book = Book.query.get(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404
    book.available = True
    db.session.commit()
    return jsonify({
        "message": f"Book '{book.title}' has been returned successfully ."
    }), 200
    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not Users.query.filter_by(username='admin@gmail.com').first() and not Users.query.filter_by(username='user@gmail.com').first():
            admin = Users(username='admin@gmail.com', password='adminpass', user_role="Admin")
            user = Users(username='user@gmail.com', password='userpass', user_role="User")
            db.session.add(admin)
            db.session.add(user)
            db.session.commit()
    app.run(debug=True)