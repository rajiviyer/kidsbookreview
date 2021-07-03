from bookcollection import app, os, db
from flask import render_template, redirect, url_for, flash, request
from bookcollection.models import Book, Review, Quote
from sqlalchemy import or_
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import base64
import io
from bs4 import BeautifulSoup
import requests
import re
from better_profanity import profanity


#nltk.download('wordnet')
#nltk.download('stopwords')
#nltk.download('punkt')

class DataCollection:
    '''
    Class is used for Retrieval and Insertion of Childrens' Books Data
    '''
    def __init__(self, book_name):
        self.title = book_name.split(", Book")[0]
        self.url = "https://www.commonsensemedia.org"
        self.kwroute = "book-reviews"
        self.headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'
                    }
        self.firefox_driver_path = "geckodriver.exe"
        self.book_review_url = "https://www.goodreads.com"
        self.command = "/search?q="
        self.quotes_command = "/work/quotes/"

    def getDescription(self):
        book = Book.query.filter(Book.title.like(self.title + "%")).first()
        return book.description

    def getReviewText(self):
        book = Book.query.filter(Book.title.like(self.title + "%")).first()
        # if reviews not found in DB try retrieving from web and loading into DB
        if not self.reviewExistDB(book.id):
            try:
                for review in self.getReviewsFromWeb():
                    review_obj = Review(review_text=review, book=book)
                    db.session.add(review_obj)
                    db.session.commit()
                    print(f"Added Reviews for book {self.title}")
            except Exception as e:
                print(f"BooK: {self.title} Exception: {str(e)}")

        reviews = Review.query.filter_by(book_id=book.id)
        corpus = ""
        for review in reviews:
            corpus += review.review_text
        stop_words = stopwords.words('english')
        lemmatizer = WordNetLemmatizer()
        lemmatized_words = [lemmatizer.lemmatize(word, pos='v') for word in word_tokenize(corpus.lower()) if
                            word not in stop_words and word.isalnum()]
        final_set = " ".join(lemmatized_words)
        return final_set

    def getQuoteText(self):
        book = Book.query.filter(Book.title.like(self.title + "%")).first()
        # if quotes not found in DB try retrieving from web and loading into DB
        if not self.quoteExistDB(book.id):
            try:
                for quote in self.getQuotesFromWeb():
                    quote_obj = Quote(review_text=review, book=book)
                    db.session.add(quote_obj)
                    db.session.commit()
                    print(f"Added Quote for book {self.title}")
            except Exception as e:
                print(f"Book: {self.title} Exception: {str(e)}")

        reviews = Review.query.filter_by(book_id=book.id)
        corpus = ""
        for review in reviews:
            corpus += review.review_text
        stop_words = stopwords.words('english')
        lemmatizer = WordNetLemmatizer()
        lemmatized_words = [lemmatizer.lemmatize(word, pos='v') for word in word_tokenize(corpus.lower()) if
                            word not in stop_words and word.isalnum()]
        final_set = " ".join(lemmatized_words)
        return final_set

    def reviewExistDB(self, book_id):
        return(Review.query.filter_by(book_id=book_id).first())

    def quoteExistDB(self, book_id):
        return(Quote.query.filter_by(book_id=book_id).first())

    def getReviewsFromWeb(self):
        formatted_title = self.getBookTitleString()
        review_links_res = requests.get(self.book_review_url + formatted_title)
        reviews_links_soup = BeautifulSoup(review_links_res.text, features="html.parser")
        review_divs = reviews_links_soup.findAll("div", {"id": "bookReviews"})[0]
        review_spans = review_divs.findAll('span', id=re.compile(r"reviewTextContainer\d.*"))
        for span in review_spans:
            txtContSpan = span.find("span", id=re.compile(r"freeTextContainer\d.*"))
            txtSpan = span.find("span", id=re.compile(r"freeText\d.*"))
            if txtSpan:
                yield txtSpan.get_text().strip()
            else:
                yield txtContSpan.get_text().strip()

    def getQuotesFromWeb(self):
        formatted_title = self.getBookTitleString
        quotes_res = requests.get(self.book_review_url + self.quotes_command + formatted_title)
        quotes_page = BeautifulSoup(quotes_res.text, features="html.parser")
        quotes_divs = quotes_page.findAll('div', {'class': 'quoteText'})
        #print(quotes_divs)
        for quotes in quotes_divs:
            quote_extracted = quotes.get_text().replace("\n", "").split("―")[0]
            quote_trimmed = quote_extracted.strip().lstrip("“").rstrip("”")
            yield quote_trimmed

    def getBookTitleString(self):
        search_text = self.title.lower().replace(" ", "-")
        res = requests.get(self.book_review_url + self.command + search_text, headers=self.headers)
        main_page = BeautifulSoup(res.text, features="html.parser")
        formatted_title = main_page.findAll('a', {'class': 'bookTitle'})[0]['href'].split("?")[0]
        return formatted_title

    def saveImage(self, review_text, file_name):
        try:
            wordcloud = WordCloud(background_color="white", width=800, height=400).generate(review_text)
            plt.figure(figsize=(10, 8))
            plt.axis("off")
            plt.imshow(wordcloud, interpolation='bilinear')
            image_path = os.path.join(app.config['IMG_DIR'], file_name + '.png')
            #        clean = Clean(directory=app.config['IMG_DIR'])
            #        clean.cleanUp()
            print(image_path)
            plt.tight_layout()
            plt.savefig(image_path, bbox_inches="tight")
            plt.close()
        except Exception as e:
            print(f"Exception: {str(e)}")

    def getWCImage(self, review_text):
        try:
            wordcloud = WordCloud(background_color="white", width=800, height=400).generate(review_text)
            plt.figure(figsize=(6, 4))
            plt.axis("off")
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.tight_layout()
            data = io.BytesIO()
            plt.savefig(data, bbox_inches="tight", format="png")
            data.seek(0)
            plt.close()
            return base64.b64encode(data.getvalue())
        except Exception as e:
            print(f"Exception: {str(e)}")
            return None

    def cleanUp(self, clean_path):
        if os.listdir(clean_path) != list():
            # iterate over the files and remove each file
            files = os.listdir(clean_path)
            for fileName in files:
                print(fileName)
                os.remove(os.path.join(clean_path, fileName))
        print("cleaned!")

