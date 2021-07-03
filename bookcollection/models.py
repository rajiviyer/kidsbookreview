from bookcollection import db

class Book(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(length=500), nullable=False, unique=True)
    rating = db.Column(db.Integer())
    description = db.Column(db.String(length=500))
    age = db.Column(db.Integer())
    author = db.Column(db.String(length=100), nullable=False)
    year = db.Column(db.Integer())
    addresses = db.relationship('Review', backref='book', lazy=True)
    quotes = db.relationship('Quote', backref='book', lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    review_text = db.Column(db.String())
    book_id = db.Column(db.Integer(), db.ForeignKey('book.id'), nullable=False)

class Quote(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    quote_text = db.Column(db.String())
    book_id = db.Column(db.Integer(), db.ForeignKey('book.id'), nullable=False)