@app.route("/", methods=['GET', 'POST'], defaults={"page_num": 1})
@app.route("/home/<int:page_num>", methods=['GET', 'POST'])
def home_page(page_num):
    books = Book.query.paginate(per_page=8, page=page_num, error_out=True)
    if request.method == 'POST' and 'tag' in request.form:
       tag = request.form["tag"]
       search = "%{}%".format(tag)
       print(f"search: {search}")
       books = Book.query.filter(or_(Book.title.like(search), Book.rating.like(search),
                                     Book.age.like(search), Book.author.like(search),
                                     Book.year.like(search))).paginate(per_page=8, error_out=True)
       return render_template('home.html', books=books, tag=tag)
    return render_template('home.html', books=books)

@app.route("/details/<book_name>", methods=['GET', 'POST'])
def details_page(book_name):
    bookData = DataCollection(book_name)
    description = bookData.getDescription()
    reviewText = bookData.getReviewText()
#    if reviewText:
#        bookData.saveImage(reviewText, book_name.lower().replace(" ", "_"))
    if reviewText:
        stop_words = stopwords.words('english')
        lemmatizer = WordNetLemmatizer()
        lemmatized_words = [lemmatizer.lemmatize(word, pos='v') for word in word_tokenize(reviewText.lower()) if
                            word not in stop_words and word.isalnum()]
        profanity.load_censor_words()
        profane_words = [lemma for lemma in lemmatized_words if lemma in profanity.CENSOR_WORDSET]
        lemma_review_set = " ".join(lemmatized_words)
        profane_review_set = " ".join(profane_words)
        wordCloudReviewImg = bookData.getWCImage(lemma_review_set)
        wordCloudProfanityImg = bookData.getWCImage(profane_review_set)
        if wordCloudReviewImg:
            wordCloudReviewImg = wordCloudReviewImg.decode('utf-8')

        if wordCloudProfanityImg:
            wordCloudProfanityImg = wordCloudProfanityImg.decode('utf-8')
    else:
        wordCloudReviewImg = None
        wordCloudProfanityImg = None

#    full_filename = os.path.join(app.config['IMG_DIR'], book_name.lower().replace(" ", "_")+".png")
    return render_template('details.html', book_name=book_name, description=description,
                           review_wordcloud=wordCloudReviewImg,
                           profane_wordcloud=wordCloudProfanityImg
                           )
